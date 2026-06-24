"""
Experiment 4 — Compute complexity.

Question: what does each metric cost, and how does it scale? Backfill at AV
scale is the binding constraint (PLAN Week-1 compute pass). We time every metric
on the SAME cloud random-downsampled to a geometric ladder of sizes, then fit
the empirical exponent in log-log space — so O(N) vs O(N log N) is measured.

Outputs
  results/exp04_complexity.json
  figures/f5_compute_complexity.png   log-log time vs N with fitted exponents
"""

from __future__ import annotations
import numpy as np

from harness import (get_reference, save_json, FIGURES, CFG)
from slam_synthbench import inject, observed_cloud, profiling
from slam_synthbench import metrics as M
from slam_synthbench.metrics import METRIC_INFO
from slam_synthbench.sampling import random_downsample
from slam_synthbench import plotting as P

SIZES = [2_000, 5_000, 10_000, 20_000, 50_000, 100_000, 200_000, 400_000]


def run():
    print("[exp04] building base cloud + timing metrics across sizes…")
    scene, traj, ref = get_reference("room")
    dr = inject(traj, scene, "gyro_bias", 0.6, seed=0)
    base = observed_cloud(scene, traj, dr, CFG, seed=0)
    ref_fixed = random_downsample(ref, 8000, seed=0)

    clouds = {N: random_downsample(base, N, seed=0) for N in SIZES if N <= len(base)}

    metric_fns = {
        "voxel_pca_crispness": lambda p: M.voxel_pca_crispness(p, voxel=0.5),
        "mme_grid":            lambda p: M.mme_grid(p, voxel=0.5),
        "mom_planarity":       lambda p: M.mom_planarity(p, voxel=0.5),
        "bev_edge_density":    lambda p: M.bev_edge_density(p),
        "knn_entropy_mme":     lambda p: M.knn_entropy_mme(p),
        "chamfer_oracle":      lambda p: M.chamfer_oracle(p, ref_fixed),
    }
    profile = profiling.complexity_sweep(metric_fns, clouds, repeats=3)

    save_json({k: {kk: vv for kk, vv in v.items()} for k, v in profile.items()},
              "exp04_complexity")
    P.complexity_loglog(profile, FIGURES / "f5_compute_complexity.png",
                        title="F5 · Metric compute scaling (room, log-log)")

    biggest = max(clouds)
    print(f"[exp04] per-metric time @ N={biggest:,} and fitted exponent p:")
    for k, p in sorted(profile.items(), key=lambda kv: kv[1]["times"][-1]):
        print(f"         {METRIC_INFO[k].label:18s} {p['times'][-1]*1e3:8.1f} ms   p≈{p['exponent']:.2f}")


if __name__ == "__main__":
    run()
