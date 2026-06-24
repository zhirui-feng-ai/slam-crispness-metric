"""
cloud.py — accumulate LiDAR sweeps into a map, the SLAM way.

Two clouds come out of a drift scenario:

  reference_cloud  — STATIC scene, TRUE poses, noise-free, full range.
                     The ideal map. Only the oracle metric (chamfer) sees it.

  observed_cloud   — what SLAM actually builds: sweeps re-projected through the
                     DRIFTED (estimated) poses, including dynamic objects and
                     sensor effects (noise / dropout / range collapse / scale).
                     Every reference-free metric scores this.

The re-projection physics (mirrors the original 2D injector): sense from the
TRUE pose, express the hit in the sensor-local frame, then place it back in the
world through the ESTIMATED pose. Correct observations through a wrong pose —
exactly what smears a SLAM map.
"""

from __future__ import annotations

import numpy as np

from .geometry import transform_points
from .sensor import LidarConfig, scan_local, with_overrides
from .trajectory import Trajectory
from .scenes import Scene
from .drift import DriftResult


def reference_cloud(scene: Scene, traj: Trajectory, cfg: LidarConfig) -> np.ndarray:
    """Ideal noise-free static map from the ground-truth trajectory."""
    clean_cfg = with_overrides(cfg, range_noise_sigma=0.0, dropout_prob=0.0)
    rng = np.random.default_rng(0)
    chunks = []
    for pose in traj.poses:
        local = scan_local(pose, scene.quads, clean_cfg, rng)
        if len(local):
            chunks.append(transform_points(pose, local))
    return np.vstack(chunks) if chunks else np.empty((0, 3))


def observed_cloud(scene: Scene, traj: Trajectory, drift: DriftResult,
                   cfg: LidarConfig, seed: int = 0) -> np.ndarray:
    """The drift-corrupted map a reference-free metric must score."""
    eff = drift.effects
    obs_cfg = with_overrides(
        cfg,
        range_noise_sigma=eff.range_noise_sigma,
        dropout_prob=eff.dropout_prob,
        max_range=eff.max_range,
    )
    rng = np.random.default_rng(seed + 1)
    n = traj.n
    chunks = []
    for i in range(n):
        true_pose = traj.poses[i]
        est_pose = drift.perturbed_poses[i]
        quads = scene.quads
        if eff.dynamic_quads is not None:
            quads = quads + eff.dynamic_quads(i, n)
        local = scan_local(true_pose, quads, obs_cfg, rng)
        if not len(local):
            continue
        if eff.scale_factor != 1.0:
            local = local * eff.scale_factor       # RANGE_SCALE acts in local frame
        chunks.append(transform_points(est_pose, local))
    return np.vstack(chunks) if chunks else np.empty((0, 3))


def accumulate(scene: Scene, traj: Trajectory, drift: DriftResult,
               cfg: LidarConfig, seed: int = 0,
               ref: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Convenience: (observed, reference). Pass `ref` to reuse a cached reference."""
    obs = observed_cloud(scene, traj, drift, cfg, seed=seed)
    if ref is None:
        ref = reference_cloud(scene, traj, cfg)
    return obs, ref
