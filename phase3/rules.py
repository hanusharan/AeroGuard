"""Item 28 (AoA baseline) and Item 30 (stall margin) rule wrappers.

The AoA rule itself is the EXISTING ``ml.baselines.AoAThresholdRule`` (signed alpha,
strict ``>``, top-10 train F1 then best validation F1). It is reused unchanged. The
wrappers here add only what the protocol requires and the existing code lacks:

* every input is checked BEFORE it reaches the existing code: arrays must be finite
  (the existing ``predict`` silently predicts "safe" for NaN, see PROTOCOL.md 5.3),
  one-dimensional, of equal length, with binary labels, and on a radian scale;
* the fit functions accept TRAIN and VALIDATION arrays only - there is no argument
  through which a test array could enter (checked by tests);
* the two-sided sensitivity variant (PROTOCOL.md 5.4) is the same procedure on ``|alpha|``;
* the stall-margin equivalence helpers (PROTOCOL.md 6) used for a decision-count check.

Nothing here reads data.
"""

from typing import Dict

import numpy as np

from ml.baselines import AoAThresholdRule, StallMarginThresholdRule  # reused unchanged

from . import A_PEAK_RAD

ALPHA_ABS_MAX_RAD = float(np.pi)  # an angle of attack beyond +/- pi rad is not physical: degrees-scale input


class InvalidInputError(ValueError):
    """Base class: the rule refuses invalid input instead of treating it as safe."""


class NonFiniteInputError(InvalidInputError):
    """NaN or +/-inf in an input array."""


class UnitError(InvalidInputError):
    """alpha does not look like it is expressed in radians."""


def require_finite_1d(values, name: str) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        raise InvalidInputError(f"{name} must be one-dimensional, got shape {arr.shape}")
    bad = ~np.isfinite(arr)
    if bad.any():
        raise NonFiniteInputError(f"{name} contains {int(bad.sum())} non-finite value(s) (NaN/inf); refusing to treat them as safe")
    return arr


def require_radians(alpha: np.ndarray, name: str = "alpha") -> np.ndarray:
    if alpha.size and float(np.max(np.abs(alpha))) > ALPHA_ABS_MAX_RAD:
        raise UnitError(f"{name} has |value| > pi ({float(np.max(np.abs(alpha))):.4g}); angles of attack must be in radians")
    return alpha


def require_binary_labels(values, name: str) -> np.ndarray:
    arr = require_finite_1d(values, name)
    if not np.isin(arr, (0.0, 1.0)).all():
        raise InvalidInputError(f"{name} must contain only 0/1 labels")
    return arr.astype(int)


def _validated_alpha(values, name: str) -> np.ndarray:
    return require_radians(require_finite_1d(values, name), name)


def _fit_on(transform, train_alpha, y_train, val_alpha, y_val, top_k: int) -> AoAThresholdRule:
    a_tr = transform(_validated_alpha(train_alpha, "train_alpha"))
    a_va = transform(_validated_alpha(val_alpha, "val_alpha"))
    y_tr = require_binary_labels(y_train, "y_train")
    y_va = require_binary_labels(y_val, "y_val")
    if len(a_tr) != len(y_tr):
        raise InvalidInputError("train_alpha and y_train must have the same length")
    if len(a_va) != len(y_va):
        raise InvalidInputError("val_alpha and y_val must have the same length")
    if y_tr.min() == y_tr.max() or y_va.min() == y_va.max():
        raise InvalidInputError("train and validation labels must each contain both classes")
    return AoAThresholdRule(top_k=top_k).fit(a_tr, y_tr, a_va, y_va)


def fit_signed_aoa(train_alpha, y_train, val_alpha, y_val, top_k: int = 10) -> AoAThresholdRule:
    """Primary rule: ``alpha > threshold`` (signed), existing selection procedure."""
    return _fit_on(lambda a: a, train_alpha, y_train, val_alpha, y_val, top_k)


def fit_two_sided_aoa(train_alpha, y_train, val_alpha, y_val, top_k: int = 10) -> AoAThresholdRule:
    """Sensitivity variant (PROTOCOL.md 5.4): the identical procedure applied to ``|alpha|``."""
    return _fit_on(np.abs, train_alpha, y_train, val_alpha, y_val, top_k)


def predict_signed(rule: AoAThresholdRule, alpha) -> np.ndarray:
    """Strict ``alpha > threshold`` as 0/1 ints; invalid input raises."""
    return rule.predict(_validated_alpha(alpha, "alpha"))


def predict_two_sided(rule: AoAThresholdRule, alpha) -> np.ndarray:
    """Strict ``|alpha| > threshold`` as 0/1 ints; invalid input raises."""
    return rule.predict(np.abs(_validated_alpha(alpha, "alpha")))


def score_signed(alpha) -> np.ndarray:
    """Continuous score of the signed rule (alpha itself), for PR-AUC / ROC-AUC."""
    return _validated_alpha(alpha, "alpha").copy()


def score_two_sided(alpha) -> np.ndarray:
    return np.abs(_validated_alpha(alpha, "alpha"))


def rule_summary(rule: AoAThresholdRule) -> Dict[str, object]:
    """JSON-ready record of a fitted rule, including the full candidate list."""
    if rule.threshold_rad is None:
        raise InvalidInputError("rule is not fitted")
    info = dict(rule.calibration_info)
    return {
        "operator": "strict >",
        "threshold_rad": float(rule.threshold_rad),
        "threshold_deg": float(np.degrees(rule.threshold_rad)),
        "calibration_info": info,
    }


# --- Item 30: the stall-margin rule is the AoA rule on a shifted, inverted scale ----------

def stall_margin(alpha, a_p: float = A_PEAK_RAD) -> np.ndarray:
    """``stall_margin = alpha_at_cl_peak - alpha`` (same formula as aeroguard_dataset.features)."""
    return a_p - _validated_alpha(alpha, "alpha")


def equivalent_margin_threshold(tau_alpha: float, a_p: float = A_PEAK_RAD) -> float:
    """tau_m such that ``margin <= tau_m`` matches ``alpha > tau_alpha`` away from the threshold."""
    return float(a_p - tau_alpha)


def margin_rule_predict(margin, tau_m: float) -> np.ndarray:
    """Decision of the existing ``StallMarginThresholdRule.predict``: ``margin <= tau_m``."""
    rule = StallMarginThresholdRule()
    rule.threshold_rad = float(tau_m)
    return rule.predict(require_finite_1d(margin, "margin"))


def equivalence_report(alpha, tau_alpha: float, a_p: float = A_PEAK_RAD) -> Dict[str, int]:
    """Count rows on which the AoA rule (``alpha > tau``) and the margin rule with the
    equivalent threshold disagree. Decision counts only: no labels, no metrics."""
    a = _validated_alpha(alpha, "alpha")
    aoa = (a > tau_alpha).astype(int)
    margin_pred = margin_rule_predict(a_p - a, equivalent_margin_threshold(tau_alpha, a_p))
    differ = aoa != margin_pred
    at_tie = a == tau_alpha
    return {
        "n_rows": int(a.size),
        "n_disagree": int(differ.sum()),
        "n_disagree_exactly_at_threshold": int((differ & at_tie).sum()),
        "n_disagree_elsewhere": int((differ & ~at_tie).sum()),
        "n_rows_exactly_at_threshold": int(at_tie.sum()),
    }
