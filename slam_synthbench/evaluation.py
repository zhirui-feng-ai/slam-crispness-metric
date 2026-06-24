"""
evaluation.py — the metric scorecard (the PLAN's "Evaluation Scorecard").

Translates the qualitative pass-conditions into rank-based, scale-free numbers
so heterogeneous metrics are directly comparable:

  sensitivity        Spearman ρ(drift_intensity, score). Want strongly NEGATIVE
                     for higher-is-better metrics (score falls as drift grows),
                     and monotonic. Reported oriented so +1 = ideal.
  separability       Mann-Whitney AUC separating clean vs drifted samples
                     (0.5 = useless, 1.0 = perfect). Plus Cohen's d.
  scene_independence 1 − coefficient-of-variation of the clean score across
                     scenes (1 = scene-invariant).
  noise_robustness   1 − fractional score drop across the noise sweep (1 = a
                     metric that correctly ignores zero-mean noise).

All take metric orientation into account via METRIC_INFO.higher_is_better.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr, mannwhitneyu

from .metrics import METRIC_INFO


def _oriented(values: np.ndarray, key: str) -> np.ndarray:
    """Flip so that LARGER always means crisper (for uniform downstream logic)."""
    v = np.asarray(values, float)
    return v if METRIC_INFO[key].higher_is_better else -v


def sensitivity(intensities, scores, key: str) -> dict:
    """Spearman correlation of crisper-oriented score vs drift intensity.
    Ideal = −1 (score falls monotonically as drift grows). Reported as
    `monotonicity` = −ρ so that +1 is ideal."""
    x = np.asarray(intensities, float)
    y = _oriented(scores, key)
    if len(x) < 3 or np.allclose(x, x[0]) or np.allclose(y, y[0]):
        return {"rho": float("nan"), "monotonicity": float("nan")}
    rho, _ = spearmanr(x, y)
    return {"rho": float(rho), "monotonicity": float(-rho)}


def separability(clean_scores, drift_scores, key: str) -> dict:
    """Rank-AUC + Cohen's d separating clean from drifted populations."""
    c = _oriented(clean_scores, key)
    d = _oriented(drift_scores, key)
    c = c[np.isfinite(c)]; d = d[np.isfinite(d)]
    if len(c) < 2 or len(d) < 2:
        return {"auc": float("nan"), "cohens_d": float("nan")}
    # AUC = P(clean ranks crisper than drifted). >0.5 means clean looks crisper.
    u, _ = mannwhitneyu(c, d, alternative="greater")
    auc = u / (len(c) * len(d))
    pooled = np.sqrt((c.var(ddof=1) + d.var(ddof=1)) / 2) or 1e-9
    cohens_d = (c.mean() - d.mean()) / pooled
    return {"auc": float(auc), "cohens_d": float(cohens_d)}


def scene_independence(clean_scores_by_scene: dict, key: str) -> dict:
    """1 − CoV of the clean score across scenes. 1 = perfectly scene-invariant."""
    vals = _oriented(np.array([np.mean(v) for v in clean_scores_by_scene.values()]), key)
    mu = np.mean(vals)
    if abs(mu) < 1e-9:
        return {"cov": float("nan"), "scene_independence": float("nan")}
    cov = np.std(vals) / abs(mu)
    return {"cov": float(cov), "scene_independence": float(max(0.0, 1.0 - cov))}


def noise_robustness(noise_levels, scores, key: str) -> dict:
    """1 − fractional drop of the crisper-oriented score across a noise sweep.
    A robust metric (correctly blind to zero-mean noise) scores near 1."""
    y = _oriented(scores, key)
    order = np.argsort(noise_levels)
    y = y[order]
    base = y[0]
    if abs(base) < 1e-9:
        return {"frac_drop": float("nan"), "noise_robustness": float("nan")}
    frac_drop = (base - y[-1]) / abs(base)
    return {"frac_drop": float(frac_drop), "noise_robustness": float(1.0 - max(0.0, frac_drop))}
