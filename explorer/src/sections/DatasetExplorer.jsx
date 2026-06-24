import { useMemo, useState } from 'react'
import { useCSV } from '../lib/data.js'
import { fmt } from '../lib/ui.js'
import { METRICS, METRIC_COLORS, MODES, TIERS } from '../data/catalog.js'

const PLOTTABLE = METRICS.map(m => m.key)            // 5 ref-free + chamfer oracle
const LABEL = Object.fromEntries(METRICS.map(m => [m.key, m.label]))

// modes/scenes present in the core sweep
const CORE_MODES = ['sensor_noise', 'accel_bias', 'gyro_bias', 'dynamic_objects',
  'geometric_degeneracy', 'weather_dropout', 'imu_saturation', 'random_walk']
const CORE_SCENES = ['room', 'highway', 'tunnel']

function groupMean(rows, xKey, metricKeys) {
  const by = new Map()
  for (const r of rows) {
    const x = r[xKey]
    if (!by.has(x)) by.set(x, [])
    by.get(x).push(r)
  }
  return [...by.entries()].map(([x, rs]) => {
    const o = { x }
    for (const k of metricKeys) {
      const vals = rs.map(r => r[k]).filter(v => typeof v === 'number' && !Number.isNaN(v))
      o[k] = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : NaN
    }
    return o
  }).sort((a, b) => a.x - b.x)
}

function Chart({ pts, keys, normalize, xLabel }) {
  const W = 720, H = 380, PAD = { l: 52, r: 16, t: 18, b: 46 }
  const cw = W - PAD.l - PAD.r, ch = H - PAD.t - PAD.b
  const xs = pts.map(p => p.x)
  const xmin = Math.min(...xs), xmax = Math.max(...xs)
  const toX = x => PAD.l + (xmax === xmin ? 0.5 : (x - xmin) / (xmax - xmin)) * cw

  // per-metric min/max for normalization
  const range = {}
  keys.forEach(k => {
    const vs = pts.map(p => p[k]).filter(v => !Number.isNaN(v))
    range[k] = [Math.min(...vs), Math.max(...vs)]
  })
  const toY = (k, v) => {
    let t
    if (normalize) {
      const [lo, hi] = range[k]; t = hi === lo ? 0.5 : (v - lo) / (hi - lo)
    } else { t = v }  // assumes already [0,1]-ish; raw mode only sensible for normalize off on bounded metrics
    return PAD.t + (1 - t) * ch
  }

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', background: '#fff', borderRadius: 8 }}>
      {[0, 0.25, 0.5, 0.75, 1].map(g => (
        <g key={g}>
          <line x1={PAD.l} x2={PAD.l + cw} y1={PAD.t + (1 - g) * ch} y2={PAD.t + (1 - g) * ch} stroke="#e4e8ff" />
          <text x={PAD.l - 8} y={PAD.t + (1 - g) * ch + 4} fontSize="10" fill="#8688b4" textAnchor="end">{g.toFixed(2)}</text>
        </g>
      ))}
      {pts.map(p => (
        <text key={p.x} x={toX(p.x)} y={H - PAD.b + 16} fontSize="10" fill="#8688b4" textAnchor="middle">{fmt(p.x, 2)}</text>
      ))}
      <text x={PAD.l + cw / 2} y={H - 6} fontSize="11" fill="#4b4e8a" textAnchor="middle">{xLabel}</text>
      <text x={14} y={PAD.t + ch / 2} fontSize="11" fill="#4b4e8a" textAnchor="middle"
            transform={`rotate(-90 14 ${PAD.t + ch / 2})`}>{normalize ? 'score (normalized)' : 'score'}</text>
      {keys.map(k => {
        const d = pts.filter(p => !Number.isNaN(p[k]))
          .map((p, i) => `${i ? 'L' : 'M'}${toX(p.x).toFixed(1)} ${toY(k, p[k]).toFixed(1)}`).join(' ')
        const dashed = k === 'chamfer_oracle'
        return (
          <g key={k}>
            <path d={d} fill="none" stroke={METRIC_COLORS[k]} strokeWidth="2.4"
                  strokeDasharray={dashed ? '5 4' : 'none'} />
            {pts.filter(p => !Number.isNaN(p[k])).map(p => (
              <circle key={p.x} cx={toX(p.x)} cy={toY(k, p[k])} r="3.2" fill={METRIC_COLORS[k]} />
            ))}
          </g>
        )
      })}
    </svg>
  )
}

