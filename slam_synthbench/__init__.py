"""
slam_synthbench — synthetic SLAM-drift benchmark for crispness-metric evaluation.

A reusable, verifiable harness that:
  1. builds 3D scenes spanning the geometric-conditioning spectrum (scenes.py),
  2. drives a configurable 3D LiDAR over a timed trajectory (trajectory, sensor),
  3. injects physically-grounded drift in three research tiers (drift.py),
  4. accumulates the drift-corrupted map the SLAM way (cloud.py),
  5. scores it with six metric candidates (metrics.py),
  6. and grades each metric on sensitivity / separability / scene-independence /
     noise-robustness / compute (evaluation.py, profiling.py).

High-level entry point: `make_sample(...)` runs the whole pipeline once and
returns a Sample (clouds + metric scores + labels).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
import numpy as np

# numpy 2.0's BLAS matmul spuriously sets FP-exception flags on macOS Accelerate
# for non-contiguous operands (outputs are verified finite). Silence only that
# specific false-positive; all other RuntimeWarnings stay live.
warnings.filterwarnings("ignore", message=".*encountered in matmul", category=RuntimeWarning)

from .scenes import build_scene, Scene, SCENE_ORDER, SCENE_BUILDERS
from .trajectory import make_trajectory, Trajectory
from .sensor import LidarConfig
from .drift import (inject, DriftResult, DRIFT_MODES, list_modes, Tier,
                    IMU_GRADES, IMU_GRADE_ORDER, imu_grade_bias)
from .cloud import reference_cloud, observed_cloud, accumulate
from .metrics import compute_all, voxel_pca, METRIC_INFO, REFERENCE_FREE
from . import metrics, evaluation, profiling, sampling

__all__ = [
    "build_scene", "Scene", "SCENE_ORDER", "SCENE_BUILDERS",
    "make_trajectory", "Trajectory", "LidarConfig",
    "inject", "DriftResult", "DRIFT_MODES", "list_modes", "Tier",
    "IMU_GRADES", "IMU_GRADE_ORDER", "imu_grade_bias",
    "reference_cloud", "observed_cloud", "accumulate",
    "compute_all", "voxel_pca", "METRIC_INFO", "REFERENCE_FREE",
    "metrics", "evaluation", "profiling", "sampling",
    "make_sample", "Sample",
]


@dataclass
class Sample:
    scene: str
    mode: str
    tier: str
    level: float
    seed: int
    drift_intensity: float
    n_points: int
    scores: dict
    realized: dict
    observed: np.ndarray = field(default=None, repr=False)
    reference: np.ndarray = field(default=None, repr=False)


def make_sample(scene_name: str = "room", mode: str = "gyro_bias", level: float = 0.5,
                seed: int = 0, cfg: LidarConfig | None = None,
                duration: float = 30.0, speed: float = 16.7,
                voxel: float = 0.5, keep_clouds: bool = False,
                ref: np.ndarray | None = None) -> Sample:
    """Run scene → trajectory → drift → accumulate → score, end to end."""
    cfg = cfg or LidarConfig()
    scene = build_scene(scene_name)
    traj = make_trajectory(scene, speed=speed, duration=duration)
    dr = inject(traj, scene, mode, level, seed=seed)
    obs = observed_cloud(scene, traj, dr, cfg, seed=seed)
    if ref is None:
        ref = reference_cloud(scene, traj, cfg)
    scores = compute_all(obs, ref, voxel=voxel)
    return Sample(
        scene=scene_name, mode=mode, tier=dr.tier, level=level, seed=seed,
        drift_intensity=dr.drift_intensity, n_points=len(obs),
        scores=scores, realized=dr.realized,
        observed=obs if keep_clouds else None,
        reference=ref if keep_clouds else None,
    )
