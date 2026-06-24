"""
sensor.py — spinning 3D LiDAR model.

Casts a ring-stack of beams from a pose against scene quads and returns hits in
the **sensor-local frame** (so cloud.py can re-project them through either the
true or the drifted pose — the SLAM physics).

LidarConfig exposes the levers the research flags as worth sweeping:
  · n_beams           — 32 / 64 / 128 (research-imu-grades §4: trajectory ATE
                        saturates ~32–64 beams, but map *density* keeps rising —
                        a crispness-vs-beams question that is still open)
  · range_noise_sigma — zero-mean per-point range jitter (the NOISE tier)
  · dropout_prob      — random point loss (rain ≥30 mm/h loses up to 56%)
  · max_range         — fog collapses effective range to ~25 m
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import numpy as np

from .geometry import Quad, raycast, rot_matrix


@dataclass(frozen=True)
class LidarConfig:
    n_beams: int = 32
    vfov_deg: tuple = (-25.0, 15.0)   # vertical field of view (low, high)
    azimuth_step_deg: float = 1.5     # horizontal resolution → 240 columns
    max_range: float = 80.0
    range_noise_sigma: float = 0.02   # 2 cm — typical mechanical LiDAR (NOISE tier baseline)
    dropout_prob: float = 0.0

    def beam_dirs_local(self) -> np.ndarray:
        """(R,3) unit beam directions in the sensor frame."""
        elev = np.deg2rad(np.linspace(self.vfov_deg[0], self.vfov_deg[1], self.n_beams))
        az = np.deg2rad(np.arange(0.0, 360.0, self.azimuth_step_deg))
        E, A = np.meshgrid(elev, az, indexing="ij")
        ce = np.cos(E)
        dirs = np.stack([ce * np.cos(A), ce * np.sin(A), np.sin(E)], axis=-1)
        return dirs.reshape(-1, 3)


def scan_local(pose: np.ndarray, quads: list[Quad], cfg: LidarConfig,
               rng: np.random.Generator) -> np.ndarray:
    """
    One LiDAR sweep from `pose`. Returns (M,3) hit points in the SENSOR-LOCAL
    frame, with zero-mean range noise and random dropout applied. Empty (0,3) if
    nothing is hit.
    """
    R, t = rot_matrix(pose[3:6]), pose[0:3]
    dirs_local = cfg.beam_dirs_local()
    dirs_world = dirs_local @ R.T                      # (R,3)
    hit_world, mask = raycast(t, dirs_world, quads, cfg.max_range)
    if len(hit_world) == 0:
        return np.empty((0, 3))

    # Back to local frame (range/bearing realized about the true sensor origin).
    local = (hit_world - t) @ R                        # (K,3)

    # NOISE tier: zero-mean Gaussian along the beam (radial) direction.
    if cfg.range_noise_sigma > 0:
        rng_norm = np.linalg.norm(local, axis=1, keepdims=True)
        unit = local / np.maximum(rng_norm, 1e-9)
        local = local + unit * rng.normal(0.0, cfg.range_noise_sigma, size=(len(local), 1))

    # Random dropout (weather point loss).
    if cfg.dropout_prob > 0:
        keep = rng.random(len(local)) >= cfg.dropout_prob
        local = local[keep]

    return local


def with_overrides(cfg: LidarConfig, *, range_noise_sigma=None, dropout_prob=None,
                   max_range=None) -> LidarConfig:
    """Return a copy of `cfg` with selected fields overridden (used by drift modes)."""
    kw = {}
    if range_noise_sigma is not None:
        kw["range_noise_sigma"] = range_noise_sigma
    if dropout_prob is not None:
        kw["dropout_prob"] = dropout_prob
    if max_range is not None:
        kw["max_range"] = max_range
    return replace(cfg, **kw)
