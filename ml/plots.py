"""New plot types for the baseline experiment (calibration, lead-time
buckets). Core plots (PR/ROC curves, confusion matrix, feature
importance, probability distribution) are already in ml/evaluation.py
and are reused as-is by train_baseline.py / evaluate_baseline.py.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_calibration_curve(calibration_info: dict, save_path: str, title: str):
    predicted = calibration_info["calibration_predicted"]
    observed = calibration_info["calibration_observed"]
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "--", color="gray", label="perfectly calibrated")
    ax.plot(predicted, observed, "o-", color="darkorange", label="model")
    ax.set_xlabel("mean predicted probability")
    ax.set_ylabel("observed positive fraction")
    ax.set_title(f"{title}\nBrier score = {calibration_info['brier_score']:.4f}")
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_lead_time_buckets(lead_time_df: pd.DataFrame, save_path: str, title: str):
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(lead_time_df))
    recalls = lead_time_df["recall"].to_numpy()
    ax.bar(x, np.nan_to_num(recalls, nan=0.0), color="steelblue")
    for i, (r, n) in enumerate(zip(recalls, lead_time_df["n_positive_rows"])):
        label = "n/a" if np.isnan(r) else f"{r:.2f}\n(n={n})"
        ax.text(i, (0 if np.isnan(r) else r) + 0.02, label, ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(lead_time_df["bucket"])
    ax.set_ylim(0, 1.15)
    ax.set_xlabel("time until the actual future stall crossing")
    ax.set_ylabel("recall (fraction of positive rows correctly warned)")
    ax.set_title(title)
    ax.grid(True, axis="y")
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
