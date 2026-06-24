# Methods — Synthetic Drift Benchmark for Crispness-Metric Evaluation

**Author:** Zephyr Feng · **Date:** 2026-06-23 · **Project:** SLAM Pointcloud Crispness

This document specifies *how* the benchmark works and *why* each choice is
grounded in the project research. Results and interpretation are in
[results.md](results.md).

---

## 1. Goal and design principles

We need to choose a production crispness metric. To choose defensibly we must
measure, for each candidate, how it behaves under **realistic road-test error**
and how that behavior changes with **point-cloud complexity** and **failure
mode**. The benchmark is built to be:

- **Physically grounded** — drift magnitudes are in meters/seconds and calibrated
  to the research error budgets, not abstract knobs.
- **Verifiable** — every layer is a small, importable, separately-testable module
  with deterministic, seeded output.
- **Reusable** — the same `slam_synthbench` package drives the automated
  experiments and the interactive notebook; metrics are the exact functions a
  Flyte task would call.
- **Scale-free in evaluation** — metric comparison uses rank statistics
  (Spearman, Mann-Whitney AUC) so candidates on different units are directly
  comparable without hand-tuned normalization.

This re-grounds the original 2D injector in three research findings:

1. **The three-tier taxonomy** (research-failure-modes): *noise* (zero-mean,
   benign, should be invisible), *systematic bias* (monotonic, the target),
   *catastrophic* (degeneracy/dynamics/weather/saturation, should crater).
2. **Error accumulation math** (research-error-accumulation): accel bias →
   position error ∝ t²; gyro bias → ∝ t³ via gravity coupling. Drift is the
   integral of bias; noise averages out.
3. **IMU-grade limits** (research-imu-grades): sensor grade sets the drift
   *coefficient*, not its shape; geometry sets the floor. A per-segment metric
   measures the residual neither removes.

---

## 2. The simulation pipeline

```
scene (3D quads) ──► trajectory (timed 6-DoF poses) ──► drift injection (3 tiers)
                                                              │
                              ┌───────────────────────────────┤
                              ▼                               ▼
                 reference_cloud (ideal)            observed_cloud (drift-corrupted)
                  static · true poses · noise-free    static+dynamic · estimated poses
                              │                          · noise/dropout/range/scale
                              └──────────────┬────────────┘
                                             ▼
                              6 metrics  +  evaluation criteria
```

### 2.1 Scenes (`scenes.py`) — the complexity axis

Five scenes ordered by geometric conditioning, each built from planar **quads**:

| Scene | Conditioning | Degenerate axis |
|---|---|---|
| `room` | well-conditioned (walls/floor/ceiling/obstacle, normals everywhere) | none |
| `parking` | structured but sparse (pillar grid + perimeter) | none |
| `highway` | feature-sparse open (ground + guardrails + sparse signs) | along-track (x) |
| `corridor` | mildly degenerate (long hallway, end-capped) | along-track (x) |
| `tunnel` | strongly degenerate (symmetric tube, no along-axis features) | along-track (x) |

`degenerate_axis` is the world direction the geometry fails to constrain; the
catastrophic *geometric-degeneracy* mode pushes pose error along it — the
synthetic analog of ICP "sliding" in a tunnel (research-failure-modes §1, where
all 7 SOTA methods failed).

### 2.2 Trajectory (`trajectory.py`) — physical time

Poses are 6-vectors `[x,y,z,roll,pitch,yaw]` sampled at 10 Hz over a **30 s**
window at **16.7 m/s (≈60 km/h)** — the crispness operating window from
research-failure-modes §6 (≈500 m / segment). Timestamps are load-bearing: the
bias tier integrates over real seconds so O(t²)/O(t³) growth is physical.

### 2.3 Sensor (`sensor.py`) — configurable 3D LiDAR

A spinning LiDAR casts a ring-stack of beams (default 24–32 beams, 1.5–2.5°
azimuth, −25°…+15° vFOV, 80 m range). Exposed levers map to research questions:
beam count (ATE saturates ~32–64 beams but map density keeps rising), per-point
range noise σ_r (the noise tier), dropout and max-range (weather). Hits are
returned in the **sensor-local frame** so the SLAM re-projection physics applies.

### 2.4 Drift injection (`drift.py`) — three calibrated tiers

Every mode is `f(traj, scene, level, rng) → (pose_errors (N,6), SensorEffects)`.
`level ∈ [0,1]` is severity; each mode maps it to physical magnitude and reports
the realized RMS position error (m).

| Tier | Mode | Physical model |
|---|---|---|
| **noise** | `sensor_noise` | zero-mean range jitter σ_r ∈ [0.02, 0.15] m; no pose error |
| **bias** | `accel_bias` | δp = ½·b_a·t², b_a ∈ [0, 0.01] m/s² |
| **bias** | `gyro_bias` | δp = ⅙·g·b_g·t³ + tilt b_g·t, b_g ∈ [0, 1e-4] rad/s |
| **bias** | `imu_{grade}` | calibrated unaided drift per IMU grade (t³ shape) |
| **catastrophic** | `dynamic_objects` | 1–6 moving cars → ghost trails (no ego error) |
| **catastrophic** | `geometric_degeneracy` | random-walk + creep along the scene's degenerate axis |
| **catastrophic** | `weather_dropout` | up to 60% dropout + range collapse 80→25 m (fog) |
| **catastrophic** | `imu_saturation` | gyro clip in a maneuver window → localized rotational smear |
| **phenomenological** | the original 7 patterns | ported to 3D / physical units (legacy baseline) |

