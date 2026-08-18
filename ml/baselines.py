"""Rule-based early-warning baselines (Section 7/8).

Both rules are calibrated using TRAIN (candidate generation + scoring),
with the final single operating point selected on VALIDATION -- never
TEST. Once `.fit()` returns, the rule's parameters are frozen; calling
`.predict()`/`.predict_score()` afterward never re-touches TRAIN/VAL.
"""

from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from .calibration import top_k_thresholds_by_train_f1 as _top_k_thresholds_by_train_f1


@dataclass
class AoAThresholdRule:
    """Warn when alpha exceeds a frozen threshold.

    Calibration procedure (deterministic, documented):
      1. Compute the full TRAIN precision-recall curve using alpha itself
         as a continuous score against future_stall_5s.
      2. Rank all candidate thresholds from that curve by TRAIN F1; take
         the top `top_k`.
      3. Evaluate each of those `top_k` candidates on VALIDATION F1;
         select the single threshold with the best VALIDATION F1.
      4. Freeze it as `self.threshold_rad`.
    """

    top_k: int = 10
    threshold_rad: float = field(init=False, default=None)
    calibration_info: dict = field(init=False, default_factory=dict)

    def fit(self, train_alpha: np.ndarray, y_train: np.ndarray, val_alpha: np.ndarray, y_val: np.ndarray) -> "AoAThresholdRule":
        candidates = _top_k_thresholds_by_train_f1(y_train, train_alpha, self.top_k)
        val_scores = []
        for thr in candidates:
            pred = (val_alpha > thr).astype(int)
            val_scores.append(f1_score(y_val, pred, zero_division=0))
        best_idx = int(np.argmax(val_scores))
        self.threshold_rad = float(candidates[best_idx])
        self.calibration_info = {
            "method": "top_k_train_f1_then_best_val_f1",
            "top_k": self.top_k,
            "candidate_thresholds_rad": [float(c) for c in candidates],
            "candidate_val_f1": [float(s) for s in val_scores],
            "selected_threshold_rad": self.threshold_rad,
            "selected_threshold_deg": float(np.degrees(self.threshold_rad)),
            "selected_val_f1": float(val_scores[best_idx]),
        }
        return self

    def predict(self, alpha: np.ndarray) -> np.ndarray:
        if self.threshold_rad is None:
            raise RuntimeError("AoAThresholdRule.fit() must be called before predict()")
        return (np.asarray(alpha) > self.threshold_rad).astype(int)

    def predict_score(self, alpha: np.ndarray) -> np.ndarray:
        """alpha itself, used as a continuous score for PR-AUC/ROC curves
        (monotonic with the rule's decision, well-defined for a
        single-feature threshold rule)."""
        return np.asarray(alpha)


@dataclass
class TrendRule:
    """Warn when stall_margin is small AND dalpha_dt is sufficiently
    positive: (stall_margin <= margin_threshold) AND (dalpha_dt >= trend_threshold).

    Calibration procedure (deterministic, documented):
      1. Build candidate margin_threshold values from percentiles of TRAIN
         stall_margin (5th-95th percentile, 15 points) and candidate
         trend_threshold values from percentiles of TRAIN dalpha_dt
         (50th-99th percentile, 15 points) -- a modest 15x15=225-combo grid,
         not an exhaustive search.
      2. Score every combo's F1 on TRAIN; take the top `top_k` combos.
      3. Evaluate those on VALIDATION F1; select the combo with the best
         VALIDATION F1.
      4. Freeze (margin_threshold, trend_threshold).
    """

    top_k: int = 10
    n_margin_candidates: int = 15
    n_trend_candidates: int = 15
    margin_threshold: float = field(init=False, default=None)
    trend_threshold: float = field(init=False, default=None)
    calibration_info: dict = field(init=False, default_factory=dict)

    def fit(
        self,
        train_margin: np.ndarray, train_trend: np.ndarray, y_train: np.ndarray,
        val_margin: np.ndarray, val_trend: np.ndarray, y_val: np.ndarray,
    ) -> "TrendRule":
        margin_candidates = np.unique(np.percentile(train_margin, np.linspace(5, 95, self.n_margin_candidates)))
        trend_candidates = np.unique(np.percentile(train_trend, np.linspace(50, 99, self.n_trend_candidates)))

        combos: List[Tuple[float, float]] = []
        train_f1s: List[float] = []
        for m in margin_candidates:
            pred_margin_ok = train_margin <= m
            for t in trend_candidates:
                pred = (pred_margin_ok & (train_trend >= t)).astype(int)
                combos.append((float(m), float(t)))
                train_f1s.append(f1_score(y_train, pred, zero_division=0))

        train_f1s = np.array(train_f1s)
        top_idx = np.argsort(-train_f1s)[: self.top_k]

        val_f1s = []
        for idx in top_idx:
            m, t = combos[idx]
            pred = ((val_margin <= m) & (val_trend >= t)).astype(int)
            val_f1s.append(f1_score(y_val, pred, zero_division=0))

        best_local = int(np.argmax(val_f1s))
        best_combo = combos[top_idx[best_local]]
        self.margin_threshold, self.trend_threshold = best_combo

        self.calibration_info = {
            "method": "grid_top_k_train_f1_then_best_val_f1",
            "grid_size": len(combos),
            "top_k": self.top_k,
            "top_k_combos_rad": [combos[i] for i in top_idx],
            "top_k_train_f1": [float(train_f1s[i]) for i in top_idx],
            "top_k_val_f1": [float(v) for v in val_f1s],
            "selected_margin_threshold_rad": float(self.margin_threshold),
            "selected_margin_threshold_deg": float(np.degrees(self.margin_threshold)),
            "selected_trend_threshold_rad_s": float(self.trend_threshold),
            "selected_trend_threshold_deg_s": float(np.degrees(self.trend_threshold)),
            "selected_val_f1": float(val_f1s[best_local]),
        }
        return self

    def predict(self, margin: np.ndarray, trend: np.ndarray) -> np.ndarray:
        if self.margin_threshold is None:
            raise RuntimeError("TrendRule.fit() must be called before predict()")
        margin, trend = np.asarray(margin), np.asarray(trend)
        return ((margin <= self.margin_threshold) & (trend >= self.trend_threshold)).astype(int)

    def predict_score(self, margin: np.ndarray, trend: np.ndarray) -> np.ndarray:
        """A monotonic derived combination (higher = more warning-like)
        used ONLY for PR-AUC/ROC curve visualization -- the frozen rule
        itself always uses the two discrete thresholds above, not this
        score."""
        margin, trend = np.asarray(margin), np.asarray(trend)
        return trend - margin


