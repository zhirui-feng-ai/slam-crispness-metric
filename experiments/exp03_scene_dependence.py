"""
Experiment 3 — Scene dependence.

Question: does a metric's CLEAN score hold across the geometric-conditioning
spectrum (room → parking → highway → corridor → tunnel)? A scene-dependent
metric needs scene-conditional thresholds in production — a deployment cost.
This is the documented MOM weakness (research-map-quality-metrics): it craters
in feature-sparse scenes even when the map is clean.

Outputs
  results/exp03_scene_dependence.json
  figures/f4_scene_dependence.png   clean score per metric across all 5 scenes
"""

from __future__ import annotations
import numpy as np
import pandas as pd

from harness import one_sample, save_json, FIGURES
from slam_synthbench import plotting as P
from slam_synthbench import SCENE_ORDER
from slam_synthbench.metrics import REFERENCE_FREE, METRIC_INFO
from slam_synthbench.evaluation import scene_independence

SEEDS = [0, 1, 2]


def run():
    print("[exp03] clean-score scan across all scenes…")
    rows = []
    for scene in SCENE_ORDER:
        for seed in SEEDS:
            # level 0 of any mode → clean cloud; use sensor_noise at baseline σ
            rows.append(one_sample(scene, "sensor_noise", 0.0, seed))
    df = pd.DataFrame(rows)

    clean_by_scene = {sc: df[df.scene == sc] for sc in SCENE_ORDER}
    si, table = {}, {}
    for mk in REFERENCE_FREE:
        per_scene = {sc: clean_by_scene[sc][mk].values for sc in SCENE_ORDER}
        si[mk] = scene_independence(per_scene, mk)["scene_independence"]
        table[mk] = {sc: float(np.mean(v)) for sc, v in per_scene.items()}

    save_json({"clean_score": table, "scene_independence": si}, "exp03_scene_dependence")

    series = {mk: [table[mk][sc] for sc in SCENE_ORDER] for mk in REFERENCE_FREE}
    P.grouped_bars(SCENE_ORDER, series, FIGURES / "f4_scene_dependence.png",
                   ylabel="clean-cloud metric score",
                   title="F4 · Scene dependence — clean score across conditioning spectrum")

    print("[exp03] scene-independence (1 = scene-invariant):")
    for k, v in sorted(si.items(), key=lambda kv: -kv[1]):
        print(f"         {METRIC_INFO[k].label:18s} {v:+.3f}")


if __name__ == "__main__":
    run()
