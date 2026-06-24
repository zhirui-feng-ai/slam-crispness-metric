import { figURL } from '../lib/data.js'

const FIGS = [
  ['f0_scorecard.png', 'F0 · Scorecard', 'All metrics × 6 evaluation dimensions, higher = better.'],
  ['f1_sensitivity_grid.png', 'F1 · Sensitivity grid', 'Per-mode metric response vs severity (room) — which metric catches which failure.'],
  ['f2_monotonicity_heatmap.png', 'F2 · Monotonicity', 'Sensitivity (−ρ vs severity) per metric × mode in the room scene.'],
  ['f3_tier_separability.png', 'F3 · Separability', 'Clean-vs-drifted Mann-Whitney AUC per metric × tier.'],
  ['f4_scene_dependence.png', 'F4 · Scene dependence', 'Clean-cloud score across the conditioning spectrum.'],
  ['f5_compute_complexity.png', 'F5 · Compute scaling', 'Log-log metric time vs point count, with fitted exponents.'],
  ['f6_imu_grade.png', 'F6 · IMU grade', 'Response across IMU grades + grade-discrimination bars (consumer 19 m → navigation 0.02 m).'],
  ['f7_oracle_correlation.png', 'F7 · Oracle agreement', 'Within-(scene,mode) Spearman of each reference-free metric with the chamfer oracle.'],
  ['f8_noise_robustness.png', 'F8 · Noise robustness', 'Score vs zero-mean range jitter; the green band is realistic LiDAR noise.'],
]

export default function Figures() {
  return (
    <div>
      <div className="sec-tag">Generated assets</div>
      <h1 className="sec-title">Figure gallery</h1>
      <p className="sec-desc">
        The nine figures produced by <span className="kbd">experiments/run_all.py</span>. Re-running the
        suite and <span className="kbd">npm run sync</span> refreshes them here.
      </p>
      <div className="grid" style={{ gap: 22 }}>
        {FIGS.map(([f, title, cap]) => (
          <div className="fig" key={f}>
            <img src={figURL(f)} alt={title} loading="lazy" />
            <div className="fig-cap"><strong style={{ color: 'var(--text)' }}>{title}</strong> — {cap}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
