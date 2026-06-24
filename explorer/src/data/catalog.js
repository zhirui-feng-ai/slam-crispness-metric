// Catalog metadata mirrored from the slam_synthbench package (scenes.py,
// drift.py, metrics.py). Kept in sync by hand — small and stable.

export const METRIC_COLORS = {
  voxel_pca_crispness: '#4361ee',
  mme_grid: '#059669',
  mom_planarity: '#ef4444',
  bev_edge_density: '#f59e0b',
  knn_entropy_mme: '#8b5cf6',
  chamfer_oracle: '#8688b4',
}

export const METRICS = [
  { key: 'voxel_pca_crispness', label: 'Voxel PCA', higher: true, ref_free: true, complexity: 'O(N)',
    def: '1 − mean(λ₃/λ₁) over voxels. Healthy maps are locally planar (λ₃≈0).',
    note: 'Original primary candidate. Cheap, noise-robust, scene-invariant on clean maps — but blind to along-axis degeneracy drift.' },
  { key: 'mme_grid', label: 'MME (grid)', higher: true, ref_free: true, complexity: 'O(N)',
    def: '1/(1 + mean(λ₃)/scale). Grid approximation of Mean Map Entropy.',
    note: 'Entropy proxy via the minor eigenvalue (surface thickness).' },
  { key: 'mom_planarity', label: 'MOM planarity', higher: true, ref_free: true, complexity: 'O(N)',
    def: 'planar-fraction × normal-diversity (voxels below a planarity threshold).',
    note: 'Threshold-based; best separability but lower sensitivity. Documented scene dependence in feature-sparse scenes.' },
  { key: 'bev_edge_density', label: 'BEV edge density', higher: true, ref_free: true, complexity: 'O(N)',
    def: 'Sobel energy of a top-down density image. Crisp thin walls → sharp gradients.',
    note: 'PLAN’s 4th candidate. ~23× cheaper than voxel metrics but weak sensitivity/separability and scene-dependent — a cheap pre-filter at best.' },
  { key: 'knn_entropy_mme', label: 'kNN MME (true)', higher: true, ref_free: true, complexity: 'O(N log N)',
    def: '−mean log det(Σ_kNN), k=12, on a fixed query subsample. True Mean Map Entropy.',
    note: 'The accuracy winner: best sensitivity, oracle agreement, separability, and the only metric that tracks IMU grade in degenerate scenes.' },
  { key: 'chamfer_oracle', label: 'Chamfer (oracle)', higher: false, ref_free: false, complexity: 'O(N log N)',
    def: 'Symmetric nearest-neighbour distance to the ideal reference cloud (meters).',
    note: 'Not productionizable (needs the ideal map) — the ground-truth yardstick every reference-free metric is scored against.' },
]

export const SCENES = [
  { key: 'room', label: 'Room', conditioning: 'well-conditioned',
    desc: '4 walls + floor + ceiling + obstacle; planar structure in every direction.', degenerate: 'none' },
  { key: 'parking', label: 'Parking', conditioning: 'structured but sparse',
    desc: 'Underground-parking analog: perimeter walls + pillar grid.', degenerate: 'none' },
  { key: 'highway', label: 'Highway', conditioning: 'feature-sparse open',
    desc: 'Ground plane + thin guardrails + sparse roadside signs; weak along-track constraint.', degenerate: 'along-track (x)' },
  { key: 'corridor', label: 'Corridor', conditioning: 'mildly degenerate',
    desc: 'Long end-capped hallway; weak along-axis constraint.', degenerate: 'along-track (x)' },
  { key: 'tunnel', label: 'Tunnel', conditioning: 'strongly degenerate',
    desc: 'Symmetric tube, no along-axis features → translation along x geometrically unobservable.', degenerate: 'along-track (x)' },
]

export const TIERS = {
  noise: { label: 'Noise', blurb: 'Zero-mean, benign — a good metric should NOT fire.' },
  bias: { label: 'Systematic bias', blurb: 'Monotonic surface smear — the target the metric must catch.' },
  catastrophic: { label: 'Catastrophic', blurb: 'Degeneracy / dynamics / weather / saturation — crispness should crater.' },
  phenomenological: { label: 'Phenomenological', blurb: 'The original 7 patterns, recalibrated to physical units (legacy baseline).' },
}

