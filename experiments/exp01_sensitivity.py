"""
Experiment 1 — Sensitivity & oracle agreement.

Question: does each metric fall monotonically as drift grows, and does a
reference-free metric track the (reference-based) chamfer oracle — i.e. does it
measure *true* drift, not an artifact?

Outputs
  results/core_dataset.csv      the shared sweep (reused by exp02)
  results/exp01_sensitivity.json  monotonicity ρ per (metric, scene, mode) + oracle corr
  figures/f1_sensitivity_grid.png  score-vs-severity, one panel per mode (room)
  figures/f2_monotonicity_heatmap.png  metric × mode monotonicity (room)
  figures/f7_oracle_correlation.png    which reference-free metric best tracks the oracle
"""

from __future__ import annotations
import numpy as np
from scipy.stats import spearmanr

from harness import (gen_dataset, save_df, save_json, FIGURES,
                     SCENES_CORE, MODES_CORE)
from slam_synthbench import plotting as P
from slam_synthbench.metrics import REFERENCE_FREE, METRIC_INFO
from slam_synthbench.evaluation import sensitivity

LEVELS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
SEEDS = [0, 1, 2]
ALL_METRICS = list(METRIC_INFO)


def run():
    print("[exp01] generating core dataset (scenes × modes × levels × seeds)…")
    df = gen_dataset(SCENES_CORE, MODES_CORE, LEVELS, SEEDS)
    save_df(df, "core_dataset")

    # ── monotonicity ρ(level, score) per (metric, scene, mode) ──
    mono = {}
    for scene in SCENES_CORE:
        for mode in MODES_CORE:
            sub = df[(df.scene == scene) & (df["mode"] == mode)]
            for mk in ALL_METRICS:
                s = sensitivity(sub["level"].values, sub[mk].values, mk)
                mono[f"{scene}|{mode}|{mk}"] = s["monotonicity"]

    # ── oracle agreement: Spearman(ref-free score, chamfer) WITHIN each
    #    (scene, mode), averaged. Pooling across scenes confounds the measure
    #    (tunnel chamfer ≫ room chamfer at equal score), so we de-confound by
    #    grouping — this is "does the metric track true drift, given the scene". ──
    smear = df[df.drift_intensity > 0]
    oracle_corr = {}
    for mk in REFERENCE_FREE:
        rhos = []
        for (_sc, _mode), s in smear.groupby(["scene", "mode"]):
            if s["drift_intensity"].nunique() <= 2:
                continue
            x, y = s[mk].values, s["chamfer_oracle"].values
            m = np.isfinite(x) & np.isfinite(y)
            if m.sum() <= 3:
                continue
            rho, _ = spearmanr(x[m], y[m])
            rhos.append(-rho if METRIC_INFO[mk].higher_is_better else rho)
        oracle_corr[mk] = float(np.nanmean(rhos)) if rhos else float("nan")

    save_json({"monotonicity": mono, "oracle_corr": oracle_corr}, "exp01_sensitivity")

    # ── figures ──
    room = df[df.scene == "room"]
    P.sensitivity_grid(room, ALL_METRICS, MODES_CORE, FIGURES / "f1_sensitivity_grid.png",
                       title="F1 · Metric response by failure mode (room scene)")

    # monotonicity heatmap: metrics × modes (room)
    mat = np.array([[mono[f"room|{mode}|{mk}"] for mode in MODES_CORE] for mk in ALL_METRICS])
    P.heatmap(mat, [METRIC_INFO[k].label for k in ALL_METRICS], MODES_CORE,
              FIGURES / "f2_monotonicity_heatmap.png",
              "F2 · Sensitivity (monotonicity ρ↓ vs severity) — room",
              cbar_label="−ρ  (+1 = score falls as drift grows)",
              cmap="RdYlGn", vmin=-1, vmax=1)

    P.correlation_bars(oracle_corr, FIGURES / "f7_oracle_correlation.png",
                       title="F7 · Reference-free agreement with chamfer oracle (within scene×mode)")

    print("[exp01] oracle agreement (|ρ| vs true drift):")
    for k, v in sorted(oracle_corr.items(), key=lambda kv: -abs(kv[1])):
        print(f"         {METRIC_INFO[k].label:18s} {v:+.3f}")
    return df


if __name__ == "__main__":
    run()
