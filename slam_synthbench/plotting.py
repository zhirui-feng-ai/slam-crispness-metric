"""
plotting.py — reusable figure helpers (matplotlib, Agg backend).

Every figure function takes a DataFrame (or arrays) and an output path, draws,
saves a PNG, and returns the path — so experiments and the notebook share one
drawing layer. Style is dark to match the slam-explorer web app.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .metrics import METRIC_INFO

plt.rcParams.update({
    "figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
    "savefig.facecolor": "#0d1117", "text.color": "#c9d1d9",
    "axes.labelcolor": "#c9d1d9", "xtick.color": "#8b949e", "ytick.color": "#8b949e",
    "axes.edgecolor": "#30363d", "grid.color": "#21262d", "font.size": 10,
})

METRIC_COLORS = {
    "voxel_pca_crispness": "#58a6ff", "mme_grid": "#3fb950", "mom_planarity": "#f85149",
    "bev_edge_density": "#e3b341", "knn_entropy_mme": "#bc8cff", "chamfer_oracle": "#8b949e",
}


def _save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def _norm(v):
    v = np.asarray(v, float)
    lo, hi = np.nanmin(v), np.nanmax(v)
    return (v - lo) / (hi - lo) if hi > lo else np.zeros_like(v)


def sensitivity_curves(df, metric_keys, out_path, title="Metric sensitivity vs drift"):
    """df columns: drift_intensity, <metric keys> (mean per intensity). One panel
    per metric is overkill — overlay min-max-normalized curves on shared axes."""
    g = df.groupby("drift_intensity")[metric_keys].mean().reset_index()
    fig, ax = plt.subplots(figsize=(7, 4.2))
    x = g["drift_intensity"].values
    for k in metric_keys:
        y = _norm(g[k].values)
        ax.plot(x, y, "-o", ms=3, lw=1.8, color=METRIC_COLORS.get(k), label=METRIC_INFO[k].label)
    ax.set_xlabel("drift intensity — RMS pose error (m)")
    ax.set_ylabel("metric score (min-max normalized)")
    ax.set_title(title)
    ax.grid(True, alpha=0.4); ax.legend(fontsize=8, framealpha=0.2)
    return _save(fig, out_path)


def grouped_bars(labels, series: dict, out_path, ylabel, title, ylim=None):
    """series: {name: [values aligned with labels]} → grouped bar chart."""
    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.9), 4.2))
    n = len(series); w = 0.8 / max(n, 1)
    x = np.arange(len(labels))
    for i, (name, vals) in enumerate(series.items()):
        ax.bar(x + i * w - 0.4 + w / 2, vals, w, label=name,
               color=METRIC_COLORS.get(name))
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel(ylabel); ax.set_title(title)
    if ylim:
        ax.set_ylim(*ylim)
    ax.grid(True, axis="y", alpha=0.4); ax.legend(fontsize=8, framealpha=0.2)
    return _save(fig, out_path)


def heatmap(matrix, row_labels, col_labels, out_path, title, cbar_label="",
            cmap="viridis", fmt="{:.2f}", vmin=None, vmax=None):
    fig, ax = plt.subplots(figsize=(max(6, len(col_labels) * 0.95),
                                    max(3.5, len(row_labels) * 0.55)))
    im = ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(col_labels))); ax.set_xticklabels(col_labels, rotation=30, ha="right", fontsize=8)
    ax.set_yticks(range(len(row_labels))); ax.set_yticklabels(row_labels, fontsize=8)
    for i in range(len(row_labels)):
        for j in range(len(col_labels)):
            val = matrix[i][j]
            if val == val:  # not NaN
                ax.text(j, i, fmt.format(val), ha="center", va="center",
                        color="white", fontsize=7)
    cb = fig.colorbar(im, ax=ax); cb.set_label(cbar_label, fontsize=8)
    ax.set_title(title)
    return _save(fig, out_path)


def complexity_loglog(profile: dict, out_path, title="Compute scaling"):
    """profile: {key: {sizes, times, exponent}} → log-log time vs N."""
    fig, ax = plt.subplots(figsize=(6.5, 4.3))
    for k, p in profile.items():
        ax.plot(p["sizes"], p["times"], "-o", ms=4, color=METRIC_COLORS.get(k),
                label=f"{METRIC_INFO[k].label}  (p≈{p['exponent']:.2f})")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("point count N"); ax.set_ylabel("metric compute time (s)")
    ax.set_title(title); ax.grid(True, which="both", alpha=0.35)
    ax.legend(fontsize=8, framealpha=0.2)
    return _save(fig, out_path)


def distributions(df, metric_key, out_path, by="tier", title=None):
    """Box/strip of one metric's distribution grouped by `by` (tier or mode)."""
    groups = list(dict.fromkeys(df[by]))
    data = [df[df[by] == gname][metric_key].dropna().values for gname in groups]
    fig, ax = plt.subplots(figsize=(max(6, len(groups) * 1.1), 4.2))
    bp = ax.boxplot(data, labels=groups, patch_artist=True, showfliers=False)
    for patch in bp["boxes"]:
        patch.set(facecolor=METRIC_COLORS.get(metric_key, "#58a6ff"), alpha=0.5)
    for med in bp["medians"]:
        med.set(color="#c9d1d9")
    ax.set_ylabel(METRIC_INFO[metric_key].label)
    ax.set_title(title or f"{METRIC_INFO[metric_key].label} by {by}")
    ax.set_xticklabels(groups, rotation=30, ha="right", fontsize=8)
    ax.grid(True, axis="y", alpha=0.4)
    return _save(fig, out_path)


