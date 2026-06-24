"""
profiling.py — compute-cost instrumentation.

The PLAN's compute pass: "profile on realistic segment sizes" and "establish a
budget ceiling" for backfill. We measure wall-clock per metric vs point count
and fit the empirical scaling exponent via a log-log regression, so O(N) vs
O(N log N) shows up as a measured slope, not a claim.
"""

from __future__ import annotations

import time
import numpy as np


def time_call(fn, *args, repeats: int = 3, **kw) -> float:
    """Median wall-clock seconds of fn(*args, **kw) over `repeats` runs."""
    ts = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn(*args, **kw)
        ts.append(time.perf_counter() - t0)
    return float(np.median(ts))


def fit_exponent(sizes, times) -> dict:
    """Fit time ≈ c·N^p in log-log space. Returns exponent p and constant c."""
    s = np.log(np.asarray(sizes, float))
    t = np.log(np.maximum(np.asarray(times, float), 1e-9))
    p, logc = np.polyfit(s, t, 1)
    return {"exponent": float(p), "const": float(np.exp(logc))}


def complexity_sweep(metric_fns: dict, clouds_by_size: dict, repeats: int = 3) -> dict:
    """
    metric_fns      : {key: callable(points) -> float}
    clouds_by_size  : {N: points array}  (already downsampled to size N)

    Returns {key: {"sizes": [...], "times": [...], "exponent": p, "const": c,
                   "us_per_point": [...]}}.
    """
    sizes = sorted(clouds_by_size)
    out = {}
    for key, fn in metric_fns.items():
        times = [time_call(fn, clouds_by_size[N], repeats=repeats) for N in sizes]
        fit = fit_exponent(sizes, times)
        out[key] = {
            "sizes": sizes,
            "times": times,
            "exponent": fit["exponent"],
            "const": fit["const"],
            "us_per_point": [t / N * 1e6 for t, N in zip(times, sizes)],
        }
    return out
