"""
harness.py — shared experiment infrastructure.

Centralizes the operating point, reference-cloud caching, and the honest
sampling policy so every experiment script is a thin, declarative wrapper.

Sampling policy
---------------
We score on a RANDOM downsample (cap NPOINTS), never a voxel downsample. Voxel
downsampling collapses each cell to a centroid and silently *denoises* the cloud
— which would let a metric look noise-robust for the wrong reason (the sampler
did the work). Random downsampling preserves per-point spread and density, so
the noise tier is evaluated fairly.
"""

from __future__ import annotations

import os, sys, json, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import slam_synthbench as sb
from slam_synthbench import (build_scene, make_trajectory, reference_cloud,
                             observed_cloud, inject, LidarConfig)
from slam_synthbench.metrics import compute_all, REFERENCE_FREE
from slam_synthbench.sampling import random_downsample

RESULTS = ROOT / "experiments" / "results"
FIGURES = ROOT / "figures"
RESULTS.mkdir(exist_ok=True)
FIGURES.mkdir(exist_ok=True)

# ── operating point (≈ the 30 s crispness window, kept compute-bounded) ─────
CFG = LidarConfig(n_beams=24, azimuth_step_deg=2.5, max_range=80.0, range_noise_sigma=0.02)
DURATION = 20.0        # seconds
SPEED = 16.7           # m/s (≈60 km/h)
VOXEL = 0.5            # metric voxel edge (m)
NPOINTS = 80_000       # random-downsample cap for scoring

# Representative scene triplet spanning the conditioning spectrum.
SCENES_CORE = ["room", "highway", "tunnel"]
# Default mode set: one+ per tier (skip range_scale/loop/sine/step for the core
# sweep — they're available for the notebook).
MODES_CORE = ["sensor_noise", "accel_bias", "gyro_bias", "dynamic_objects",
              "geometric_degeneracy", "weather_dropout", "imu_saturation",
              "random_walk"]


_REF_CACHE: dict = {}


def get_reference(scene_name: str, cfg: LidarConfig = CFG, duration=DURATION, speed=SPEED):
    """Reference (ideal) cloud + scene + trajectory, cached per scene/cfg."""
    key = (scene_name, cfg.n_beams, cfg.azimuth_step_deg, duration, speed)
    if key not in _REF_CACHE:
        scene = build_scene(scene_name)
        traj = make_trajectory(scene, speed=speed, duration=duration)
        ref = reference_cloud(scene, traj, cfg)
        _REF_CACHE[key] = (scene, traj, ref)
    return _REF_CACHE[key]


def one_sample(scene_name, mode, level, seed, cfg=CFG, cap=NPOINTS, voxel=VOXEL,
               keep_clouds=False) -> dict:
    """Run the pipeline once and return a flat record (scores + labels)."""
    scene, traj, ref = get_reference(scene_name, cfg)
    dr = inject(traj, scene, mode, level, seed=seed)
    obs = observed_cloud(scene, traj, dr, cfg, seed=seed)
    obs_s = random_downsample(obs, cap, seed=seed)
    ref_s = random_downsample(ref, cap, seed=seed)
    scores = compute_all(obs_s, ref_s, voxel=voxel)
    rec = dict(scene=scene_name, mode=mode, tier=dr.tier, level=level, seed=seed,
               drift_intensity=dr.drift_intensity, n_points=len(obs), **scores)
    rec.update({f"realized.{k}": v for k, v in dr.realized.items()
                if isinstance(v, (int, float))})
    if keep_clouds:
        rec["_obs"], rec["_ref"] = obs_s, ref_s
    return rec


def gen_dataset(scenes, modes, levels, seeds, cfg=CFG, cap=NPOINTS, voxel=VOXEL,
                verbose=True) -> pd.DataFrame:
    """Cartesian sweep scenes × modes × levels × seeds → tidy DataFrame."""
    rows, t0, total = [], time.perf_counter(), 0
    n_total = len(scenes) * len(modes) * len(levels) * len(seeds)
    for scene_name in scenes:
        for mode in modes:
            for level in levels:
                for seed in seeds:
                    rows.append(one_sample(scene_name, mode, level, seed, cfg, cap, voxel))
                    total += 1
            if verbose:
                print(f"  [{total:4d}/{n_total}] {scene_name:9s} {mode:22s} "
                      f"({time.perf_counter()-t0:5.1f}s)", flush=True)
    return pd.DataFrame(rows)


def save_df(df: pd.DataFrame, name: str):
    path = RESULTS / f"{name}.csv"
    df.to_csv(path, index=False)
    return path


def save_json(obj, name: str):
    path = RESULTS / f"{name}.json"
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=lambda o: float(o) if isinstance(o, np.floating) else o)
    return path
