# Synthetic Experiment — Crispness Metric Evaluation

A self-contained, reproducible harness that uses **synthetic SLAM-drift
injection** to evaluate candidate pointcloud-crispness metrics on the axes that
decide production fitness: **sensitivity, separability, scene-independence,
noise-robustness, and compute cost** — and how each changes with **point-cloud
complexity** and **failure mode**.

This is the 3D successor to the original 2D [`drift-injector/`](../drift-injector).
It re-grounds drift in the project's research: the three-tier error taxonomy
(noise / systematic bias / catastrophic), calibrated IMU-grade bias growth
(O(t²)/O(t³)), and the real failure modes (tunnel degeneracy, dynamic-object
ghosting, weather dropout, IMU saturation). See [research/](../research).

## Layout

```
synthetic-experiment/
├── slam_synthbench/        reusable package (verified, importable)
│   ├── geometry.py         SE(3) poses, quads, vectorized 3D ray caster
│   ├── scenes.py           5 scenes: room→parking→highway→corridor→tunnel
│   ├── trajectory.py       timed 3D pose paths (the 30 s operating window)
│   ├── sensor.py           configurable spinning-LiDAR model (beams, noise, dropout)
│   ├── drift.py            3-tier physical drift injection + IMU grades + 7 legacy patterns
│   ├── cloud.py            reference (ideal) vs observed (drift-corrupted) maps
│   ├── metrics.py          6 candidates, shared batched voxel-PCA, compute-instrumented
│   ├── sampling.py         voxel / random / farthest-point downsampling
│   ├── evaluation.py       scorecard criteria (rank-based, scale-free)
│   ├── profiling.py        compute-cost timing + log-log exponent fit
│   └── plotting.py         shared figure layer
├── experiments/            one script per question + run_all.py + results/
├── figures/                generated PNGs (f0…f8)
├── reports/                methods.md + results.md
├── notebooks/explore.ipynb interactive walkthrough
├── explorer/               static React + Vite front-end (browse everything)
└── .venv/                  local environment (numpy/scipy/matplotlib/pandas/jupyter)
```

## Quick start

```bash
cd synthetic-experiment
python -m venv .venv && ./.venv/bin/pip install -r requirements.txt   # first time

# run everything (≈5 min) → results/, figures/, scorecard
./.venv/bin/python experiments/run_all.py

# or one question at a time
./.venv/bin/python experiments/exp04_complexity.py

# explore interactively (notebook)
./.venv/bin/jupyter notebook notebooks/explore.ipynb

# or the web explorer (scorecard, dataset replot, catalogs, figures, reports)
cd explorer && npm install && npm run dev    # → http://localhost:5173
```

Minimal use of the library:

```python
import slam_synthbench as sb
s = sb.make_sample(scene_name="tunnel", mode="gyro_bias", level=0.6, keep_clouds=True)
print(s.drift_intensity, s.scores)   # RMS pose error (m) + all 6 metric scores
```

## The five experiments

| # | Question | Figure |
|---|---|---|
| 1 | Does each metric fall monotonically with drift, and track the oracle? | f1, f2, f7 |
| 2 | Can it separate clean from drifted? Does it ignore benign noise? | f3, f8 |
| 3 | Does the clean score hold across the scene-complexity spectrum? | f4 |
| 4 | What does each metric cost, and how does it scale? | f5 |
| 5 | Does crispness degrade gracefully across IMU grades or cliff? | f6 |

Results, scorecard, and interpretation: [reports/results.md](reports/results.md).
Design and physical grounding: [reports/methods.md](reports/methods.md).