export default function DatasetExplorer() {
  const { data: rows, error } = useCSV('data/core_dataset.csv')
  const [scene, setScene] = useState('tunnel')
  const [mode, setMode] = useState('gyro_bias')
  const [sel, setSel] = useState(['voxel_pca_crispness', 'knn_entropy_mme', 'chamfer_oracle'])
  const [normalize, setNormalize] = useState(true)

  const subset = useMemo(() => rows ? rows.filter(r => r.scene === scene && r.mode === mode) : [], [rows, scene, mode])
  const driftVaries = useMemo(() => {
    const s = new Set(subset.map(r => r.drift_intensity)); return s.size > 1
  }, [subset])
  const xKey = driftVaries ? 'drift_intensity' : 'level'
  const xLabel = driftVaries ? 'drift intensity — RMS pose error (m)' : 'severity level'
  const pts = useMemo(() => subset.length ? groupMean(subset, xKey, PLOTTABLE) : [], [subset, xKey])

  if (error) return <div className="card" style={{ borderColor: 'var(--red)' }}>
    Couldn’t load <span className="kbd">core_dataset.csv</span>: {error}. Run the experiments + <span className="kbd">npm run sync</span>.</div>
  if (!rows) return <div className="loading">Loading dataset (432 samples)…</div>

  const tier = MODES.find(m => m.key === mode)?.tier

  return (
    <div>
      <div className="sec-tag">Live replot</div>
      <h1 className="sec-title">Dataset explorer</h1>
      <p className="sec-desc">
        Replot the full sweep straight from <span className="kbd">core_dataset.csv</span> (432 samples,
        means over 3 seeds). Pick a scene and failure mode, choose which metrics to overlay, and watch
        them respond as drift grows. The chamfer oracle (dashed) is the ground-truth drift.
      </p>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="grid g2" style={{ marginBottom: 14 }}>
          <div>
            <div className="label-sm" style={{ marginBottom: 6 }}>Scene</div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {CORE_SCENES.map(s => (
                <button key={s} className={`btn${scene === s ? ' active' : ''}`} onClick={() => setScene(s)}>{s}</button>
              ))}
            </div>
          </div>
          <div>
            <div className="label-sm" style={{ marginBottom: 6 }}>Failure mode <span style={{ color: 'var(--muted2)' }}>· {TIERS[tier]?.label}</span></div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {CORE_MODES.map(m => (
                <button key={m} className={`btn${mode === m ? ' active' : ''}`} onClick={() => setMode(m)}>{m}</button>
              ))}
            </div>
          </div>
        </div>
        <div className="label-sm" style={{ marginBottom: 6 }}>Metrics to overlay</div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
          {PLOTTABLE.map(k => (
            <button key={k} className="btn" onClick={() => setSel(s => s.includes(k) ? s.filter(x => x !== k) : [...s, k])}
              style={{ borderColor: sel.includes(k) ? METRIC_COLORS[k] : 'var(--border)',
                       background: sel.includes(k) ? METRIC_COLORS[k] + '18' : 'var(--surface2)',
                       color: sel.includes(k) ? METRIC_COLORS[k] : 'var(--muted)', fontWeight: sel.includes(k) ? 600 : 400 }}>
              {sel.includes(k) ? '●' : '○'} {LABEL[k]}
            </button>
          ))}
          <label style={{ marginLeft: 'auto', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
            <input type="checkbox" checked={normalize} onChange={e => setNormalize(e.target.checked)} /> normalize per metric
          </label>
        </div>
        {pts.length && sel.length
          ? <Chart pts={pts} keys={sel} normalize={normalize} xLabel={xLabel} />
          : <div className="loading">Select at least one metric.</div>}
        {!normalize && <div style={{ fontSize: 11, color: 'var(--orange)', marginTop: 6 }}>
          Raw mode: chamfer is in meters and kNN-MME in nats — turn normalize on to compare shapes on one axis.</div>}
      </div>

      <div className="card" style={{ overflowX: 'auto' }}>
        <div className="label-sm" style={{ marginBottom: 10 }}>Grouped means · {scene} / {mode}</div>
        <table className="tbl">
          <thead><tr><th className="num">{driftVaries ? 'drift (m)' : 'level'}</th>
            {sel.map(k => <th key={k} className="num">{LABEL[k]}</th>)}</tr></thead>
          <tbody>
            {pts.map(p => (
              <tr key={p.x}><td className="num">{fmt(p.x, 3)}</td>
                {sel.map(k => <td key={k} className="num">{fmt(p[k], 3)}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
