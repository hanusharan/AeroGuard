"""Seeded forest builder, per-condition fit, threshold selection and the single-shot scoring ledger
(PROTOCOL.md sections 5, 6, 11).

Why a new builder: ``ml.models.build_random_forest`` hard-codes ``random_state = config.ML_SEED``, and
``ml.temporal_experiment.fit_rf_and_threshold`` calls it, so neither can fit a second seed. The parameters,
the leakage guard (``get_xy``) and the threshold procedure (``select_threshold_train_then_val``) are reused
unchanged; only the seed is explicit here. A test compares the parameter sets.

``fit_condition`` accepts a TRAIN table and a VALIDATION table only; its signature has no test argument,
and ``require_split`` refuses a table tagged with any other split.
"""

import resource
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from ml.calibration import select_threshold_train_then_val  # reused unchanged
from ml.temporal_config_v03 import FROZEN_RF_PARAMS  # reused unchanged
from ml.temporal_experiment import get_xy  # reused unchanged (leakage guard, NaN refusal)

from . import SEEDS
from .conditions import features_for, validate_manifest
from .guards import GateViolation, assert_output_path
from .population import SplitTable, require_split, usable_mask

RF_PARAMS: Dict[str, object] = dict(FROZEN_RF_PARAMS)
_PROTOCOL_RF_PARAMS = {"n_estimators": 200, "max_depth": 12, "min_samples_leaf": 5, "class_weight": "balanced_subsample"}
if RF_PARAMS != _PROTOCOL_RF_PARAMS:  # pragma: no cover - guards against upstream drift
    raise ImportError("FROZEN_RF_PARAMS differs from the protocol's recorded forest configuration")


def build_forest(seed: int) -> RandomForestClassifier:
    """The frozen forest configuration with an explicit seed (no hyperparameter search)."""
    if int(seed) != seed or not (0 <= int(seed) < 2 ** 32):
        raise ValueError(f"invalid forest seed {seed!r}")
    return RandomForestClassifier(**RF_PARAMS, random_state=int(seed), n_jobs=-1)


def apply_threshold(score, threshold: float) -> np.ndarray:
    """Strict ``score > threshold`` as 0/1 ints (the canonical operator)."""
    return (np.asarray(score, dtype=float) > float(threshold)).astype(int)


@dataclass
class FitResult:
    condition: str
    seed: int
    model: object
    threshold: float
    threshold_info: dict
    features: List[str]
    rf_params: dict
    n_train_rows: int
    n_val_rows: int
    fit_seconds: float
    peak_rss_mb: float
    resolved_max_features: Optional[int]
    train_score: Optional[np.ndarray] = field(default=None, repr=False)
    val_score: Optional[np.ndarray] = field(default=None, repr=False)

    def record(self) -> dict:
        """JSON-able fit record (no arrays, no model)."""
        return {
            "status": "FITTED", "condition": self.condition, "seed": self.seed, "n_features": len(self.features), "features": list(self.features),
            "rf_params": dict(self.rf_params), "threshold": self.threshold, "operator": "strict >", "threshold_info": self.threshold_info,
            "n_train_rows": self.n_train_rows, "n_val_rows": self.n_val_rows, "fit_seconds": self.fit_seconds,
            "peak_rss_mb": self.peak_rss_mb, "resolved_max_features": self.resolved_max_features,
        }


@dataclass
class FitFailure:
    condition: str
    seed: int
    error_type: str
    error: str
    traceback: str

    def record(self) -> dict:
        return {"status": "FAILED", "condition": self.condition, "seed": self.seed, "error_type": self.error_type,
                "error": self.error, "traceback": self.traceback}


def _resolved_max_features(model) -> Optional[int]:
    try:
        return int(model.estimators_[0].max_features_)
    except Exception:
        return None


