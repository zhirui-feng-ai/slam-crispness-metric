"""
scenes.py — 3D environments spanning the geometric-conditioning spectrum.

The scene controls *point-cloud complexity*, the second axis of every experiment
(the first is drift). Scenes are ordered from well-constrained (lots of planar
structure, normals in every direction) to degenerate (featureless along one axis):

    room      → fully constrained: 4 walls + floor + ceiling + obstacle
    parking   → structured but sparse: floor + pillar grid + perimeter
    highway   → feature-sparse open: ground plane + sparse guardrail/signs
    corridor  → mild degeneracy: long hallway, weak along-axis constraint
    tunnel    → strong degeneracy: long symmetric tube, along-axis unobservable

`degenerate_axis` is the unit world-direction whose translation the geometry
fails to constrain (None if well-conditioned). The catastrophic "geometric
degeneracy" drift mode pushes pose error preferentially along this axis — the
synthetic analog of ICP "sliding" in a tunnel (research-failure-modes §1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np

from .geometry import Quad, box_quads, ground_plane


@dataclass
class Scene:
    name: str
    quads: list
    degenerate_axis: np.ndarray | None  # unit vec of poorly-constrained translation, or None
    bounds: np.ndarray                  # (3,2) world AABB [min,max] per axis
    structure: str                      # human label of geometric conditioning
    path_kind: str                      # default trajectory style for this scene

    def n_surfaces(self) -> int:
        return len(self.quads)


# ── Builders ────────────────────────────────────────────────────────────────

def room(width=20.0, depth=14.0, height=4.0, add_obstacle=True) -> Scene:
    """Closed rectangular room. The well-conditioned reference scene."""
    quads = []
    cx, cy = width / 2, depth / 2
    # Floor + ceiling
    quads.append(ground_plane((cx, cy), (width, depth)))
    quads.append(Quad([0, 0, height], [width, 0, 0], [0, depth, 0]))
    # 4 walls
    quads.append(Quad([0, 0, 0], [width, 0, 0], [0, 0, height]))        # y=0
    quads.append(Quad([0, depth, 0], [width, 0, 0], [0, 0, height]))    # y=depth
    quads.append(Quad([0, 0, 0], [0, depth, 0], [0, 0, height]))        # x=0
    quads.append(Quad([width, 0, 0], [0, depth, 0], [0, 0, height]))    # x=width
    if add_obstacle:
        quads += box_quads([cx, cy, height / 2], [4.0, 3.0, height * 0.9])
    return Scene("room", quads, None,
                 np.array([[0, width], [0, depth], [0, height]], float),
                 "well-conditioned (planar structure in all directions)", "loop")


def parking(width=40.0, depth=24.0, height=3.0, n_cols=4, n_rows=2) -> Scene:
    """Underground-parking analog: floor + perimeter walls + pillar grid."""
    quads = [ground_plane((width / 2, depth / 2), (width, depth)),
             Quad([0, 0, height], [width, 0, 0], [0, depth, 0])]
    quads.append(Quad([0, 0, 0], [width, 0, 0], [0, 0, height]))
    quads.append(Quad([0, depth, 0], [width, 0, 0], [0, 0, height]))
    quads.append(Quad([0, 0, 0], [0, depth, 0], [0, 0, height]))
    quads.append(Quad([width, 0, 0], [0, depth, 0], [0, 0, height]))
    for i in range(1, n_cols + 1):
        for j in range(1, n_rows + 1):
            px = width * i / (n_cols + 1)
            py = depth * j / (n_rows + 1)
            quads += box_quads([px, py, height / 2], [0.6, 0.6, height])
    return Scene("parking", quads, None,
                 np.array([[0, width], [0, depth], [0, height]], float),
                 "structured but sparse (pillars + perimeter)", "serpentine")


def highway(length=120.0, lane_width=16.0, n_signs=6) -> Scene:
    """Open highway: ground plane + thin guardrails + sparse roadside signs.
    Feature-sparse; cross-track constrained by rails, along-track weakly."""
    quads = [ground_plane((length / 2, 0.0), (length, lane_width * 2))]
    # Low guardrails on both sides (thin vertical strips).
    for side in (-1, 1):
        y = side * lane_width
        quads.append(Quad([0, y, 0], [length, 0, 0], [0, 0, 0.8]))
    # Sparse roadside signs (small vertical quads).
    rng = np.random.default_rng(7)
    for k in range(n_signs):
        x = length * (k + 0.5) / n_signs
        y = (lane_width + 2.0) * (1 if k % 2 else -1)
        z0 = 1.5
        quads.append(Quad([x, y, z0], [0, 1.2, 0], [0, 0, 1.2]))
    return Scene("highway", quads, np.array([1.0, 0.0, 0.0]),
                 np.array([[0, length], [-lane_width, lane_width], [0, 5]], float),
                 "feature-sparse open (weak along-track constraint)", "straight")


def corridor(length=60.0, width=3.0, height=3.0) -> Scene:
    """Long narrow hallway. Mild degeneracy along its length (x-axis)."""
    quads = [ground_plane((length / 2, 0.0), (length, width)),
             Quad([0, -width / 2, height], [length, 0, 0], [0, width, 0])]
    quads.append(Quad([0, -width / 2, 0], [length, 0, 0], [0, 0, height]))
    quads.append(Quad([0, width / 2, 0], [length, 0, 0], [0, 0, height]))
    # End caps give weak along-axis constraint (corridor < tunnel degeneracy).
    quads.append(Quad([0, -width / 2, 0], [0, width, 0], [0, 0, height]))
    quads.append(Quad([length, -width / 2, 0], [0, width, 0], [0, 0, height]))
    return Scene("corridor", quads, np.array([1.0, 0.0, 0.0]),
                 np.array([[0, length], [-width, width], [0, height]], float),
                 "mildly degenerate (long hallway, end-capped)", "straight")


def tunnel(length=100.0, width=5.0, height=4.5) -> Scene:
    """Long symmetric tube, NO end caps → strong along-axis degeneracy.
    The hardest scene: translation along x is geometrically unobservable."""
    quads = [ground_plane((length / 2, 0.0), (length, width)),
             Quad([0, -width / 2, height], [length, 0, 0], [0, width, 0])]
    quads.append(Quad([0, -width / 2, 0], [length, 0, 0], [0, 0, height]))
    quads.append(Quad([0, width / 2, 0], [length, 0, 0], [0, 0, height]))
    return Scene("tunnel", quads, np.array([1.0, 0.0, 0.0]),
                 np.array([[0, length], [-width, width], [0, height]], float),
                 "strongly degenerate (symmetric tube, no along-axis features)", "straight")


def street(length=80.0, road_width=12.0, sidewalk=3.0, height=12.0) -> Scene:
    """Urban-canyon on-road scene: road + sidewalks + segmented building facades
    of varying height on both sides + curbs + parked cars + lamp poles. The
    realistic scenario for the 3D drift viewer. Facades make it well-conditioned
    (urban canyons are tractable; the threat there is GNSS, not geometry)."""
    half = road_width / 2 + sidewalk
    span_y = (half + 4) * 2
    quads = [ground_plane((length / 2, 0.0), (length, span_y))]
    rng = np.random.default_rng(11)

    # Segmented building facades on both sides, each "building" a different height.
    seg = 12.0
    x = 0.0
    while x < length - 1e-6:
        w = min(seg, length - x)
        for side in (-1, 1):
            y = side * half
            h = height * rng.uniform(0.55, 1.5)
            quads.append(Quad([x, y, 0], [w, 0, 0], [0, 0, h]))      # facade
            # a couple of windows ledges → vertical texture (thin offset strips)
            quads.append(Quad([x, y - side * 0.3, h * 0.5], [w, 0, 0], [0, 0, 0.3]))
        x += w

    # Curbs (low strips at the road edge).
    for side in (-1, 1):
        y = side * road_width / 2
        quads.append(Quad([0, y, 0], [length, 0, 0], [0, 0, 0.15]))

    # Parked cars (left curb) + lamp poles (right) every 16 m.
    for k in range(int(length / 16)):
        xx = 8 + k * 16
        quads += box_quads([xx, -(road_width / 2 + 1.3), 0.75], [4.4, 1.9, 1.5])
        quads += box_quads([xx + 8, road_width / 2 + 0.6, 2.5], [0.3, 0.3, 5.0])

    return Scene("street", quads, None,
                 np.array([[0, length], [-(half + 4), half + 4], [0, height * 1.5]], float),
                 "urban canyon (on-road: facades + cars + poles)", "straight")


# Registry: ordered by increasing geometric difficulty.
SCENE_BUILDERS = {
    "room": room,
    "parking": parking,
    "highway": highway,
    "corridor": corridor,
    "tunnel": tunnel,
    "street": street,
}

# Core conditioning-spectrum set used by the scene-dependence experiment
# (street is a demo/viewer scene, intentionally excluded from the sweep).
SCENE_ORDER = ["room", "parking", "highway", "corridor", "tunnel"]


def build_scene(name: str, **kw) -> Scene:
    return SCENE_BUILDERS[name](**kw)
