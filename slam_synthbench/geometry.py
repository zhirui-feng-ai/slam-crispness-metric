"""
geometry.py — 3D geometry primitives for the SLAM synthetic benchmark.

Everything downstream (scenes, sensor, drift, cloud accumulation) is built on:
  · SE(3) poses stored as 6-vectors [x, y, z, roll, pitch, yaw]  (meters, radians)
  · planar **quads** as the only scene primitive (origin + two edge vectors)
  · a vectorized ray caster that intersects a bundle of rays against a quad list

Conventions
-----------
  Rotation order:  R = Rz(yaw) @ Ry(pitch) @ Rx(roll)   (ZYX intrinsic / yaw-pitch-roll)
  World frame:     x forward-ish, y left, z up (right-handed). Ground plane is z = 0.
  A "pose" transforms sensor-local points into the world:  p_world = R @ p_local + t
"""

from __future__ import annotations

import numpy as np

EPS = 1e-9


# ── SE(3) ──────────────────────────────────────────────────────────────────────

def rot_matrix(rpy: np.ndarray) -> np.ndarray:
    """Rotation matrix from [roll, pitch, yaw] (radians), ZYX order."""
    r, p, y = float(rpy[0]), float(rpy[1]), float(rpy[2])
    cr, sr = np.cos(r), np.sin(r)
    cp, sp = np.cos(p), np.sin(p)
    cy, sy = np.cos(y), np.sin(y)
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def pose_to_Rt(pose: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Split a 6-vector pose into (R 3x3, t 3,)."""
    pose = np.asarray(pose, dtype=np.float64)
    return rot_matrix(pose[3:6]), pose[0:3].copy()


def transform_points(pose: np.ndarray, local_pts: np.ndarray) -> np.ndarray:
    """Map (M,3) local points into world frame through a 6-vector pose."""
    if len(local_pts) == 0:
        return local_pts
    R, t = pose_to_Rt(pose)
    return local_pts @ R.T + t


def world_to_local(pose: np.ndarray, world_pts: np.ndarray) -> np.ndarray:
    """Inverse transform: world points into the pose's local frame."""
    if len(world_pts) == 0:
        return world_pts
    R, t = pose_to_Rt(pose)
    return (world_pts - t) @ R


# ── Quad primitive ───────────────────────────────────────────────────────────

class Quad:
    """
    A finite planar rectangle in 3D: origin `o` plus two edge vectors `e1`, `e2`.
    A surface point is  o + a*e1 + b*e2  with a, b in [0, 1].
    """

    __slots__ = ("o", "e1", "e2", "n", "_inv11", "_inv22")

    def __init__(self, o, e1, e2):
        self.o = np.asarray(o, dtype=np.float64)
        self.e1 = np.asarray(e1, dtype=np.float64)
        self.e2 = np.asarray(e2, dtype=np.float64)
        n = np.cross(self.e1, self.e2)
        nn = np.linalg.norm(n)
        self.n = n / nn if nn > EPS else n
        # Precompute 1/|e|^2 for the inside test.
        self._inv11 = 1.0 / max(self.e1 @ self.e1, EPS)
        self._inv22 = 1.0 / max(self.e2 @ self.e2, EPS)

    def translated(self, delta: np.ndarray) -> "Quad":
        return Quad(self.o + np.asarray(delta, float), self.e1, self.e2)


def box_quads(center, size) -> list[Quad]:
    """Axis-aligned box as 6 quads. `center` (3,), `size` (3,) full extents."""
    cx, cy, cz = center
    sx, sy, sz = np.asarray(size, float) / 2.0
    # 8 corners
    def c(dx, dy, dz):
        return np.array([cx + dx * sx, cy + dy * sy, cz + dz * sz])
    # Each face: origin corner + two edge vectors.
    faces = [
        (c(-1, -1, -1), c(1, -1, -1) - c(-1, -1, -1), c(-1, 1, -1) - c(-1, -1, -1)),  # bottom z-
        (c(-1, -1, 1),  c(1, -1, 1) - c(-1, -1, 1),  c(-1, 1, 1) - c(-1, -1, 1)),   # top z+
        (c(-1, -1, -1), c(1, -1, -1) - c(-1, -1, -1), c(-1, -1, 1) - c(-1, -1, -1)),  # y-
        (c(-1, 1, -1),  c(1, 1, -1) - c(-1, 1, -1),  c(-1, 1, 1) - c(-1, 1, -1)),   # y+
        (c(-1, -1, -1), c(-1, 1, -1) - c(-1, -1, -1), c(-1, -1, 1) - c(-1, -1, -1)),  # x-
        (c(1, -1, -1),  c(1, 1, -1) - c(1, -1, -1),  c(1, -1, 1) - c(1, -1, -1)),   # x+
    ]
    return [Quad(o, e1, e2) for o, e1, e2 in faces]


def ground_plane(center_xy, extent) -> Quad:
    """A horizontal floor quad at z=0 centered on `center_xy` with full `extent` (ex, ey)."""
    cx, cy = center_xy
    ex, ey = extent
    o = np.array([cx - ex / 2, cy - ey / 2, 0.0])
    return Quad(o, np.array([ex, 0, 0]), np.array([0, ey, 0]))


# ── Vectorized ray caster ───────────────────────────────────────────────────

def raycast(origin: np.ndarray, dirs: np.ndarray, quads: list[Quad],
            max_range: float) -> tuple[np.ndarray, np.ndarray]:
    """
    Cast a bundle of rays from a single `origin` along unit `dirs` (R,3) against
    `quads`. Returns (hit_points (K,3), hit_mask (R,)) for the rays that hit.

    Nearest-hit per ray. Pure-numpy, vectorized over rays, looped over quads
    (quad count is small — tens). O(R * Q).
    """
    R = dirs.shape[0]
    best_t = np.full(R, max_range, dtype=np.float64)
    origin = np.asarray(origin, dtype=np.float64)

    for q in quads:
        denom = dirs @ q.n                      # (R,)
        ok = np.abs(denom) > EPS
        if not ok.any():
            continue
        t = ((q.o - origin) @ q.n) / np.where(ok, denom, 1.0)  # (R,)
        # candidate hit points
        h = origin[None, :] + t[:, None] * dirs                # (R,3)
        rel = h - q.o[None, :]
        a = (rel @ q.e1) * q._inv11
        b = (rel @ q.e2) * q._inv22
        inside = (a >= 0.0) & (a <= 1.0) & (b >= 0.0) & (b <= 1.0)
        better = ok & inside & (t > 1e-3) & (t < best_t)
        best_t = np.where(better, t, best_t)

    hit_mask = best_t < max_range
    hit_points = origin[None, :] + best_t[hit_mask, None] * dirs[hit_mask]
    return hit_points, hit_mask
