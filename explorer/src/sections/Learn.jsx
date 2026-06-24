import { useMemo, useState } from 'react'
import { mulberry32, randn, pca2d } from '../lib/pca2d.js'
import { METRIC_COLORS } from '../data/catalog.js'

/* ─────────────────────────────────────────────────────────────────────────
   Interactive: the shape of a blob of points (2D PCA)
   ───────────────────────────────────────────────────────────────────────── */
function EigenDemo() {
  const [smear, setSmear] = useState(0.12)        // perpendicular spread σ (m)
  const N = 160

  // along-wall coords (u) and standard normals (z) generated ONCE, seeded, so
  // dragging the slider just scales the perpendicular spread smoothly.
  const base = useMemo(() => {
    const rng = mulberry32(7)
    const u = [], z = []
    for (let i = 0; i < N; i++) { u.push((rng() - 0.5) * 6); z.push(randn(rng)) }
    return { u, z }
  }, [])

  const pts = base.u.map((u, i) => ({ x: u, y: base.z[i] * smear }))
  const { mean, l1, l2, angle } = pca2d(pts)
  const ratio = l1 > 1e-9 ? l2 / l1 : 0
  const crispness = 1 - ratio
  const thickness = Math.sqrt(l2)                 // ≈ σ, the surface thickness

  // ── render to SVG (1 m = SCALE px) ──
  const W = 520, H = 300, SCALE = 46
  const cx = W / 2, cy = H / 2
  const toX = x => cx + x * SCALE
  const toY = y => cy - y * SCALE
  const deg = -angle * 180 / Math.PI
  const rx = 2 * Math.sqrt(l1) * SCALE
  const ry = 2 * Math.sqrt(Math.max(l2, 1e-4)) * SCALE
  const color = crispness > 0.85 ? '#059669' : crispness > 0.65 ? '#f59e0b' : '#ef4444'

  return (
    <div className="card">
      <div className="grid g2" style={{ gap: 20, alignItems: 'center' }}>
        <div>
          <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', background: '#0d1117', borderRadius: 8 }}>
            {/* the "true" wall line */}
            <line x1={toX(-3.2)} y1={toY(0)} x2={toX(3.2)} y2={toY(0)} stroke="#30363d" strokeDasharray="4 4" />
            {/* points */}
            {pts.map((p, i) => (
              <circle key={i} cx={toX(p.x)} cy={toY(p.y)} r="2.4" fill="#58a6ff" opacity="0.7" />
            ))}
            {/* covariance ellipse */}
            <ellipse cx={toX(mean.x)} cy={toY(mean.y)} rx={rx} ry={ry}
                     transform={`rotate(${deg} ${toX(mean.x)} ${toY(mean.y)})`}
                     fill={color} fillOpacity="0.12" stroke={color} strokeWidth="2" />
            {/* eigen-axes */}
            <line x1={toX(mean.x)} y1={toY(mean.y)}
                  x2={toX(mean.x) + Math.cos(-angle) * rx} y2={toY(mean.y) + Math.sin(-angle) * rx}
                  stroke="#8b949e" strokeWidth="1.5" />
            <line x1={toX(mean.x)} y1={toY(mean.y)}
                  x2={toX(mean.x) - Math.sin(-angle) * ry} y2={toY(mean.y) - Math.cos(-angle) * ry}
                  stroke={color} strokeWidth="2" />
            <text x={12} y={20} fill="#8b949e" fontSize="11">one voxel · {N} points</text>
          </svg>
          <div style={{ marginTop: 12 }}>
            <div className="label-sm" style={{ marginBottom: 6 }}>
              Drift smear σ = {smear.toFixed(2)} m <span style={{ color: 'var(--muted2)' }}>— drag to spread the points</span>
            </div>
            <input type="range" min="0.02" max="1.2" step="0.01" value={smear}
                   onChange={e => setSmear(+e.target.value)} style={{ width: '100%' }} />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--muted2)' }}>
              <span>clean wall</span><span>smeared by drift</span>
            </div>
          </div>
        </div>

        <div>
          <Stat label="λ₁ — spread ALONG the wall (major axis)" value={l1.toFixed(2)} note="big & roughly fixed" />
          <Stat label="λ₂ — spread ACROSS the wall (thickness²)" value={l2.toFixed(3)} note="grows as drift smears" color={color} />
          <Stat label="flatness ratio = λ₂ / λ₁" value={ratio.toFixed(3)} note="0 = perfect plane · 1 = blob" />
          <div style={{ margin: '14px 0 4px', fontWeight: 700 }}>
            Voxel-PCA crispness = 1 − λ₂/λ₁
          </div>
          <div style={{ height: 14, background: 'var(--surface3)', borderRadius: 7, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${crispness * 100}%`, background: color, transition: 'width .1s' }} />
          </div>
          <div style={{ fontSize: 22, fontWeight: 800, color, marginTop: 6 }}>{crispness.toFixed(3)}</div>
          <div style={{ fontSize: 12.5, color: 'var(--muted)', marginTop: 8, lineHeight: 1.6 }}>
            The surface is <strong>{thickness.toFixed(2)} m</strong> thick. A clean wall is paper-thin
            (λ₂≈0 → crispness≈1). Drift spreads the same points into a fat band (λ₂ grows → crispness
            falls). That single ratio is the whole metric.
          </div>
        </div>
      </div>
    </div>
  )
}

const Stat = ({ label, value, note, color }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '5px 0', borderBottom: '1px solid var(--border)' }}>
    <span style={{ fontSize: 12.5, color: 'var(--muted)' }}>{label}</span>
    <span style={{ fontFamily: 'var(--mono)', fontWeight: 700, color: color || 'var(--text)' }}>{value}
      <span style={{ fontWeight: 400, fontSize: 11, color: 'var(--muted2)', marginLeft: 6 }}>{note}</span>
    </span>
  </div>
)

/* ── small clean-vs-drifted surface illustration ─────────────────────────── */
function CleanVsDrift({ caption }) {
  const rng = mulberry32(3)
  const clean = Array.from({ length: 40 }, (_, i) => ({ x: 10 + i * 4.4, y: 40 + randn(rng) * 1.2 }))
  const rng2 = mulberry32(3)
  const drift = Array.from({ length: 40 }, (_, i) => ({ x: 10 + i * 4.4, y: 40 + randn(rng2) * 9 }))
  return (
    <div style={{ display: 'flex', gap: 12 }}>
      {[['clean', clean, '#059669'], ['drifted', drift, '#ef4444']].map(([t, pts, c]) => (
        <div key={t} style={{ flex: 1 }}>
          <svg viewBox="0 0 190 80" style={{ width: '100%', background: '#0d1117', borderRadius: 6 }}>
            {pts.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r="1.8" fill={c} opacity="0.8" />)}
          </svg>
          <div style={{ fontSize: 11, color: c, textAlign: 'center', marginTop: 4 }}>{t}</div>
        </div>
      ))}
    </div>
  )
}

/* ─────────────────────────────────────────────────────────────────────────
   Section
   ───────────────────────────────────────────────────────────────────────── */
const SHAPE_TABLE = [
  ['Flat plane (clean wall)', 'λ₁ ≈ λ₂ ≫ λ₃ ≈ 0', 'thin → CRISP', 'var(--green)'],
  ['Line / edge', 'λ₁ ≫ λ₂ ≈ λ₃ ≈ 0', 'thin', 'var(--green)'],
  ['Fuzzy blob (drift-smeared)', 'λ₁ ≈ λ₂ ≈ λ₃', 'thick → BLURRY', 'var(--red)'],
]

function H({ id, children }) { return <h2 id={id} style={{ scrollMarginTop: 70 }}>{children}</h2> }

export default function Learn() {
  return (
    <div className="md" style={{ maxWidth: 880 }}>
      <div className="sec-tag">Tutorial</div>
      <h1 className="sec-title" style={{ marginBottom: 8 }}>How the metrics work</h1>
      <p style={{ color: 'var(--muted)', fontSize: 15, marginBottom: 8 }}>
        A from-scratch walkthrough — no prior math assumed. By the end you’ll understand exactly
        what each metric computes and <em>why</em> it can detect SLAM drift.
      </p>

      <H id="idea">1 · The one big idea</H>
      <p>
        A LiDAR builds a map by stacking millions of 3D points onto the surfaces it sees — walls,
        floors, signs. If the vehicle’s estimated path is even slightly wrong (<strong>drift</strong>),
        the same wall gets painted at slightly different places on each pass. The result: instead of one
        crisp, paper-thin wall, you get a <strong>fuzzy, smeared band</strong> of points.
      </p>
      <CleanVsDrift />
      <blockquote>
        <strong>The whole project in one sentence:</strong> a healthy map is locally <em>thin and flat</em>;
        drift makes it <em>thick and fuzzy</em>. Every metric is a different way to measure that thickness —
        cheaply, without knowing the “true” map.
      </blockquote>

      <H id="voxels">2 · Step one: look locally (voxels)</H>
      <p>
        A whole map is too big and varied to judge at once. So we chop 3D space into little cubes called
        <strong> voxels</strong> (here, 0.5 m on a side) and ask the same question in each one:
        <em> are the points in this cube thin-and-flat, or fuzzy?</em> Averaging that answer over all the
        voxels gives a single map-quality score. Working locally is also what makes it fast — and what
        creates the one blind spot we’ll meet at the end.
      </p>

      <H id="shape">3 · Step two: measure the shape of a blob</H>
      <p>
        How do you turn “a cloud of points in a cube” into a number for <em>how flat</em> it is? With a
        classic tool called <strong>PCA</strong> (Principal Component Analysis). Don’t worry about the name —
        here’s all it does:
      </p>
      <ul>
        <li>It finds the <strong>directions the points spread out in</strong>, longest first.</li>
        <li>For each direction it gives a number — an <strong>eigenvalue</strong> (written λ) — that is just
          <strong> how far the points spread along that direction</strong> (a variance).</li>
      </ul>
      <p>
        In 3D you get three: <span className="kbd">λ₁ ≥ λ₂ ≥ λ₃</span>. Picture fitting the tightest
        possible ellipsoid (a squashed rugby ball) around the points — λ₁, λ₂, λ₃ are the lengths of its
        three axes. The smallest, <strong>λ₃, is the thickness</strong> of the surface.
      </p>

      <p><strong>Play with it (in 2D, so there are just λ₁ and λ₂):</strong> drag the slider to smear a
        clean wall and watch the fitted ellipse fatten and the crispness score drop.</p>
      <EigenDemo />

      <p style={{ marginTop: 16 }}>The shape tells you everything:</p>
      <table>
        <thead><tr><th>Local point shape</th><th>Eigenvalues</th><th>Verdict</th></tr></thead>
        <tbody>
          {SHAPE_TABLE.map(([s, e, v, c]) => (
            <tr key={s}><td>{s}</td><td><code>{e}</code></td><td style={{ color: c, fontWeight: 600 }}>{v}</td></tr>
          ))}
        </tbody>
      </table>

      <H id="scores">4 · Step three: turn the shape into a score</H>
      <p>Three of the six metrics are just different ways to summarize those eigenvalues:</p>

      <MetricBlock color={METRIC_COLORS.voxel_pca_crispness} name="Voxel PCA crispness" formula="1 − mean(λ₃ / λ₁)">
        The ratio <code>λ₃/λ₁</code> is “thickness ÷ length” = how blob-like the cube is (0 for a perfect
        plane, →1 for a ball). Average over all voxels and flip the sign so <strong>higher = crisper</strong>.
        This is exactly the slider demo above, done in 3D.
      </MetricBlock>

      <MetricBlock color={METRIC_COLORS.mme_grid} name="MME (grid)" formula="1 / (1 + mean(λ₃) / scale)">
        Uses the raw <strong>thickness λ₃</strong> directly (not a ratio). <code>scale</code> is tuned so a
        clean scene scores ≈ 0.9. Thicker surfaces → bigger λ₃ → score drops toward 0. A grid-fast
        approximation of a textbook measure called Mean Map Entropy.
      </MetricBlock>

      <MetricBlock color={METRIC_COLORS.mom_planarity} name="MOM planarity" formula="planar-fraction × normal-diversity">
        A counting approach: a voxel “passes” if it’s strictly flat (<code>λ₃/λ₁ &lt; 0.1</code>).
        <strong> planar-fraction</strong> = how many voxels pass. <strong>normal-diversity</strong> rewards
        walls facing many directions (a plane’s “normal” is the arrow pointing straight out of it). Drift
        pushes voxels past the flat threshold, so fewer pass and the score falls.
      </MetricBlock>

      <H id="others">5 · The other three metrics</H>

      <MetricBlock color={METRIC_COLORS.knn_entropy_mme} name="kNN MME (true)" formula="mean( −log det(Σ of 12 nearest neighbors) )">
        Instead of fixed cubes, it looks at each point’s <strong>12 nearest neighbors</strong> and measures
        the <em>volume</em> they occupy (<code>det</code> of their covariance = size of the local ellipsoid).
        A flat patch → tiny volume → big score. Because the neighborhood adapts to the data instead of
        snapping to a grid, this turned out to be the <strong>most accurate</strong> metric in our tests.
        Slightly more expensive (it builds a nearest-neighbor index).
      </MetricBlock>

      <MetricBlock color={METRIC_COLORS.bev_edge_density} name="BEV edge density" formula="sharpness of the top-down image">
        Squash the cloud flat into a top-down picture (“bird’s-eye view”) and measure how <strong>sharp the
        edges</strong> are. A crisp thin wall is a sharp bright line; a smeared wall is a soft blur. Very
        cheap, but weak and scene-sensitive — best as a quick pre-filter, not the main judge.
      </MetricBlock>

      <MetricBlock color={METRIC_COLORS.chamfer_oracle} name="Chamfer (oracle)" formula="avg distance to the ideal map (meters)">
        The cheater’s metric: it compares the drifted cloud to the <strong>known-perfect</strong> reference
        map and measures the average gap, in meters. You can’t use it in production (you never have the
        perfect map), but in the experiment it’s the <strong>ground-truth ruler</strong> we grade every
        other metric against — “does metric X agree with the real drift?”
      </MetricBlock>

      <H id="why">6 · Why does this actually work?</H>
      <p>The research gives the reason drift is detectable at all (see the Reports tab):</p>
      <ul>
        <li><strong>Random sensor noise averages out.</strong> It jitters points equally in all directions
          by a tiny, fixed amount — it doesn’t systematically thicken a surface, so crispness correctly
          <em> ignores</em> it.</li>
        <li><strong>Systematic drift accumulates.</strong> A small sensor bias integrates over time into a
          steadily growing pose error (the research shows it grows like t² or t³). That error paints the
          same surface in steadily-shifting places → the surface gets <strong>thicker and thicker</strong> →
          λ₃ climbs → crispness falls. Drift is exactly the kind of error that smears, and smear is exactly
          what these metrics see.</li>
      </ul>
      <p>That’s the success story: the metric is blind to the harmless thing (noise) and sensitive to the
        harmful thing (accumulating drift) — for free, per segment, with no ground-truth map.</p>

      <H id="blindspot">7 · Where it fails — the blind spot</H>
      <p>
        The local trick has one catch. In a <strong>tunnel or empty highway</strong>, the geometry can’t
        pin down motion <em>along</em> the corridor. When drift pushes points <em>along</em> a wall (rather
        than away from it), they slide <strong>across the surface but stay on it</strong> — so the wall stays
        thin, λ₃ barely changes, and the planarity metrics see nothing… even when the true error is large.
      </p>
      <blockquote>
        This is why the experiment found voxel-PCA reading ≈ 0.99 in a tunnel with metres of real drift,
        while the chamfer oracle (and, partly, kNN-MME) caught it. The fix: pair crispness with a
        degeneracy-aware signal, and use scene-aware thresholds. See the <strong>Scorecard</strong> and
        <strong> Dataset Explorer</strong> tabs to watch this happen — pick scene <code>tunnel</code>, mode
        <code>geometric_degeneracy</code>.
      </blockquote>

      <div className="card" style={{ background: 'var(--surface2)', marginTop: 24 }}>
        <strong>Recap.</strong> Chop the map into cubes → in each, fit an ellipsoid and read its thickness
        (λ₃) → average into a score that’s high for thin/flat maps and low for smeared ones. Noise doesn’t
        smear, drift does — so the score tracks drift. The only place it’s fooled is when drift slides
        points along a surface without thickening it.
      </div>
    </div>
  )
}

function MetricBlock({ color, name, formula, children }) {
  return (
    <div className="card card-sm" style={{ borderLeft: `3px solid ${color}`, marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8, alignItems: 'baseline' }}>
        <span style={{ fontWeight: 700, fontSize: 14.5, color }}>{name}</span>
        <code style={{ fontSize: 12.5 }}>{formula}</code>
      </div>
      <div style={{ fontSize: 13.5, color: 'var(--muted)', marginTop: 6, lineHeight: 1.7 }}>{children}</div>
    </div>
  )
}
