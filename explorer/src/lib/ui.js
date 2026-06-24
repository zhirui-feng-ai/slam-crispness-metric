// Shared tiny UI helpers.

/** RdYlGn-ish color for a value in [0,1]. Used by scorecard / heatmaps. */
export function heatColor(v, { vmin = 0, vmax = 1 } = {}) {
  if (v === null || v === undefined || Number.isNaN(v)) return '#e4e8ff'
  const t = Math.max(0, Math.min(1, (v - vmin) / (vmax - vmin)))
  // red (0) → yellow (0.5) → green (1)
  const r = t < 0.5 ? 230 : Math.round(230 - (t - 0.5) * 2 * 180)
  const g = t < 0.5 ? Math.round(120 + t * 2 * 110) : 200
  const b = Math.round(70 + Math.min(t, 0.5) * 2 * 20)
  return `rgb(${r},${g},${b})`
}

export const fmt = (v, d = 3) =>
  v === null || v === undefined || Number.isNaN(v) ? '—' : Number(v).toFixed(d)

export const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'learn', label: 'How It Works' },
  { id: 'road3d', label: '3D Road Scene' },
  { id: 'scorecard', label: 'Scorecard' },
  { id: 'dataset', label: 'Dataset Explorer' },
  { id: 'catalog', label: 'Catalogs' },
  { id: 'figures', label: 'Figures' },
  { id: 'reports', label: 'Reports' },
]