export const MODES = [
  { key: 'sensor_noise', tier: 'noise', desc: 'Zero-mean per-point range jitter (σ_r 0.02→0.15 m). No pose error.', model: 'σ_r ∈ [0.02, 0.15] m' },
  { key: 'accel_bias', tier: 'bias', desc: 'Constant accelerometer bias → quadratic position drift.', model: 'δp = ½·b_a·t²,  b_a ≤ 0.01 m/s²' },
  { key: 'gyro_bias', tier: 'bias', desc: 'Gyro bias → tilt → gravity-coupled cubic position drift.', model: 'δp = ⅙·g·b_g·t³,  b_g ≤ 1e-4 rad/s' },
  { key: 'imu_consumer', tier: 'bias', desc: 'Consumer-grade IMU unaided drift (≈19 m / 30 s).', model: 't³ shape, 100 °/h gyro bias' },
  { key: 'imu_industrial', tier: 'bias', desc: 'Industrial-grade IMU unaided drift (≈1.9 m / 30 s).', model: 't³ shape, 8 °/h gyro bias' },
  { key: 'imu_tactical', tier: 'bias', desc: 'Tactical-grade IMU unaided drift (≈0.24 m / 30 s).', model: 't³ shape, 0.5 °/h gyro bias' },
  { key: 'imu_navigation', tier: 'bias', desc: 'Navigation-grade IMU unaided drift (≈0.02 m / 30 s).', model: 't³ shape, 0.02 °/h gyro bias' },
  { key: 'dynamic_objects', tier: 'catastrophic', desc: '1–6 moving cars leave ghost trails; ego pose unaffected.', model: 'transient quads swept over time' },
  { key: 'geometric_degeneracy', tier: 'catastrophic', desc: 'ICP “slide” along the scene’s unconstrained axis.', model: 'random-walk + creep along degenerate axis' },
  { key: 'weather_dropout', tier: 'catastrophic', desc: 'Rain/fog: up to 60% point dropout + range collapse 80→25 m.', model: 'dropout + max-range collapse' },
  { key: 'imu_saturation', tier: 'catastrophic', desc: 'Gyro clip in a maneuver window → localized rotational smear.', model: 'windowed heading spike + partial recovery' },
  { key: 'random_walk', tier: 'phenomenological', desc: 'Cumulative Gaussian XY + heading per step.', model: 'cumulative Gaussian' },
  { key: 'yaw_bias', tier: 'phenomenological', desc: 'Heading accumulates bias → spiral position error.', model: 'heading bias → spiral' },
  { key: 'range_scale', tier: 'phenomenological', desc: 'LiDAR range slightly scaled (calibration error).', model: 'local distances ×(1+k)' },
  { key: 'loop_closure_seam', tier: 'phenomenological', desc: 'Drift accumulates, snaps to 0 at loop close → wall ghost.', model: 'accumulate then snap' },
  { key: 'sinusoidal', tier: 'phenomenological', desc: 'Periodic pose oscillation (vibration/bounce).', model: 'sinusoidal offset' },
  { key: 'step_jump', tier: 'phenomenological', desc: 'Sudden discrete offset at mid-trajectory → wall split.', model: 'step offset at 50%' },
  { key: 'gyro_saturation', tier: 'phenomenological', desc: 'Pure heading-error accumulation (no position offset).', model: 'cumulative heading drift' },
]

export const DIMENSIONS = [
  { key: 'sensitivity', label: 'Sensitivity', blurb: 'Monotonic score drop as drift grows (−ρ vs severity).' },
  { key: 'oracle_agreement', label: 'Oracle agreement', blurb: 'Within-scene Spearman with the chamfer oracle — does it track TRUE drift?' },
  { key: 'separability', label: 'Separability', blurb: 'Clean-vs-drifted Mann-Whitney AUC.' },
  { key: 'noise_robustness', label: 'Noise robustness', blurb: 'Flatness under realistic σ_r ≤ 0.06 m (1 = ignores benign noise).' },
  { key: 'scene_independence', label: 'Scene independence', blurb: '1 − CoV of the clean score across scenes.' },
  { key: 'compute_score', label: 'Compute', blurb: 'Rescaled inverse runtime — faster is higher.' },
]
