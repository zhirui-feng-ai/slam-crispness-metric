import { useState, lazy, Suspense, Component } from 'react'
import { TABS } from './lib/ui.js'

class ErrorBoundary extends Component {
  constructor(p) { super(p); this.state = { err: null } }
  static getDerivedStateFromError(err) { return { err } }
  componentDidCatch(err, info) { console.error('[explorer] render error', err, info) }
  render() {
    if (this.state.err) return (
      <div className="card" style={{ borderColor: 'var(--red)' }}>
        <strong>Something failed to render.</strong>
        <pre style={{ whiteSpace: 'pre-wrap', marginTop: 8 }}>{String(this.state.err)}</pre>
        <button className="btn" style={{ marginTop: 10 }} onClick={() => location.reload()}>Reload</button>
      </div>
    )
    return this.props.children
  }
}
import Overview from './sections/Overview.jsx'
import Learn from './sections/Learn.jsx'
import Scorecard from './sections/Scorecard.jsx'
import DatasetExplorer from './sections/DatasetExplorer.jsx'
import Catalogs from './sections/Catalogs.jsx'
import Figures from './sections/Figures.jsx'
import Reports from './sections/Reports.jsx'

// Lazy-load the 3D page so Three.js only downloads when that tab is opened.
const RoadScene = lazy(() => import('./sections/RoadScene.jsx'))

const VIEWS = {
  overview: Overview,
  learn: Learn,
  road3d: RoadScene,
  scorecard: Scorecard,
  dataset: DatasetExplorer,
  catalog: Catalogs,
  figures: Figures,
  reports: Reports,
}

export default function App() {
  const [tab, setTab] = useState('overview')
  const View = VIEWS[tab]
  return (
    <>
      <nav className="nav">
        <span className="nav-logo">⬡ SynthBench</span>
        {TABS.map(t => (
          <button key={t.id} className={`nav-link${tab === t.id ? ' active' : ''}`}
                  onClick={() => { setTab(t.id); window.scrollTo(0, 0) }}>
            {t.label}
          </button>
        ))}
      </nav>
      <div className="page">
        <div className="container">
          <ErrorBoundary key={tab}>
            <Suspense fallback={<div className="loading">Loading 3D viewer…</div>}>
              <View go={setTab} />
            </Suspense>
          </ErrorBoundary>
        </div>
      </div>
    </>
  )
}
