"""
metrics.py — the six reference-free / reference-based crispness candidates,
all native 3D.

  voxel_pca_crispness   1 − mean(λ3/λ1) per voxel.        higher = crisper. O(N)
  mme_grid              grid-approx Mean Map Entropy.      higher = crisper. O(N)
  mom_planarity         planar-fraction × normal-diversity. higher = crisper. O(N)
  bev_edge_density      Sobel energy on top-down density.  higher = crisper. O(N)
  knn_entropy_mme       TRUE kNN Mean Map Entropy.         higher = crisper. O(N log N)
  chamfer_oracle        symmetric NN distance to reference. LOWER = better. O(N log N)

The four voxel/grid metrics share one vectorized PCA pass (`voxel_pca`):
points are bucketed into a voxel grid and per-voxel 3×3 covariance eigenvalues
(and the minor-eigenvalue normal, for MOM) are computed in a single batched
`eigh`. No Python loop over voxels.

Scores are returned RAW (not normalized). Evaluation uses rank statistics
(Spearman, Mann-Whitney AUC) that are invariant to any monotonic rescaling, so
absolute units never need to be reconciled across metrics. `METRIC_INFO` records
the orientation (`higher_is_better`) and whether a reference cloud is required.
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy.spatial import cKDTree


# ── shared voxel PCA ─────────────────────────────────────────────────────────

@dataclass
class VoxelPCA:
    l1: np.ndarray       # (G,) largest eigenvalue per kept voxel  (λ1 ≥ λ2 ≥ λ3)
    l2: np.ndarray
    l3: np.ndarray
    normals: np.ndarray  # (G,3) minor-eigenvalue direction (surface normal)
    counts: np.ndarray   # (G,) points per kept voxel
    n_total_voxels: int  # voxels before the min_pts filter


def voxel_pca(points: np.ndarray, voxel: float = 0.5, min_pts: int = 8) -> VoxelPCA:
    """Batched per-voxel 3×3 PCA. One eigh over all voxels, no per-voxel loop."""
    n = len(points)
    if n == 0:
        z = np.zeros(0)
        return VoxelPCA(z, z, z, np.zeros((0, 3)), z.astype(int), 0)

    keys = np.floor(points / voxel).astype(np.int64)
    uniq, inv, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    inv = inv.ravel()
    n_total = len(uniq)

    order = np.argsort(inv, kind="stable")
    ps = points[order]
    starts = np.zeros(n_total, dtype=np.int64)
    starts[1:] = np.cumsum(counts)[:-1]

    S1 = np.add.reduceat(ps, starts, axis=0)                      # (G,3) sum of points
    outer = (ps[:, :, None] * ps[:, None, :]).reshape(n, 9)
    S2 = np.add.reduceat(outer, starts, axis=0).reshape(-1, 3, 3)  # (G,3,3)

    c = counts[:, None].astype(np.float64)
    mean = S1 / c
    cov = S2 / c[:, :, None] - mean[:, :, None] * mean[:, None, :]

    keep = counts >= min_pts
    if not keep.any():
        z = np.zeros(0)
        return VoxelPCA(z, z, z, np.zeros((0, 3)), z.astype(int), n_total)

    cov = cov[keep]
    evals, evecs = np.linalg.eigh(cov)        # ascending: evals[:,0] ≤ … ≤ evals[:,2]
    evals = np.clip(evals, 0.0, None)
    l3, l2, l1 = evals[:, 0], evals[:, 1], evals[:, 2]
    normals = evecs[:, :, 0]                  # minor-eigenvalue direction
    return VoxelPCA(l1, l2, l3, normals, counts[keep], n_total)


# ── 1. Voxel PCA crispness ───────────────────────────────────────────────────

def voxel_pca_crispness(points, voxel: float = 0.5, min_pts: int = 8,
                        pca: VoxelPCA | None = None) -> float:
    p = pca or voxel_pca(points, voxel, min_pts)
    if len(p.l1) == 0:
        return 1.0
    ok = p.l1 > 1e-9
    if not ok.any():
        return 1.0
    ratio = p.l3[ok] / p.l1[ok]
    return float(1.0 - np.mean(ratio))


# ── 2. MME (grid approximation) ──────────────────────────────────────────────

def mme_grid(points, voxel: float = 0.5, min_pts: int = 8,
             pca: VoxelPCA | None = None) -> float:
    p = pca or voxel_pca(points, voxel, min_pts)
    if len(p.l3) == 0:
        return 1.0
    scale = (voxel * 0.1) ** 2                # tuned: clean planar scene → ~0.9
    return float(1.0 / (1.0 + np.mean(p.l3) / scale))


# ── 3. MOM planarity ─────────────────────────────────────────────────────────

def mom_planarity(points, voxel: float = 0.5, min_pts: int = 8,
                  plane_thresh: float = 0.1, pca: VoxelPCA | None = None) -> float:
    p = pca or voxel_pca(points, voxel, min_pts)
    if len(p.l1) == 0:
        return 0.0
    ok = p.l1 > 1e-9
    planar = ok & ((p.l3 / np.where(ok, p.l1, 1.0)) < plane_thresh)
    if not planar.any():
        return 0.0
    planar_fraction = planar.sum() / len(p.l1)
    # normal diversity: bin minor-eigenvalue normals into 6 axis-sign bins
    nv = p.normals[planar]
    dom = np.argmax(np.abs(nv), axis=1)
    sign = (nv[np.arange(len(nv)), dom] >= 0).astype(int)
    bins = set(zip(dom.tolist(), sign.tolist()))
    diversity = 0.5 + 0.5 * (len(bins) / 6.0)
    # planar_fraction (∈[0,1]) × diversity (∈[0.5,1]) — no saturating ×2, so the
    # metric keeps headroom to fall as drift pushes voxels past plane_thresh.
    return float(planar_fraction * diversity)


# ── 4. BEV edge density ──────────────────────────────────────────────────────

def bev_edge_density(points, cell: float = 0.25, squash: float = 6.0) -> float:
    """Sobel energy of a top-down density image. Crisp thin walls → sharp
    gradients → high energy; drift spreads density → softer gradients."""
    if len(points) < 16:
        return 0.0
    xy = points[:, :2]
    mn = xy.min(0); mx = xy.max(0)
    span = np.maximum(mx - mn, 1e-6)
    nbins = np.maximum((span / cell).astype(int) + 1, 2)
    nbins = np.minimum(nbins, 1024)
    ix = np.minimum(((xy[:, 0] - mn[0]) / span[0] * (nbins[0] - 1)).astype(int), nbins[0] - 1)
    iy = np.minimum(((xy[:, 1] - mn[1]) / span[1] * (nbins[1] - 1)).astype(int), nbins[1] - 1)
    grid = np.zeros((nbins[0], nbins[1]), dtype=np.float64)
    np.add.at(grid, (ix, iy), 1.0)
    grid /= max(grid.max(), 1e-9)             # normalize density to [0,1]
    gx = np.gradient(grid, axis=0)
    gy = np.gradient(grid, axis=1)
    mag = np.hypot(gx, gy)
    occ = grid > 0
    if not occ.any():
        return 0.0
    energy = float(mag[occ].mean())           # mean edge energy per occupied cell
    return energy / (energy + 1.0 / squash)   # squash to [0,1]


# ── 5. kNN entropy MME (true, O(N log N)) ────────────────────────────────────

def knn_entropy_mme(points, k: int = 12, max_queries: int = 4000,
                    seed: int = 0) -> float:
    """True Mean Map Entropy: −mean log det(Σ_kNN). Higher = crisper.
    Queries a random subset for O(N log N) tractability at AV scale."""
    n = len(points)
    if n < k + 1:
        return 0.0
    tree = cKDTree(points)
    rng = np.random.default_rng(seed)
    q_idx = rng.choice(n, size=min(max_queries, n), replace=False)
    _, nbr = tree.query(points[q_idx], k=k)    # (Q,k) neighbor indices
    nb = points[nbr]                            # (Q,k,3)
    mean = nb.mean(axis=1, keepdims=True)
    d = nb - mean
    cov = np.einsum("qki,qkj->qij", d, d) / k   # (Q,3,3)
    cov += np.eye(3) * 1e-9
    sign, logdet = np.linalg.slogdet(cov)
    valid = sign > 0
    if not valid.any():
        return 0.0
    return float(np.mean(-logdet[valid]))       # crisp → tiny det → large +value


# ── 6. Chamfer oracle (reference-based) ──────────────────────────────────────

def chamfer_oracle(points, reference: np.ndarray, max_queries: int = 8000,
                   seed: int = 0) -> float:
    """Symmetric mean nearest-neighbor distance (meters). LOWER = better.
    Needs the ideal reference cloud → not productionizable, but the ground-truth
    yardstick every reference-free metric is scored against."""
    if len(points) == 0 or reference is None or len(reference) == 0:
        return float("nan")
    rng = np.random.default_rng(seed)

    def _sample(a):
        return a if len(a) <= max_queries else a[rng.choice(len(a), max_queries, replace=False)]

    p, r = _sample(points), _sample(reference)
    d_pr, _ = cKDTree(r).query(p)
    d_rp, _ = cKDTree(p).query(r)
    return float(0.5 * (d_pr.mean() + d_rp.mean()))


# ── registry ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MetricInfo:
    key: str
    label: str
    higher_is_better: bool
    needs_reference: bool
    complexity: str

METRIC_INFO = {
    "voxel_pca_crispness": MetricInfo("voxel_pca_crispness", "Voxel PCA", True, False, "O(N)"),
    "mme_grid":            MetricInfo("mme_grid", "MME (grid)", True, False, "O(N)"),
    "mom_planarity":       MetricInfo("mom_planarity", "MOM planarity", True, False, "O(N)"),
    "bev_edge_density":    MetricInfo("bev_edge_density", "BEV edge density", True, False, "O(N)"),
    "knn_entropy_mme":     MetricInfo("knn_entropy_mme", "kNN MME (true)", True, False, "O(N log N)"),
    "chamfer_oracle":      MetricInfo("chamfer_oracle", "Chamfer (oracle)", False, True, "O(N log N)"),
}

REFERENCE_FREE = [k for k, m in METRIC_INFO.items() if not m.needs_reference]


def compute_all(observed: np.ndarray, reference: np.ndarray | None = None,
                voxel: float = 0.5, min_pts: int = 8) -> dict:
    """Compute every applicable metric on one cloud (shares one voxel_pca pass)."""
    pca = voxel_pca(observed, voxel, min_pts)
    out = {
        "voxel_pca_crispness": voxel_pca_crispness(observed, voxel, min_pts, pca=pca),
        "mme_grid":            mme_grid(observed, voxel, min_pts, pca=pca),
        "mom_planarity":       mom_planarity(observed, voxel, min_pts, pca=pca),
        "bev_edge_density":    bev_edge_density(observed),
        "knn_entropy_mme":     knn_entropy_mme(observed),
    }
    if reference is not None:
        out["chamfer_oracle"] = chamfer_oracle(observed, reference)
    return out
