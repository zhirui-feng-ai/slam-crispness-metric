"""
Experiment 2 — Tier separability & noise robustness.

Two questions:
  (a) Separability — can the metric tell a CLEAN segment from a DRIFTED one?
      Measured as Mann-Whitney AUC of clean (level 0) vs each tier's samples.
  (b) Noise robustness — does the metric stay flat under REALISTIC zero-mean
      sensor noise (σ_r ≤ 0.06 m)? A metric that craters on benign noise raises
      false alarms. Measured as 1 − fractional score drop over a fine noise sweep.

Outputs
  results/exp02_separability.json
  figures/f3_tier_separability.png      metric × tier AUC heatmap
  figures/f8_noise_robustness.png       score vs realistic σ_r
"""

from __future__ import annotations
import numpy as np
import pandas as pd

from harness import (one_sample, save_json, FIGURES, RESULTS, SCENES_CORE)
from slam_synthbench import plotting as P
from slam_synthbench.metrics import REFERENCE_FREE, METRIC_INFO
from slam_synthbench.evaluation import separability, noise_robustness

TIERS = ["bias", "catastrophic", "phenomenological"]
# realistic LiDAR noise: σ_r = 0.02 + level*0.13 → level≤0.31 keeps σ_r ≤ 0.06 m
NOISE_LEVELS = [0.0, 0.08, 0.15, 0.23, 0.31]
SEEDS = [0, 1, 2]


def run():
    df = pd.read_csv(RESULTS / "core_dataset.csv")

    # ── (a) separability: clean (level 0, any mode) vs each tier (level>0) ──
    clean = df[df.level == 0.0]
    auc_mat, d_mat = [], []
    for mk in REFERENCE_FREE:
        auc_row, d_row = [], []
        for tier in TIERS:
            drifted = df[(df.tier == tier) & (df.level > 0)]
            r = separability(clean[mk].values, drifted[mk].values, mk)
            auc_row.append(r["auc"]); d_row.append(r["cohens_d"])
        auc_mat.append(auc_row); d_mat.append(d_row)
    auc_mat = np.array(auc_mat)

    # ── (b) noise robustness over a realistic σ_r range (room) ──
    print("[exp02] realistic noise sweep…")
    noise_rows = []
    for lvl in NOISE_LEVELS:
        for seed in SEEDS:
            noise_rows.append(one_sample("room", "sensor_noise", lvl, seed))
    ndf = pd.DataFrame(noise_rows)
    ndf["sigma_r"] = ndf["realized.range_noise_sigma"]
    robust = {}
    for mk in REFERENCE_FREE:
        g = ndf.groupby("sigma_r")[mk].mean().reset_index()
        robust[mk] = noise_robustness(g["sigma_r"].values, g[mk].values, mk)["noise_robustness"]

    save_json({
        "auc": {METRIC_INFO[mk].key: dict(zip(TIERS, auc_mat[i].tolist()))
                for i, mk in enumerate(REFERENCE_FREE)},
        "noise_robustness": robust,
    }, "exp02_separability")

    # ── figures ──
    P.heatmap(auc_mat, [METRIC_INFO[k].label for k in REFERENCE_FREE], TIERS,
              FIGURES / "f3_tier_separability.png",
              "F3 · Clean-vs-drifted separability (Mann-Whitney AUC)",
              cbar_label="AUC (0.5 = blind, 1.0 = perfect)",
              cmap="RdYlGn", vmin=0.5, vmax=1.0)

    series = {mk: ndf.groupby("sigma_r")[mk].mean().values for mk in REFERENCE_FREE}
    sigmas = sorted(ndf["sigma_r"].unique())
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for mk in REFERENCE_FREE:
        y = series[mk]; y = (y - y.min()) / (y.max() - y.min() + 1e-9)
        ax.plot(sigmas, y, "-o", ms=3, color=P.METRIC_COLORS.get(mk), label=METRIC_INFO[mk].label)
    ax.axvspan(0.02, 0.04, color="#3fb950", alpha=0.12)
    ax.text(0.03, 0.02, "realistic\nLiDAR", fontsize=7, color="#3fb950", ha="center")
    ax.set_xlabel("range noise σ_r (m)"); ax.set_ylabel("score (normalized)")
    ax.set_title("F8 · Noise robustness — score vs zero-mean range jitter (room)")
    ax.grid(True, alpha=0.4); ax.legend(fontsize=8, framealpha=0.2)
    fig.tight_layout(); fig.savefig(FIGURES / "f8_noise_robustness.png", dpi=130); plt.close(fig)

    print("[exp02] noise robustness (1 = ignores benign noise):")
    for k, v in sorted(robust.items(), key=lambda kv: -kv[1]):
        print(f"         {METRIC_INFO[k].label:18s} {v:+.3f}")


if __name__ == "__main__":
    run()
