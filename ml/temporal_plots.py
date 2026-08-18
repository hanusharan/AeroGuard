"""Stage-4 plot types not already covered by ml/evaluation.py or
ml/plots.py (both reused as-is where they already fit: PR/ROC curves,
confusion matrix, feature importance, probability distribution,
calibration curve).
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def plot_lead_time_recall_comparison(model_lead_dfs: dict, save_path: str, title: str):
    """model_lead_dfs: {model_label: lead_time_bucket_analysis DataFrame}."""
    buckets = model_lead_dfs[next(iter(model_lead_dfs))]["bucket"].tolist()
    n_models = len(model_lead_dfs)
    x = np.arange(len(buckets))
    width = 0.8 / max(n_models, 1)

    fig, ax = plt.subplots(figsize=(10, 6))
    for i, (label, df) in enumerate(model_lead_dfs.items()):
        recalls = df.set_index("bucket").reindex(buckets)["recall"].to_numpy()
        ax.bar(x + i * width, np.nan_to_num(recalls, nan=0.0), width=width, label=label)
    ax.set_xticks(x + width * (n_models - 1) / 2)
    ax.set_xticklabels(buckets)
    ax.set_xlabel("time until the actual future stall crossing")
    ax.set_ylabel("recall")
    ax.set_ylim(0, 1.05)
    ax.set_title(title)
    ax.legend(fontsize=8)
    ax.grid(True, axis="y")
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_warning_composition(composition_rows: list, save_path: str, title: str):
    labels = [r["time_to_nearest_crossing_bucket"] for r in composition_rows]
    fractions = [r["fraction_of_all_warnings"] for r in composition_rows]
    colors = ["crimson" if not r["true_positive_by_construction"] else "steelblue" for r in composition_rows]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(range(len(labels)), fractions, color=colors)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("fraction of all issued warnings")
    ax.set_title(f"{title}\n(blue = true positive by construction, red = false alarm)")
    ax.grid(True, axis="y")
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_pr_auc_vs_window(window_results: dict, save_path: str, title: str = "PR-AUC vs. history window length (common subset, TEST)"):
    """window_results: {model_key: result_dict} from run_window_ablation,
    with keys like 'B_state_derivatives', 'C_0.5s', 'D_0.5s', ... ."""
    windows = []
    c_scores, d_scores = [], []
    for key, res in window_results.items():
        if key.startswith("C_") or key.startswith("D_"):
            wtag = key.split("_", 1)[1].rstrip("s")
            w = float(wtag)
            if key.startswith("C_"):
                c_scores.append((w, res["test_metrics"]["pr_auc"]))
            else:
                d_scores.append((w, res["test_metrics"]["pr_auc"]))
    c_scores.sort(); d_scores.sort()
    b_pr_auc = window_results.get("B_state_derivatives", {}).get("test_metrics", {}).get("pr_auc")
    a_pr_auc = window_results.get("A_frozen_baseline", {}).get("test_metrics", {}).get("pr_auc")

    fig, ax = plt.subplots(figsize=(8, 6))
    if c_scores:
        ax.plot(*zip(*c_scores), "o-", label="C: state + temporal summary", color="darkorange")
    if d_scores:
        ax.plot(*zip(*d_scores), "s-", label="D: state + derivatives + temporal summary", color="crimson")
    if b_pr_auc is not None:
        ax.axhline(b_pr_auc, color="steelblue", linestyle="--", label=f"B: state + derivatives (no window, PR-AUC={b_pr_auc:.3f})")
    if a_pr_auc is not None:
        ax.axhline(a_pr_auc, color="gray", linestyle=":", label=f"A: frozen instantaneous baseline (PR-AUC={a_pr_auc:.3f})")
    ax.set_xlabel("history window length (s)")
    ax.set_ylabel("PR-AUC (common subset, TEST)")
    ax.set_title(title)
    ax.legend(fontsize=8)
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_lead_time_recall_vs_window(window_results: dict, save_path: str, title: str = "Early-warning recall vs. history window length"):
    """The plot the research question actually hinges on: does a LONGER
    window move USEFUL (2-3s+) recall earlier, not just PR-AUC."""
    buckets_of_interest = ["1-2s", "2-3s", "3-4s"]
    fig, ax = plt.subplots(figsize=(8, 6))
    for bucket in buckets_of_interest:
        pts = []
        for key, res in window_results.items():
            if not key.startswith("D_"):
                continue
            w = float(key.split("_", 1)[1].rstrip("s"))
            row = next((r for r in res["lead_time_recall_bucket"] if r["bucket"] == bucket), None)
            if row is not None:
                pts.append((w, row["recall"]))
        pts.sort()
        if pts:
            ax.plot(*zip(*pts), "o-", label=f"recall in {bucket} bucket (Model D)")
    ax.set_xlabel("history window length (s)")
    ax.set_ylabel("recall")
    ax.set_ylim(0, 1.05)
    ax.set_title(title)
    ax.legend(fontsize=8)
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_warning_time_distribution(lead_times_s: list, save_path: str, title: str):
    lead_times_s = np.asarray(lead_times_s, dtype=float)
    fig, ax = plt.subplots(figsize=(8, 5))
    if len(lead_times_s) > 0:
        ax.hist(lead_times_s, bins=30, color="teal", alpha=0.8)
        ax.axvline(np.median(lead_times_s), color="k", linestyle="--", label=f"median={np.median(lead_times_s):.2f}s")
        ax.legend()
    ax.set_xlabel("credited warning (lead) time, seconds")
    ax.set_ylabel("count of correctly-warned stall events")
    ax.set_title(title)
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_lead_time_by_group(df: pd.DataFrame, group_col: str, save_path: str, title: str):
    """df: concatenated lead_time_bucket_analysis rows with an extra
    `group_col` column (regime or airspeed bin)."""
    groups = pd.unique(df[group_col])
    buckets = pd.unique(df["bucket"])
    x = np.arange(len(buckets))
    width = 0.8 / max(len(groups), 1)

    fig, ax = plt.subplots(figsize=(10, 6))
    for i, g in enumerate(groups):
        sub = df[df[group_col] == g].set_index("bucket").reindex(buckets)
        recalls = sub["recall"].to_numpy()
        ax.bar(x + i * width, np.nan_to_num(recalls, nan=0.0), width=width, label=str(g))
    ax.set_xticks(x + width * (len(groups) - 1) / 2)
    ax.set_xticklabels(buckets)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("time until the actual future stall crossing")
    ax.set_ylabel("recall")
    ax.set_title(title)
    ax.legend(fontsize=8)
    ax.grid(True, axis="y")
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_diagnosis_distributions(samples: dict, variables: list, lead_times_s: list, save_path: str,
                                  title: str = "Feature distributions: near-crossing vs. safe states"):
    """samples: {(lead_time_s, variable): (near_vals, safe_vals)} from
    ml.temporal_experiment.physics_information_diagnosis. One subplot
    per variable, overlaying the 'safe' distribution against a few
    selected lead times so overlap (or separation) is directly visible."""
    n = len(variables)
    ncols = 2
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(11, 3.2 * nrows))
    axes = np.atleast_1d(axes).ravel()
    colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(lead_times_s)))

    for ax, var in zip(axes, variables):
        safe_vals = None
        for L, color in zip(lead_times_s, colors):
            near_vals, safe_vals = samples.get((L, var), (np.array([]), np.array([])))
            if len(near_vals) > 5:
                ax.hist(near_vals, bins=40, density=True, histtype="step", color=color, label=f"{L:g}s before crossing", linewidth=1.4)
        if safe_vals is not None and len(safe_vals) > 5:
            ax.hist(safe_vals, bins=40, density=True, histtype="stepfilled", color="gray", alpha=0.3, label="safe (no crossing near)")
        ax.set_title(var, fontsize=10)
        ax.grid(True, alpha=0.4)

    for ax in axes[n:]:
        ax.axis("off")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=min(len(lead_times_s) + 1, 4), fontsize=8, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(title)
    fig.tight_layout(rect=[0, 0.06, 1, 0.97])
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
