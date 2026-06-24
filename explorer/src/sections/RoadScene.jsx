import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { useJSON } from '../lib/data.js'
import { fmt } from '../lib/ui.js'

const BASE = import.meta.env.BASE_URL || '/'

// height colormap (dark-blue → teal → green → yellow → orange), t in [0,1]
const STOPS = [[33, 41, 95], [42, 110, 160], [63, 185, 130], [230, 200, 70], [240, 120, 50]]
function heightColor(t, out, i) {
  t = Math.max(0, Math.min(1, t)) * (STOPS.length - 1)
  const k = Math.floor(t), f = t - k
  const a = STOPS[k], b = STOPS[Math.min(k + 1, STOPS.length - 1)]
  out[i] = (a[0] + (b[0] - a[0]) * f) / 255
  out[i + 1] = (a[1] + (b[1] - a[1]) * f) / 255
  out[i + 2] = (a[2] + (b[2] - a[2]) * f) / 255
}

export default function RoadScene() {
  const { data: manifest, error } = useJSON('clouds/manifest.json')
  const mountRef = useRef(null)
  const three = useRef({})
  const cache = useRef(new Map())
  const [mode, setMode] = useState('random_walk')
  const [lvlIdx, setLvlIdx] = useState(0)
  const [overlay, setOverlay] = useState(false)
  const [status, setStatus] = useState('')
  const [err, setErr] = useState('')

  // ── init Three once ──
  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return
    let renderer
    try {
    const w = mount.clientWidth || 640, h = 460
    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#0d1117')
    const camera = new THREE.PerspectiveCamera(55, w / h, 0.1, 1000)
    camera.up.set(0, 0, 1)                              // Z-up (our data convention)
    camera.position.set(-6, -26, 15)
    renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
    renderer.setSize(w, h)
    mount.appendChild(renderer.domElement)
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true; controls.dampingFactor = 0.1

    const grid = new THREE.GridHelper(160, 80, 0x223, 0x1a2030)
    grid.rotation.x = Math.PI / 2                       // lay flat on XY (Z-up)
    scene.add(grid)

    // Fixed pixel-size points (sizeAttenuation off) so the cloud stays visible at
    // any zoom — world-size points go sub-pixel at this scene's viewing distance.
    const mk = (size, opacity) => {
      const g = new THREE.BufferGeometry()
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(0), 3))  // valid empty geom
      const m = new THREE.PointsMaterial({ size, vertexColors: true, sizeAttenuation: false,
        transparent: opacity < 1, opacity })
      const p = new THREE.Points(g, m); p.visible = false; scene.add(p); return p
    }
    const points = mk(1.8, 1)
    const refPoints = mk(1.3, 0.5)
    refPoints.material.vertexColors = false
    refPoints.material.color = new THREE.Color('#2ea043')

    three.current = { scene, camera, renderer, controls, points, refPoints, mount }

    let raf, renderErrLogged = false
    const loop = () => {
      raf = requestAnimationFrame(loop)            // schedule FIRST so a render throw can't kill the loop
      controls.update()
      try { renderer.render(scene, camera) }
      catch (e) { if (!renderErrLogged) { console.error('[RoadScene] render error', e); renderErrLogged = true } }
    }
    loop()
    const onResize = () => {
      const ww = mount.clientWidth || 640
      camera.aspect = ww / h; camera.updateProjectionMatrix(); renderer.setSize(ww, h)
    }
    const ro = new ResizeObserver(onResize); ro.observe(mount)

    return () => {
      cancelAnimationFrame(raf); ro.disconnect(); controls.dispose(); renderer.dispose()
      if (renderer.domElement.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement)
      three.current = {}
    }
    } catch (e) {
      console.error('[RoadScene] init failed', e)
      setErr('3D init failed: ' + e.message + ' (does your browser have WebGL enabled?)')
    }
  }, [])

  // ── frame camera to scene bounds once manifest is in ──
  useEffect(() => {
    if (!manifest || !three.current.controls) return
    const b = manifest.bounds
    three.current.controls.target.set((b.x[0] + b.x[1]) * 0.42, 0, 2.5)
    three.current.controls.update()
  }, [manifest])

  async function loadCloud(file) {
    if (cache.current.has(file)) return cache.current.get(file)
    const buf = await fetch(BASE + 'clouds/' + file).then(r => r.arrayBuffer())
    const arr = new Float32Array(buf)
    cache.current.set(file, arr)
    return arr
  }

  function setGeom(p, arr, colored, zr) {
    const g = p.geometry
    g.setAttribute('position', new THREE.BufferAttribute(arr, 3))
    if (colored) {
      const col = new Float32Array(arr.length)
      for (let i = 0; i < arr.length; i += 3) heightColor((arr[i + 2] - zr[0]) / (zr[1] - zr[0]), col, i)
      g.setAttribute('color', new THREE.BufferAttribute(col, 3))
    }
    g.computeBoundingSphere(); p.visible = true
  }

  // ── load clouds on selection change ──
  useEffect(() => {
    if (!manifest || !three.current.points) return
    const row = manifest.clouds[mode][lvlIdx]
    const zr = manifest.bounds.z
    let alive = true
    setStatus('loading…'); setErr('')
    ;(async () => {
      try {
        const arr = await loadCloud(row.file)
        if (!alive || !three.current.points) return
        setGeom(three.current.points, arr, true, zr)
        if (overlay) {
          const ref = await loadCloud('reference.bin')
          if (!alive || !three.current.refPoints) return
          setGeom(three.current.refPoints, ref, false, zr)
          three.current.refPoints.visible = true
        } else if (three.current.refPoints) {
          three.current.refPoints.visible = false
        }
        setStatus('')
      } catch (e) {
        console.error('[RoadScene] cloud load failed', e)
        setStatus(''); setErr(`Could not load ${row.file}: ${e.message}`)
      }
    })()
    return () => { alive = false }
  }, [manifest, mode, lvlIdx, overlay])

  const LEVEL_LABELS = ['clean', 'low', 'medium', 'high']
  const rows = manifest ? manifest.clouds[mode] : null
  const row = rows ? rows[lvlIdx] : null
  const ref = manifest ? manifest.reference : null

  return (
    <div>
      <div className="sec-tag">3D viewer</div>
      <h1 className="sec-title">On-road scene under drift</h1>
      <p className="sec-desc">
        A LiDAR map of an urban street (road, building facades, parked cars, lamp poles) accumulated
        over a {manifest ? fmt(manifest.duration, 0) : '14'} s drive. Start at <strong>clean</strong> to
        see the perfect map, then raise the drift level and watch the facades thicken and the cars ghost.
        Drag to orbit, scroll to zoom. Points are colored by height.
      </p>

      {/* canvas mount is ALWAYS rendered so Three.js init (deps []) finds the container */}
      <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 16 }}>
        <div ref={mountRef} style={{ width: '100%', height: 460, position: 'relative' }}>
          {!manifest && !error && <Overlay>Loading scene…</Overlay>}
          {error && <Overlay color="var(--red)">Couldn’t load clouds: {error}. Run <span className="kbd">python experiments/export_clouds.py</span></Overlay>}
          {status && <div style={{ position: 'absolute', top: 10, left: 12, color: 'var(--muted2)', fontSize: 12, zIndex: 2 }}>{status}</div>}
          {err && <Overlay color="var(--red)">{err}</Overlay>}
        </div>
      </div>

      {manifest && row && (
      <div className="grid g2" style={{ alignItems: 'start' }}>
        <div className="card">
          <div className="label-sm" style={{ marginBottom: 8 }}>Drift mode</div>
          <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
            {manifest.modes.map(m => (
              <button key={m} className={`btn${mode === m ? ' active' : ''}`} onClick={() => setMode(m)}>{m}</button>
            ))}
          </div>
          <div className="label-sm" style={{ marginBottom: 8 }}>
            Drift level — {LEVEL_LABELS[lvlIdx]} {lvlIdx === 0 ? '(perfect map)' : ''}
          </div>
          <input type="range" min="0" max={rows.length - 1} step="1" value={lvlIdx}
                 onChange={e => setLvlIdx(+e.target.value)} style={{ width: '100%' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--muted2)', marginBottom: 14 }}>
            {rows.map((r, i) => <span key={i}>{i === 0 ? 'clean' : `${r.drift_intensity} m`}</span>)}
          </div>
          <label style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
            <input type="checkbox" checked={overlay} onChange={e => setOverlay(e.target.checked)} />
            overlay the clean map (green) to compare ghosting
          </label>
        </div>

        <div className="card">
          <div className="label-sm" style={{ marginBottom: 10 }}>This map</div>
          <Stat k="True drift (RMS pose error)" v={`${fmt(row.drift_intensity, 2)} m`} hi={row.drift_intensity > 0.5} />
          <Stat k="Voxel-PCA crispness" v={fmt(row.crispness, 3)} hi={row.crispness < 0.85} flip />
          <Stat k="kNN MME (true)" v={fmt(row.knn_mme, 1)} />
          <Stat k="Chamfer vs clean (m)" v={fmt(row.chamfer, 3)} hi={row.chamfer > ref.chamfer * 1.5} />
          <Stat k="Points shown" v={row.n_points.toLocaleString()} />
          <div style={{ fontSize: 12.5, color: 'var(--muted)', marginTop: 10, lineHeight: 1.6 }}>
            As drift rises, crispness falls and the chamfer distance to the clean map grows — the surfaces
            you see thickening are exactly what the metric measures. Compare modes: <code>gyro_bias</code> is
            a subtle systematic smear; <code>random_walk</code> drifts much harder.
          </div>
        </div>
      </div>
      )}
    </div>
  )
}

const Overlay = ({ children, color }) => (
  <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
    justifyContent: 'center', textAlign: 'center', padding: 24, zIndex: 3,
    color: color || 'var(--muted2)', fontSize: 13 }}>{children}</div>
)

const Stat = ({ k, v, hi, flip }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
    <span style={{ fontSize: 13, color: 'var(--muted)' }}>{k}</span>
    <span style={{ fontFamily: 'var(--mono)', fontWeight: 700, color: hi ? (flip ? 'var(--red)' : 'var(--orange)') : 'var(--text)' }}>{v}</span>
  </div>
)
