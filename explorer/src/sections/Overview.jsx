import { SCENES, MODES, METRICS, TIERS } from '../data/catalog.js'

const PIPELINE = [
  ['Scene', '5 scenes · room → tunnel'],
  ['Trajectory', '30 s window · 60 km/h · 10 Hz'],
  ['Drift', '3 tiers · 18 modes'],
  ['Cloud', 'reference vs observed'],
  ['Metrics', '6 candidates'],
  ['Scorecard', '6 evaluation axes'],
]

const FINDINGS = [
  ['kNN MME (true) is the accuracy winner', 'Best sensitivity (0.98), oracle agreement (0.92) and separability (0.89) — the only candidate that tracks true drift across every failure mode, at competitive compute.', 'var(--green)'],
  ['Voxel-PCA has a geometric-degeneracy blind spot', 'In tunnels/highways, along-axis drift slides points along the surface → planarity preserved → the metric stays ≈0.99 even at 19 m of true drift.', 'var(--red)'],
  ['Realistic sensor noise is benign', 'At σ_r ≤ 6 cm every candidate is robust — confirming the research thesis that zero-mean noise should not trip a crispness guard.', 'var(--accent)'],
  ['Dynamic ghosting is nearly invisible', 'No reference-free metric reliably catches moving-object trails — route that to dynamic removal, not crispness.', 'var(--orange)'],
]

export default function Overview({ go }) {
  return (
    <div>
      <div className="sec-tag">Synthetic Experiment</div>
      <h1 className="sec-title">SynthBench Explorer</h1>
      <p className="sec-desc">
        Interactive front-end for the 3D synthetic-drift benchmark that evaluates SLAM
        pointcloud-crispness metric candidates. Browse the scorecard, replot the full
        sweep, inspect every scene / drift mode / metric, and read the generated figures
        and reports — all from the experiment outputs already computed by
        <span className="kbd"> run_all.py</span>.
      </p>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="label-sm" style={{ marginBottom: 14 }}>The pipeline</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
          {PIPELINE.map(([t, s], i) => (
            <div key={t} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px' }}>
                <div style={{ fontWeight: 700, fontSize: 13 }}>{t}</div>
                <div style={{ fontSize: 11, color: 'var(--muted2)' }}>{s}</div>
              </div>
              {i < PIPELINE.length - 1 && <span style={{ color: 'var(--muted2)' }}>→</span>}
            </div>
          ))}
        </div>
      </div>

      <div className="grid g3" style={{ marginBottom: 24 }}>
        {[['5', 'scenes', 'room · parking · highway · corridor · tunnel'],
          ['18', 'drift modes', '3 research tiers + 7 legacy patterns'],
          ['6', 'metrics', 'benchmarked on 6 evaluation axes'],
          ['432', 'samples', 'scenes × modes × levels × seeds'],
          ['9', 'figures', 'generated, with reports'],
          ['0.4 s', 'per sample', '3D LiDAR sim + 6 metrics']].map(([n, l, s]) => (
          <div className="card card-sm" key={l}>
            <div style={{ fontSize: 26, fontWeight: 700, color: 'var(--accent)' }}>{n}</div>
            <div style={{ fontWeight: 600, fontSize: 13 }}>{l}</div>
            <div style={{ fontSize: 12, color: 'var(--muted2)' }}>{s}</div>
          </div>
        ))}
      </div>

      <div className="label-sm" style={{ marginBottom: 12 }}>Key findings</div>
      <div className="grid g2" style={{ marginBottom: 24 }}>
        {FINDINGS.map(([t, s, c]) => (
          <div className="card card-sm" key={t} style={{ borderLeft: `3px solid ${c}` }}>
            <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>{t}</div>
            <div style={{ fontSize: 13, color: 'var(--muted)' }}>{s}</div>
          </div>
        ))}
      </div>

      <div className="card" style={{ background: 'var(--surface2)' }}>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button className="btn active" onClick={() => go('learn')}>→ New to the math? Start here</button>
          <button className="btn" onClick={() => go('scorecard')}>See the scorecard</button>
          <button className="btn" onClick={() => go('dataset')}>Explore the dataset</button>
          <button className="btn" onClick={() => go('catalog')}>Browse scenes / modes / metrics</button>
          <button className="btn" onClick={() => go('reports')}>Read the full report</button>
        </div>
      </div>
    </div>
  )
}
