"""Matched operating point M-OP (PROTOCOL.md section 9.4): defined on VALIDATION scores and labels only.

For each seed the target is C0's validation false-positive rate at its own selected threshold. Every other
condition gets the smallest threshold, among its distinct validation scores, whose validation false-positive
rate (strict ``score > t``) does not exceed that target. No test label or score is involved.
"""

from typing import Dict, Mapping

import numpy as np


def fpr_at(y, score, threshold: float) -> float:
    """False-positive rate of ``score > threshold`` among the negatives."""
    y = np.asarray(y).astype(int)
    s = np.asarray(score, dtype=float)
    neg = s[y == 0]
    if neg.size == 0:
        raise ValueError("no negative rows: false-positive rate undefined")
    return float(np.mean(neg > float(threshold)))


def matched_threshold(y_val, score_val, target_fpr: float) -> Dict[str, float]:
    y = np.asarray(y_val).astype(int)
    s = np.asarray(score_val, dtype=float)
    if y.shape != s.shape:
        raise ValueError("labels and scores must have the same shape")
    if not np.isfinite(s).all():
        raise ValueError("validation scores must be finite")
    neg = np.sort(s[y == 0])
    if neg.size == 0:
        raise ValueError("no negative rows: false-positive rate undefined")
    if not (0.0 <= target_fpr <= 1.0):
        raise ValueError("target false-positive rate must be in [0, 1]")
    cand = np.unique(s)                                           # ascending distinct validation scores
    fp = neg.size - np.searchsorted(neg, cand, side="right")      # negatives with score > candidate
    rate = fp / neg.size                                          # non-increasing in the candidate
    ok = np.flatnonzero(rate <= target_fpr)
    # the largest score always gives rate 0 <= target, so ok is never empty
    i = int(ok[0])
    return {"threshold": float(cand[i]), "achieved_fpr": float(rate[i]), "target_fpr": float(target_fpr)}


def matched_thresholds(y_val, val_scores: Mapping[str, np.ndarray], reference: str, reference_threshold: float) -> Dict[str, Dict[str, float]]:
    """Per condition: threshold matched to the reference condition's validation FPR at ``reference_threshold``."""
    if reference not in val_scores:
        raise ValueError(f"unknown reference {reference!r}")
    target = fpr_at(y_val, val_scores[reference], reference_threshold)
    out = {}
    for name, s in val_scores.items():
        out[name] = {**matched_threshold(y_val, s, target), "reference": reference, "reference_threshold": float(reference_threshold)}
    return out
