"""Shared TRAIN-then-VALIDATION threshold-calibration procedure.

Used identically by both rule baselines (ml/baselines.py) and the ML
probability threshold (ml/training.py), so the whole experiment applies
one consistent, documented calibration methodology:
  1. Rank candidate thresholds by TRAIN F1.
  2. Take the top `top_k`.
  3. Evaluate those `top_k` on VALIDATION F1; keep the best.
  4. Freeze it -- TEST is never touched here.
"""

from typing import Tuple

import numpy as np
from sklearn.metrics import f1_score, precision_recall_curve


def top_k_thresholds_by_train_f1(y_train: np.ndarray, score_train: np.ndarray, top_k: int) -> np.ndarray:
    precision, recall, thresholds = precision_recall_curve(y_train, score_train)
    precision, recall = precision[:-1], recall[:-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        f1 = np.where((precision + recall) > 0, 2 * precision * recall / (precision + recall), 0.0)
    order = np.argsort(-f1)
    return thresholds[order[:top_k]]


def select_threshold_train_then_val(
    y_train: np.ndarray, score_train: np.ndarray,
    y_val: np.ndarray, score_val: np.ndarray,
    top_k: int = 10,
) -> Tuple[float, dict]:
    """Returns (threshold, info) where info documents every candidate
    considered and its VAL F1, for full auditability."""
    candidates = top_k_thresholds_by_train_f1(y_train, score_train, top_k)
    val_f1s = []
    for thr in candidates:
        pred = (score_val > thr).astype(int)
        val_f1s.append(f1_score(y_val, pred, zero_division=0))
    best_idx = int(np.argmax(val_f1s))
    threshold = float(candidates[best_idx])
    info = {
        "method": "top_k_train_f1_then_best_val_f1",
        "top_k": top_k,
        "candidate_thresholds": [float(c) for c in candidates],
        "candidate_val_f1": [float(v) for v in val_f1s],
        "selected_threshold": threshold,
        "selected_val_f1": float(val_f1s[best_idx]),
    }
    return threshold, info
