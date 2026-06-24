"""
sampling.py — point-cloud downsampling, the third experiment axis.

Backfill at AV scale (10⁸ points) forces downsampling before metric compute.
Different schemes bias the cloud differently, so a metric's robustness to the
sampler matters as much as its raw accuracy:

  voxel_downsample  — one centroid per voxel. Density-equalizing; what most
                      production pipelines actually do.
  random_downsample — uniform random subset. Density-preserving, cheap.
  farthest_point    — greedy FPS. Coverage-maximizing; O(nN), small n only.
"""

from __future__ import annotations

import numpy as np


def voxel_downsample(points: np.ndarray, voxel: float = 0.25) -> np.ndarray:
    """One centroid per occupied voxel."""
    if len(points) == 0:
        return points
    keys = np.floor(points / voxel).astype(np.int64)
    uniq, inv, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    inv = inv.ravel()
    order = np.argsort(inv, kind="stable")
    ps = points[order]
    starts = np.zeros(len(uniq), dtype=np.int64)
    starts[1:] = np.cumsum(counts)[:-1]
    sums = np.add.reduceat(ps, starts, axis=0)
    return sums / counts[:, None]


def random_downsample(points: np.ndarray, n: int, seed: int = 0) -> np.ndarray:
    if len(points) <= n:
        return points
    rng = np.random.default_rng(seed)
    return points[rng.choice(len(points), n, replace=False)]


def farthest_point_sample(points: np.ndarray, n: int, seed: int = 0) -> np.ndarray:
    """Greedy farthest-point sampling. O(n·N) — use for small n only."""
    N = len(points)
    if N <= n:
        return points
    rng = np.random.default_rng(seed)
    idx = np.empty(n, dtype=np.int64)
    idx[0] = rng.integers(N)
    dist = np.full(N, np.inf)
    for i in range(1, n):
        last = points[idx[i - 1]]
        d = np.sum((points - last) ** 2, axis=1)
        dist = np.minimum(dist, d)
        idx[i] = np.argmax(dist)
    return points[idx]


SAMPLERS = {
    "voxel": lambda p, **kw: voxel_downsample(p, voxel=kw.get("voxel", 0.25)),
    "random": lambda p, **kw: random_downsample(p, kw.get("n", 20000), kw.get("seed", 0)),
    "fps": lambda p, **kw: farthest_point_sample(p, kw.get("n", 4000), kw.get("seed", 0)),
}
