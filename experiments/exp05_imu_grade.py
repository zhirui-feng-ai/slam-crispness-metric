"""
Experiment 5 — IMU-grade response (the open question from research-imu-grades).

"Does crispness degrade gracefully across IMU grades or cliff at consumer?"
We inject each grade's calibrated unaided 30 s drift (t³ gyro-bias-dominated,
from the research position-error table) and watch the metrics. The grades span
~800× in drift magnitude (consumer ~50 m → navigation ~0.06 m at 30 s), so the
question is where each metric saturates vs stays discriminative.

Outputs
  results/exp05_imu_grade.json
  figures/f6_imu_grade.png   metric score vs IMU grade (consumer → navigation)
"""

from __future__ import annotations
import numpy as np
import pandas as pd

from harness import one_sample, save_json, FIGURES
from slam_synthbench import IMU_GRADE_ORDER, IMU_GRADES
from slam_synthbench.metrics import REFERENCE_FREE, METRIC_INFO
from slam_synthbench import plotting as P
import matplotlib.pyplot as plt

SEEDS = [0, 1, 2]
SCENE = "highway"   # 120 m scene: large-drift grades stay within scene scale


def run():
    print("[exp05] IMU-grade sweep (calibrated unaided drift)…")
    rows = []
    for grade in IMU_GRADE_ORDER:
        for seed in SEEDS:
            rows.append(one_sample(SCENE, f"imu_{grade}", 1.0, seed))
    df = pd.DataFrame(rows)
    df["grade"] = df["mode"].str.replace("imu_", "")

    table, realized = {}, {}
    for grade in IMU_GRADE_ORDER:
        g = df[df.grade == grade]
        realized[grade] = float(g["drift_intensity"].mean())
        for mk in REFERENCE_FREE + ["chamfer_oracle"]:
            table.setdefault(mk, {})[grade] = float(g[mk].mean())

    save_json({"score_by_grade": table, "drift_intensity_by_grade": realized,
               "grade_specs": {g: vars(IMU_GRADES[g]) for g in IMU_GRADE_ORDER}},
              "exp05_imu_grade")

    # Two panels: (L) normalized curves with RAW range annotated so flat metrics
    # are visible as flat; (R) "grade discrimination" = relative raw spread —
    # how much each metric actually moves across the 800× drift range.
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12, 4.4),
                                   gridspec_kw={"width_ratios": [1.5, 1]})
    x = np.arange(len(IMU_GRADE_ORDER))
    discrimination = {}
    for mk in REFERENCE_FREE:
        raw = np.array([table[mk][g] for g in IMU_GRADE_ORDER])
        lo, hi = raw.min(), raw.max()
        discrimination[mk] = float((hi - lo) / (abs(hi) + 1e-9))   # relative spread
        y = (raw - lo) / (hi - lo + 1e-9)
        axL.plot(x, y, "-o", ms=4, color=P.METRIC_COLORS.get(mk),
                 label=f"{METRIC_INFO[mk].label}  [{lo:.2f}–{hi:.2f}]")
    axL.set_xticks(x)
    axL.set_xticklabels([f"{g}\n({realized[g]:.2f} m)" for g in IMU_GRADE_ORDER], fontsize=8)
    axL.set_xlabel("IMU grade  (mean injected 30 s drift)")
    axL.set_ylabel("score (per-metric normalized)")
    axL.set_title(f"Response across IMU grades — {SCENE}")
    axL.grid(True, alpha=0.4); axL.legend(fontsize=7.5, framealpha=0.2)

    order = sorted(discrimination, key=lambda k: discrimination[k])
    axR.barh([METRIC_INFO[k].label for k in order], [discrimination[k] for k in order],
             color=[P.METRIC_COLORS.get(k) for k in order])
    for i, k in enumerate(order):
        axR.text(discrimination[k] + 0.005, i, f"{discrimination[k]*100:.1f}%", va="center", fontsize=8)
    axR.set_xlabel("relative raw spread across grades")
    axR.set_title("Grade discrimination (higher = less blind)")
    axR.grid(True, axis="x", alpha=0.35)
    fig.suptitle("F6 · Can the metric tell IMU grades apart? (consumer 19 m → navigation 0.02 m)")
    fig.tight_layout(); fig.savefig(FIGURES / "f6_imu_grade.png", dpi=130); plt.close(fig)
    save_json({"discrimination": discrimination}, "exp05_discrimination")

    print("[exp05] mean injected drift by grade:")
    for g in IMU_GRADE_ORDER:
        print(f"         {g:12s} {realized[g]:7.3f} m  "
              f"PCA={table['voxel_pca_crispness'][g]:.3f}  oracle={table['chamfer_oracle'][g]:.3f}")


if __name__ == "__main__":
    run()
