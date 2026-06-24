import { useState } from 'react'
import { SCENES, MODES, METRICS, TIERS, METRIC_COLORS } from '../data/catalog.js'

const SUB = [['scenes', 'Scenes'], ['modes', 'Drift modes'], ['metrics', 'Metrics']]
const TIER_ORDER = ['noise', 'bias', 'catastrophic', 'phenomenological']

export default function Catalogs() {
  const [sub, setSub] = useState('modes')
  return (
    <div>
      <div className="sec-tag">Reference</div>
      <h1 className="sec-title">Catalogs</h1>
      <p className="sec-desc">
        Every building block of the benchmark: the 5 scenes spanning the geometric-conditioning
        spectrum, the 18 drift modes grouped by research tier (with physical models), and the 6
        metric candidates with definitions, complexity and orientation.
      </p>

      <div style={{ display: 'flex', gap: 6, marginBottom: 24 }}>
        {SUB.map(([id, l]) => (
          <button key={id} className={`btn${sub === id ? ' active' : ''}`} onClick={() => setSub(id)}>{l}</button>
        ))}
      </div>

      {sub === 'scenes' && (
        <div className="grid g2">
          {SCENES.map(s => (
            <div className="card" key={s.key}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontWeight: 700, fontSize: 16 }}>{s.label}</span>
                <span className="chip" style={{ background: 'var(--surface2)', color: 'var(--muted)' }}>{s.conditioning}</span>
              </div>
              <div style={{ fontSize: 13.5, color: 'var(--muted)', marginBottom: 8 }}>{s.desc}</div>
              <div style={{ fontSize: 12, color: 'var(--muted2)' }}>degenerate axis: <span className="kbd">{s.degenerate}</span></div>
            </div>
          ))}
        </div>
      )}

      {sub === 'modes' && TIER_ORDER.map(tier => (
        <div key={tier} style={{ marginBottom: 26 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 10 }}>
            <span className={`chip tier-${tier}`} style={{ fontSize: 12, padding: '3px 10px' }}>{TIERS[tier].label}</span>
            <span style={{ fontSize: 13, color: 'var(--muted)' }}>{TIERS[tier].blurb}</span>
          </div>
          <div className="grid g2">
            {MODES.filter(m => m.tier === tier).map(m => (
              <div className="card card-sm" key={m.key}>
                <div style={{ fontWeight: 700, fontFamily: 'var(--mono)', fontSize: 13, marginBottom: 4 }}>{m.key}</div>
                <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 8 }}>{m.desc}</div>
                <div style={{ fontSize: 12, fontFamily: 'var(--mono)', background: 'var(--surface2)', padding: '5px 9px', borderRadius: 6, color: 'var(--text)' }}>{m.model}</div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {sub === 'metrics' && (
        <div className="grid g2">
          {METRICS.map(m => (
            <div className="card" key={m.key} style={{ borderLeft: `3px solid ${METRIC_COLORS[m.key]}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontWeight: 700, fontSize: 15, color: METRIC_COLORS[m.key] }}>{m.label}</span>
                <span style={{ display: 'flex', gap: 6 }}>
                  <span className="chip" style={{ background: 'var(--surface2)', color: 'var(--muted)' }}>{m.complexity}</span>
                  <span className="chip" style={{ background: m.ref_free ? 'rgba(5,150,105,0.12)' : 'rgba(239,68,68,0.12)', color: m.ref_free ? 'var(--green)' : 'var(--red)' }}>
                    {m.ref_free ? 'reference-free' : 'needs reference'}
                  </span>
                </span>
              </div>
              <div style={{ fontSize: 13.5, marginBottom: 6 }}>{m.def}</div>
              <div style={{ fontSize: 12.5, color: 'var(--muted)' }}>{m.note}</div>
              <div style={{ fontSize: 11, color: 'var(--muted2)', marginTop: 8 }}>
                {m.higher ? 'higher = crisper' : 'lower = better (distance)'}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
