"""Classification metrics and diagnostic plots (Section 13).

PR-AUC/precision/recall/F1 are the headline metrics (accuracy is
reported only as a secondary figure, per Section 13 -- the positive
class is rare, ~7% of available rows, so accuracy alone would be
misleading).
"""

import os
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


def compute_classification_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_score: np.ndarray) -> Dict[str, float]:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    return {
        "pr_auc": float(average_precision_score(y_true, y_score)),
        "roc_auc": float(roc_auc_score(y_true, y_score)) if len(np.unique(y_true)) > 1 else float("nan"),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "n_positive": int(np.sum(y_true == 1)),
        "n_negative": int(np.sum(y_true == 0)),
    }


def plot_pr_curves(curves: List[Tuple[str, np.ndarray, np.ndarray]], save_path: str, title: str = "Precision-Recall curves (TEST)"):
    """curves: list of (label, y_true, y_score)."""
    fig, ax = plt.subplots(figsize=(8, 7))
    for label, y_true, y_score in curves:
        precision, recall, _ = precision_recall_curve(y_true, y_score)
        ap = average_precision_score(y_true, y_score)
        ax.plot(recall, precision, label=f"{label} (AP={ap:.3f})", linewidth=1.5)
    base_rate = curves[0][1].mean() if curves else 0
    ax.axhline(base_rate, color="gray", linestyle="--", linewidth=1, label=f"chance (positive rate={base_rate:.3f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title(title)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_roc_curves(curves: List[Tuple[str, np.ndarray, np.ndarray]], save_path: str, title: str = "ROC curves (TEST, secondary visualization)"):
    fig, ax = plt.subplots(figsize=(8, 7))
    for label, y_true, y_score in curves:
        fpr, tpr, _ = roc_curve(y_true, y_score)
        auc = roc_auc_score(y_true, y_score)
        ax.plot(fpr, tpr, label=f"{label} (AUC={auc:.3f})", linewidth=1.5)
    ax.plot([0, 1], [0, 1], color="gray", linestyle="--", linewidth=1, label="chance")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(title)
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_confusion_matrix(cm_dict: dict, save_path: str, title: str):
    cm = np.array([[cm_dict["tn"], cm_dict["fp"]], [cm_dict["fn"], cm_dict["tp"]]])
    fig, ax = plt.subplots(figsize=(5, 4.5))
    im = ax.imshow(cm, cmap="Blues")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center",
                     color="white" if cm[i, j] > cm.max() / 2 else "black")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["pred 0", "pred 1"])
    ax.set_yticks([0, 1]); ax.set_yticklabels(["true 0", "true 1"])
    ax.set_title(title, fontsize=10)
    fig.colorbar(im, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_probability_distribution(y_true: np.ndarray, y_score: np.ndarray, save_path: str, title: str, threshold: float = None):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(y_score[y_true == 0], bins=60, alpha=0.6, density=True, label="true negative", color="steelblue")
    ax.hist(y_score[y_true == 1], bins=60, alpha=0.6, density=True, label="true positive", color="crimson")
    if threshold is not None:
        ax.axvline(threshold, color="k", linestyle="--", linewidth=1.5, label=f"frozen threshold={threshold:.3f}")
    ax.set_xlabel("predicted probability / score")
    ax.set_ylabel("density")
    ax.set_title(title)
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_feature_importance(names: List[str], importances: np.ndarray, save_path: str, title: str, top_n: int = 20):
    order = np.argsort(importances)[::-1][:top_n]
    fig, ax = plt.subplots(figsize=(8, max(3, 0.35 * len(order))))
    ax.barh([names[i] for i in order][::-1], importances[order][::-1], color="teal")
    ax.set_xlabel("importance")
    ax.set_title(title)
    ax.grid(True, axis="x")
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
