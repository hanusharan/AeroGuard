"""Metrics beyond the core classification set already in ml/evaluation.py:
Brier score / calibration, threshold sweeps, lead-time-by-time-to-event
analysis, feature ablation, and post-hoc regime/airspeed breakdowns.

Nothing here fits anything on TEST data -- these are all pure
evaluation/analysis functions operating on already-frozen predictions.
"""

from typing import Dict, List, Sequence

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss, f1_score, precision_score, recall_score


def compute_brier_and_calibration(y_true: np.ndarray, y_score: np.ndarray, n_bins: int = 10) -> dict:
    """Brier score (mean squared error between predicted probability and
    the 0/1 outcome -- lower is better, 0 is perfect) plus a reliability
    curve: for each of n_bins probability bins, the mean predicted
    probability vs. the actual observed positive fraction. A
    well-calibrated model has these two nearly equal in every bin."""
    brier = float(brier_score_loss(y_true, y_score))
    observed, predicted = calibration_curve(y_true, y_score, n_bins=n_bins, strategy="uniform")
    return {"brier_score": brier, "calibration_predicted": predicted.tolist(), "calibration_observed": observed.tolist(), "n_bins": n_bins}


def threshold_sweep(y_true: np.ndarray, y_score: np.ndarray, thresholds: Sequence[float] = None) -> pd.DataFrame:
    """Full threshold sweep table (Step 6). Intended to be run on
    VALIDATION only -- the resulting table is used to pick a threshold,
    never to re-check TEST performance across many thresholds (that
    would itself be a form of test-set peeking)."""
    if thresholds is None:
        thresholds = np.round(np.arange(0.10, 0.91, 0.05), 2)

    rows = []
    n_neg = int(np.sum(y_true == 0))
    n_total = len(y_true)
    for thr in thresholds:
        pred = (y_score >= thr).astype(int)
        tp = int(np.sum((pred == 1) & (y_true == 1)))
        fp = int(np.sum((pred == 1) & (y_true == 0)))
        fn = int(np.sum((pred == 0) & (y_true == 1)))
        tn = int(np.sum((pred == 0) & (y_true == 0)))
        rows.append({
            "threshold": float(thr),
            "precision": precision_score(y_true, pred, zero_division=0),
            "recall": recall_score(y_true, pred, zero_division=0),
            "f1": f1_score(y_true, pred, zero_division=0),
            "false_positive_rate": fp / n_neg if n_neg > 0 else float("nan"),
            "warning_rate": (tp + fp) / n_total,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        })
    return pd.DataFrame(rows)


LEAD_TIME_BINS_S = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]


def lead_time_bucket_analysis(time_to_stall: np.ndarray, y_true: np.ndarray, y_pred: np.ndarray, bins=LEAD_TIME_BINS_S) -> pd.DataFrame:
    """Step 7: among rows that are TRUE positives-in-waiting (a real
    future crossing is coming), bucket by how far away that crossing
    actually is (time_to_stall, already independently verified in the
    dataset-prep stage) and measure the model's RECALL within each
    bucket. This directly answers "does the model warn early, or only
    right before impact" -- a single overall recall number cannot show
    this, since it averages over both cases.

    Only rows with y_true==1 are used (rows where a crossing genuinely
    occurs within the next 5s) -- recall is only meaningfully defined
    for the positive class. time_to_stall for these rows is always
    <= 5.0s by construction (future_stall_5s==1 implies a crossing
    within the 5s window), so the 5 bins below fully partition them.
    """
    rows = []
    positive_mask = y_true == 1
    for lo, hi in bins:
        in_bucket = positive_mask & (time_to_stall > lo) & (time_to_stall <= hi)
        n = int(in_bucket.sum())
        if n == 0:
            rows.append({"bucket": f"{lo}-{hi}s", "n_positive_rows": 0, "recall": float("nan"), "n_warned": 0, "n_missed": 0})
            continue
        n_warned = int(y_pred[in_bucket].sum())
        rows.append({
            "bucket": f"{lo}-{hi}s", "n_positive_rows": n,
            "recall": n_warned / n, "n_warned": n_warned, "n_missed": n - n_warned,
        })
    return pd.DataFrame(rows)


def regime_breakdown(y_true: np.ndarray, y_pred: np.ndarray, y_score: np.ndarray, regime: np.ndarray) -> pd.DataFrame:
    """Step 9: post-hoc only -- regime is never a model input, just used
    here to slice already-computed predictions for analysis."""
    rows = []
    for r in pd.unique(regime):
        mask = regime == r
        yt, yp = y_true[mask], y_pred[mask]
        n_pos = int(np.sum(yt == 1))
        row = {"regime": r, "n_rows": int(mask.sum()), "n_positive": n_pos}
        if n_pos > 0:
            row["recall"] = recall_score(yt, yp, zero_division=0)
        else:
            row["recall"] = float("nan")
        row["precision"] = precision_score(yt, yp, zero_division=0)
        row["f1"] = f1_score(yt, yp, zero_division=0)
        rows.append(row)
    return pd.DataFrame(rows)


def airspeed_bin_breakdown(y_true: np.ndarray, y_pred: np.ndarray, initial_airspeed: np.ndarray, bins=(30, 40, 50, 60, 75)) -> pd.DataFrame:
    labels = [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins) - 1)]
    binned = pd.cut(pd.Series(initial_airspeed), bins=bins, labels=labels, include_lowest=True)
    rows = []
    for label in labels:
        mask = (binned == label).to_numpy()
        yt, yp = y_true[mask], y_pred[mask]
        n_pos = int(np.sum(yt == 1))
        rows.append({
            "airspeed_bin_m_s": label, "n_rows": int(mask.sum()), "n_positive": n_pos,
            "recall": recall_score(yt, yp, zero_division=0) if n_pos > 0 else float("nan"),
            "precision": precision_score(yt, yp, zero_division=0),
        })
    return pd.DataFrame(rows)
