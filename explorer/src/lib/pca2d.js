// Tiny 2D PCA + deterministic RNG for the "How It Works" interactive demo.
// (2D mirrors the package's 3D voxel_pca — same idea, one fewer axis.)

/** Seeded PRNG so the demo points stay stable while a slider is dragged. */
export function mulberry32(seed) {
  let a = seed >>> 0
  return () => {
    a |= 0; a = (a + 0x6D2B79F5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** Box-Muller standard normal from a uniform generator. */
export function randn(rng) {
  let u = 0, v = 0
  while (u === 0) u = rng()
  while (v === 0) v = rng()
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v)
}

/** Covariance + eigen-decomposition of 2D points [{x,y}]. Returns
 *  { mean, l1, l2, angle } with l1 ≥ l2 and angle of the major axis (rad). */
export function pca2d(pts) {
  const n = pts.length
  if (n < 2) return { mean: { x: 0, y: 0 }, l1: 0, l2: 0, angle: 0 }
  let mx = 0, my = 0
  for (const p of pts) { mx += p.x; my += p.y }
  mx /= n; my /= n
  let a = 0, b = 0, c = 0          // cov = [[a,b],[b,c]]
  for (const p of pts) {
    const dx = p.x - mx, dy = p.y - my
    a += dx * dx; b += dx * dy; c += dy * dy
  }
  a /= n; b /= n; c /= n
  const tr = a + c, det = a * c - b * b
  const disc = Math.sqrt(Math.max(0, (tr / 2) ** 2 - det))
  const l1 = tr / 2 + disc, l2 = tr / 2 - disc
  // eigenvector of the larger eigenvalue
  const angle = Math.abs(b) < 1e-12 ? (a >= c ? 0 : Math.PI / 2)
    : Math.atan2(l1 - a, b)
  return { mean: { x: mx, y: my }, l1: Math.max(l1, 0), l2: Math.max(l2, 0), angle }
}