@dataclass
class AlwaysSafeBaseline:
    """The trivial baseline (Task 4, Step 2, item 1): never warn.

    No fitting needed -- included so every other result can be read
    against "what does doing nothing look like". Because the positive
    class is rare (~5-10%), this baseline scores deceptively well on
    accuracy alone, which is exactly why accuracy is not used as this
    project's headline metric."""

    def fit(self, *_args, **_kwargs) -> "AlwaysSafeBaseline":
        return self

    def predict(self, X) -> np.ndarray:
        n = len(X) if hasattr(X, "__len__") else X.shape[0]
        return np.zeros(n, dtype=int)

    def predict_score(self, X) -> np.ndarray:
        n = len(X) if hasattr(X, "__len__") else X.shape[0]
        return np.zeros(n, dtype=float)


@dataclass
class StallMarginThresholdRule:
    """Warn when stall_margin drops to or below a frozen threshold.

    IMPORTANT REDUNDANCY NOTE: stall_margin = alpha_at_cl_peak - alpha
    is an EXACT algebraic transform of alpha (verified in the Stage-2/3
    dataset audits: residual 0.0, correlation with alpha = -1.0000).
    A "stall_margin <= m" rule and an "alpha > (alpha_at_cl_peak - m)"
    rule are therefore mathematically the IDENTICAL rule, just phrased
    on an inverted, shifted scale -- calibrating this rule independently
    is expected to reproduce AoAThresholdRule's decisions exactly (up to
    which of the tied candidate thresholds the top-k/F1 procedure
    happens to pick). This is included because Step 2 asks for it
    explicitly, not because it is expected to add new information beyond
    AoAThresholdRule -- the report states this plainly rather than
    presenting the two as if they were independent evidence.

    Calibration procedure: identical top-k-train-F1-then-best-val-F1
    procedure as AoAThresholdRule, just scored on -stall_margin (so
    "more warning-like" is still "higher score", matching the shared
    calibration helper's convention).
    """

    top_k: int = 10
    threshold_rad: float = field(init=False, default=None)
    calibration_info: dict = field(init=False, default_factory=dict)

    def fit(self, train_margin: np.ndarray, y_train: np.ndarray, val_margin: np.ndarray, y_val: np.ndarray) -> "StallMarginThresholdRule":
        from .calibration import select_threshold_train_then_val

        neg_threshold, info = select_threshold_train_then_val(y_train, -np.asarray(train_margin), y_val, -np.asarray(val_margin), top_k=self.top_k)
        self.threshold_rad = -neg_threshold  # warn when margin <= threshold_rad
        self.calibration_info = info | {
            "selected_threshold_rad": self.threshold_rad,
            "selected_threshold_deg": float(np.degrees(self.threshold_rad)),
        }
        return self

    def predict(self, margin: np.ndarray) -> np.ndarray:
        if self.threshold_rad is None:
            raise RuntimeError("StallMarginThresholdRule.fit() must be called before predict()")
        return (np.asarray(margin) <= self.threshold_rad).astype(int)

    def predict_score(self, margin: np.ndarray) -> np.ndarray:
        """Negated so that, like every other rule's score, higher = more warning-like."""
        return -np.asarray(margin)