def fit_condition(condition: str, seed: int, train: SplitTable, val: SplitTable,
                  builder: Callable[[int], object] = build_forest, keep_scores: bool = True) -> FitResult:
    """Fit one (condition, seed) on TRAIN; select the probability threshold on VALIDATION with the existing
    train-then-validation procedure. Test data cannot be passed."""
    require_split(train, "train")
    require_split(val, "val")
    validate_manifest()
    if seed not in SEEDS:
        raise GateViolation(f"seed {seed} is not in the pre-specified list {SEEDS}")
    features = features_for(condition)
    tr_mask = pd.Series(usable_mask(train.df), index=train.df.index)
    va_mask = pd.Series(usable_mask(val.df), index=val.df.index)
    x_tr, y_tr, _ = get_xy(train.df, features, tr_mask)
    x_va, y_va, _ = get_xy(val.df, features, va_mask)
    t0 = time.perf_counter()
    model = builder(seed)
    model.fit(x_tr, y_tr)
    tr_score = model.predict_proba(x_tr)[:, 1]
    va_score = model.predict_proba(x_va)[:, 1]
    threshold, info = select_threshold_train_then_val(y_tr, tr_score, y_va, va_score)
    seconds = time.perf_counter() - t0
    return FitResult(
        condition=condition, seed=int(seed), model=model, threshold=float(threshold), threshold_info=info, features=list(features),
        rf_params=dict(RF_PARAMS), n_train_rows=int(len(x_tr)), n_val_rows=int(len(x_va)), fit_seconds=float(seconds),
        peak_rss_mb=float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024.0,
        resolved_max_features=_resolved_max_features(model),
        train_score=tr_score if keep_scores else None, val_score=va_score if keep_scores else None,
    )


def try_fit(condition: str, seed: int, train: SplitTable, val: SplitTable, builder: Callable[[int], object] = build_forest):
    """Fit, or return a recorded failure. A failure is never retried here and never silently dropped."""
    try:
        return fit_condition(condition, seed, train, val, builder=builder)
    except GateViolation:
        raise   # a protocol violation stops the run; it is not a "failed fit"
    except Exception as exc:  # noqa: BLE001 - record any fit exception verbatim
        return FitFailure(condition, int(seed), type(exc).__name__, str(exc), traceback.format_exc())


def score_rows(model, df: pd.DataFrame, features: Sequence[str], mask) -> np.ndarray:
    """Positive-class probability on the masked rows, using exactly the manifest columns."""
    feats = list(features)
    if hasattr(model, "feature_names_in_") and list(model.feature_names_in_) != feats:
        raise ValueError("model feature names differ from the requested feature list")
    x, _, _ = get_xy(df, feats, pd.Series(np.asarray(mask, dtype=bool), index=df.index))
    return model.predict_proba(x)[:, 1]


def score_test(fit: FitResult, test: SplitTable) -> np.ndarray:
    """Score the TEST rows with a fitted model; the threshold is not touched. Single use per (condition, seed) is
    enforced by ``SingleShotLedger``, which the caller must claim first."""
    require_split(test, "test")
    mask = usable_mask(test.df)
    return score_rows(fit.model, test.df, fit.features, mask)


class SingleShotLedger:
    """Each fitted model's test scores are computed once (PROTOCOL.md section 11). Claiming creates an
    exclusive marker file; a second claim for the same (condition, seed) raises."""

    def __init__(self, directory, root):
        self.directory = Path(directory)
        self.root = root

    def claim(self, condition: str, seed: int) -> Path:
        path = assert_output_path(self.directory / f"test_scored_{condition}_{int(seed)}.lock", self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "x") as f:
                f.write("claimed\n")
        except FileExistsError:
            raise GateViolation(f"test scores for ({condition}, {seed}) were already computed (single-shot rule)") from None
        return path


def save_model_exclusive(model, path, root) -> Path:
    """Persist a fitted model below the run directory (scratch). Never to the frozen-model path."""
    import joblib

    target = assert_output_path(path, root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "xb") as f:
        joblib.dump(model, f)
    return target