The bias formulas and coefficients (½·b_a·t², ⅙·g·b_g·t³) are the 3-vote-verified
closed forms from research-error-accumulation §1.

### 2.5 Cloud accumulation (`cloud.py`) — the SLAM physics

For each pose: sense from the **true** pose → express the hit in the sensor-local
frame → re-project to world through the **drifted (estimated)** pose. Correct
observations through a wrong pose are exactly what smears a SLAM map. Two clouds
result: the noise-free static **reference** (only the oracle sees it) and the
drift-corrupted **observed** cloud (every reference-free metric scores it).

---

## 3. The six metric candidates (`metrics.py`)

| Metric | Definition | Better | Complexity | Needs ref |
|---|---|---|---|---|
| **Voxel PCA crispness** | 1 − mean(λ₃/λ₁) per voxel | higher | O(N) | no |
| **MME (grid)** | 1/(1 + mean(λ₃)/scale) — grid-approx entropy | higher | O(N) | no |
| **MOM planarity** | planar-fraction × normal-diversity | higher | O(N) | no |
| **BEV edge density** | Sobel energy of top-down density image | higher | O(N) | no |
| **kNN MME (true)** | −mean log det(Σ_kNN), k=12, subsampled | higher | O(N log N) | no |
| **Chamfer (oracle)** | symmetric NN distance to reference | lower | O(N log N) | **yes** |

The four voxel/grid metrics share **one batched PCA pass** (`voxel_pca`):
points are bucketed into a grid, per-voxel 3×3 covariance is computed by
`reduceat` over a sorted index, and all eigenvalues come from a single stacked
`eigh` — no Python loop over voxels. The chamfer oracle is not productionizable
(it needs the ideal map) but is the **ground-truth yardstick**: a reference-free
metric is trustworthy only insofar as it tracks the oracle on true drift.

---

## 4. Evaluation criteria (`evaluation.py`)

Each metric is oriented via `METRIC_INFO.higher_is_better` so larger always
means crisper, then graded on:

- **Sensitivity** — Spearman ρ(severity, score); reported as `−ρ` so +1 = score
  falls monotonically as drift grows. Computed on pose-smear modes only.
- **Oracle agreement** — Spearman |ρ| between the reference-free score and the
  chamfer oracle across all drift samples. Does it measure *true* drift?
- **Separability** — Mann-Whitney AUC of clean (level 0) vs drifted populations
  (0.5 = blind, 1.0 = perfect), plus Cohen's d.
- **Scene-independence** — 1 − coefficient-of-variation of the clean score across
  the five scenes (1 = scene-invariant). A scene-dependent metric needs
  scene-conditional thresholds in production.
- **Noise-robustness** — 1 − fractional score drop across a *realistic* σ_r sweep
  (≤ 0.06 m). A metric that craters on benign noise raises false alarms.
- **Compute** — measured wall-clock vs N with a fitted log-log exponent.

---

## 5. The five experiments (`experiments/`)

| Script | Produces | Core question |
|---|---|---|
| `exp01_sensitivity.py` | core_dataset.csv, f1/f2/f7 | monotonic response + oracle agreement |
| `exp02_separability.py` | f3, f8 | clean-vs-drift AUC + noise robustness |
| `exp03_scene_dependence.py` | f4 | clean score across the complexity spectrum |
| `exp04_complexity.py` | f5 | compute cost and scaling exponent |
| `exp05_imu_grade.py` | f6 | graceful degradation vs cliff across IMU grades |
| `run_all.py` | scorecard.{csv,json}, f0 | assemble the comparable scorecard |

### Sampling policy (why random, not voxel)
Scoring runs on a **random** downsample (cap 80k points), never a voxel
downsample. Voxel downsampling collapses each cell to a centroid and silently
*denoises* the cloud — which would let a metric look noise-robust for the wrong
reason. Random downsampling preserves per-point spread and density, so the noise
tier is evaluated fairly. `sampling.py` also provides voxel and farthest-point
samplers for the point-cloud-complexity studies in the notebook.

### Reproducibility
All randomness is seeded (`numpy.random.default_rng(seed)`); every experiment
sweeps multiple seeds and reports means. Re-running `run_all.py` reproduces the
CSVs, JSONs, and figures bit-for-bit per seed.

---

## 6. Known limitations

- **2D ray-casting against planar quads** approximates LiDAR returns; real scenes
  have curved/clutter surfaces that add baseline non-planarity. Conclusions are
  *relative* (metric vs metric), which is what the metric choice needs.
- **Dynamic objects** are rigid boxes swept along straight lanes — a first-order
  ghost-trail model, not full multi-agent traffic.
- **No back-end** — we inject the *symptom* (a corrupted map from a wrong pose
  trajectory), not a SLAM optimizer. That is deliberate: the metric runs on the
  output map, so the map is what we must reproduce.
- Absolute metric values are simulator-specific; **only rank-based comparisons
  transfer** to real data. Real-data validation is Week 2–3 of the PLAN.
