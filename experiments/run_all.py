"""
run_all.py — run every experiment in order, then assemble the metric scorecard.

The scorecard collapses the five experiments into one comparable table (rows =
reference-free metric candidates, columns = the PLAN's evaluation dimensions),
each oriented so higher = better:

  Sensitivity     mean monotonicity over pose-smear modes, across scenes (exp01)
  Oracle agree    Spearman |ρ| with the chamfer oracle (exp01)
  Separability    mean clean-vs-tier AUC (exp02)
  Noise robust    flatness under realistic σ_r (exp02)
  Scene indep.    1 − CoV of clean score across scenes (exp03)
  Compute         1 / (1 + ms@200k) rescaled — faster is higher (exp04)

Outputs results/scorecard.{json,csv} and figures/f0_scorecard.png.
"""

from __future__ import annotations
import json
import numpy as np
import pandas as pd

from harness import RESULTS, FIGURES, save_json
from slam_synthbench.metrics import REFERENCE_FREE, METRIC_INFO
from slam_synthbench import plotting as P

import exp01_sensitivity, exp02_separability, exp03_scene_dependence
import exp04_complexity, exp05_imu_grade

SMEAR_MODES = ["accel_bias", "gyro_bias", "geometric_degeneracy",
               "imu_saturation", "random_walk"]
SCENES = ["room", "highway", "tunnel"]


def _load(name):
    with open(RESULTS / f"{name}.json") as f:
        return json.load(f)


def build_scorecard():
    s1 = _load("exp01_sensitivity")
    s2 = _load("exp02_separability")
    s3 = _load("exp03_scene_dependence")
    s4 = _load("exp04_complexity")

    rows = {}
    for mk in REFERENCE_FREE:
        mono = [s1["monotonicity"].get(f"{sc}|{mode}|{mk}", np.nan)
                for sc in SCENES for mode in SMEAR_MODES]
        sensitivity = float(np.nanmean(mono))
        oracle = abs(s1["oracle_corr"][mk])
        auc = float(np.nanmean(list(s2["auc"][mk].values())))
        noise = s2["noise_robustness"][mk]
        scene_indep = s3["scene_independence"][mk]
        ms = s4[mk]["times"][-1] * 1e3      # ms at largest N (≈200–400k)
        rows[mk] = dict(sensitivity=sensitivity, oracle_agreement=oracle,
                        separability=auc, noise_robustness=noise,
                        scene_independence=scene_indep, compute_ms=ms,
                        exponent=s4[mk]["exponent"])

    df = pd.DataFrame(rows).T
    # compute score: faster = higher, rescaled to [0,1] across candidates
    inv = 1.0 / (1.0 + df["compute_ms"])
    df["compute_score"] = (inv - inv.min()) / (inv.max() - inv.min() + 1e-9)
    return df


def run():
    print("=" * 64)
    for mod in (exp01_sensitivity, exp02_separability, exp03_scene_dependence,
                exp04_complexity, exp05_imu_grade):
        print(f"\n### running {mod.__name__} ###")
        mod.run()

    print("\n### assembling scorecard ###")
    df = build_scorecard()
    df.to_csv(RESULTS / "scorecard.csv")
    save_json(df.to_dict(orient="index"), "scorecard")

    dims = ["sensitivity", "oracle_agreement", "separability",
            "noise_robustness", "scene_independence", "compute_score"]
    mat = df[dims].values.astype(float)
    P.heatmap(mat, [METRIC_INFO[k].label for k in df.index],
              ["Sensitivity", "Oracle\nagree", "Separa-\nbility",
               "Noise\nrobust", "Scene\nindep", "Compute"],
              FIGURES / "f0_scorecard.png",
              "F0 · Metric scorecard (higher = better, per dimension)",
              cbar_label="score", cmap="RdYlGn", vmin=0.0, vmax=1.0)

    pd.set_option("display.width", 160, "display.float_format", lambda v: f"{v:6.3f}")
    print("\n" + "=" * 64 + "\nSCORECARD\n" + "=" * 64)
    print(df[dims + ["compute_ms", "exponent"]].to_string())
    print("\nfigures →", FIGURES)


if __name__ == "__main__":
    run()