def sensitivity_grid(df, metric_keys, modes, out_path, x_col="level",
                     title="Metric response by failure mode"):
    """Small-multiples: one panel per mode, normalized score vs severity, all
    metrics overlaid. The at-a-glance 'which metric catches which failure' view."""
    ncol = 4
    nrow = int(np.ceil(len(modes) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.4 * ncol, 2.7 * nrow), squeeze=False)
    for idx, mode in enumerate(modes):
        ax = axes[idx // ncol][idx % ncol]
        sub = df[df["mode"] == mode]
        if len(sub) == 0:
            ax.axis("off"); continue
        # use drift_intensity as x when it varies, else the controlled level
        xc = "drift_intensity" if sub["drift_intensity"].nunique() > 1 else x_col
        g = sub.groupby(xc)[metric_keys].mean().reset_index()
        for k in metric_keys:
            ax.plot(g[xc], _norm(g[k]), "-o", ms=2.5, lw=1.4, color=METRIC_COLORS.get(k))
        tier = sub["tier"].iloc[0]
        ax.set_title(f"{mode}\n({tier}, x={xc.split('_')[0]})", fontsize=8)
        ax.tick_params(labelsize=7); ax.grid(True, alpha=0.35)
    for j in range(len(modes), nrow * ncol):
        axes[j // ncol][j % ncol].axis("off")
    handles = [plt.Line2D([], [], color=METRIC_COLORS.get(k), label=METRIC_INFO[k].label)
               for k in metric_keys]
    fig.legend(handles=handles, loc="lower center", ncol=len(metric_keys),
               fontsize=8, framealpha=0.2, bbox_to_anchor=(0.5, -0.04))
    fig.suptitle(title, y=1.0)
    return _save(fig, out_path)


def correlation_bars(corr: dict, out_path, ylabel="Spearman |ρ| vs oracle",
                     title="Reference-free metric agreement with chamfer oracle"):
    """corr: {metric_key: value} → sorted horizontal bars."""
    items = sorted(corr.items(), key=lambda kv: -abs(kv[1]))
    fig, ax = plt.subplots(figsize=(6.5, 0.55 * len(items) + 1))
    labels = [METRIC_INFO[k].label for k, _ in items]
    vals = [abs(v) for _, v in items]
    ax.barh(labels, vals, color=[METRIC_COLORS.get(k) for k, _ in items])
    ax.invert_yaxis(); ax.set_xlim(0, 1); ax.set_xlabel(ylabel); ax.set_title(title)
    for i, v in enumerate(vals):
        ax.text(v + 0.01, i, f"{v:.2f}", va="center", fontsize=8)
    ax.grid(True, axis="x", alpha=0.35)
    return _save(fig, out_path)


def cloud_bev(observed, reference, out_path, title="BEV: observed vs reference"):
    """Side-by-side top-down scatter of reference and observed clouds."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
    for ax, pts, name, col in ((axes[0], reference, "reference (ideal)", "#3fb950"),
                               (axes[1], observed, "observed (drifted)", "#f85149")):
        if pts is not None and len(pts):
            s = pts if len(pts) <= 60000 else pts[np.random.default_rng(0).choice(len(pts), 60000, replace=False)]
            ax.scatter(s[:, 0], s[:, 1], s=0.4, c=col, alpha=0.4, linewidths=0)
        ax.set_aspect("equal"); ax.set_title(name, fontsize=10)
        ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)"); ax.grid(True, alpha=0.3)
    fig.suptitle(title)
    return _save(fig, out_path)
