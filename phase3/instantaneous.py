"""Item 31: the instantaneous-state model.

Why this is not ``ml.temporal_experiment_v03.fit_model_a_instantaneous``: that function
fits the model AND scores the test split inside one call (and uses a 2 s mask), so it
cannot be split into the protocol's G6 (fit, train/validation only) and G7 (score, once)
steps. The ingredients ARE reused unchanged: ``build_random_forest`` (through
``fit_rf_and_threshold``), ``get_xy`` (its leakage guard and NaN refusal) and the
existing ``FROZEN_RF_PARAMS``.

Fitting accepts a TRAIN table and a VALIDATION table only (checked at run time); the
function signature has no argument through which a test table could enter.
"""

import importlib.metadata as md
import os
import platform
import re
import resource
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Sequence

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from ml import config as mlcfg
from ml.temporal_config import INSTANTANEOUS_STATE_FEATURES  # reused unchanged
from ml.temporal_config_v03 import FROZEN_RF_PARAMS  # reused unchanged
from ml.temporal_experiment import fit_rf_and_threshold, get_xy  # reused unchanged

from . import MODEL_SEED
from .population import SplitTable, require_split, usable_mask

# PROTOCOL.md 7.1: the manifest is written out literally and asserted equal to the existing definition.
INSTANTANEOUS_FEATURES: List[str] = ["V", "alpha", "gamma", "pitch_rate", "altitude", "elevator", "throttle", "stall_margin"]
if INSTANTANEOUS_FEATURES != list(INSTANTANEOUS_STATE_FEATURES):  # pragma: no cover - guards against upstream drift
    raise ImportError("Phase 3 instantaneous manifest differs from ml.temporal_config.INSTANTANEOUS_STATE_FEATURES")

# PROTOCOL.md 7.2: hyperparameters of the frozen model's forest, reused with NO search.
RF_PARAMS: Dict[str, object] = dict(FROZEN_RF_PARAMS)
_PROTOCOL_RF_PARAMS = {"n_estimators": 200, "max_depth": 12, "min_samples_leaf": 5, "class_weight": "balanced_subsample"}
if RF_PARAMS != _PROTOCOL_RF_PARAMS:  # pragma: no cover
    raise ImportError("FROZEN_RF_PARAMS differs from the protocol's recorded configuration")
if mlcfg.ML_SEED != MODEL_SEED:  # pragma: no cover
    raise ImportError("ml.config.ML_SEED differs from the protocol's recorded seed")

EXCLUDED_EXACT = frozenset({
    "future_stall_5s", "future_stall_5s_available", "is_unsafe", "time_to_stall",
    "trajectory_id", "time", "split",
    "dV_dt", "dalpha_dt", "dgamma_dt", "dq_dt", "d2alpha_dt2",
    "theta", "vertical_speed", "thrust",
})
_WINDOW_SUFFIX = re.compile(r"_(0\.5|1|2|3)s$")


def validate_feature_manifest(features: Sequence[str]) -> List[str]:
    """Raise unless ``features`` is exactly the approved manifest and contains no temporal,
    derivative, label, identifier or future-derived column."""
    feats = list(features)
    bad = [f for f in feats if f in EXCLUDED_EXACT or _WINDOW_SUFFIX.search(f)]
    if bad:
        raise ValueError(f"feature set contains excluded column(s): {bad}")
    if feats != INSTANTANEOUS_FEATURES:
        raise ValueError(f"feature set {feats} differs from the approved manifest {INSTANTANEOUS_FEATURES}")
    return feats


def library_versions() -> Dict[str, str]:
    out = {"python": sys.version.split()[0], "platform": platform.platform(), "cpu_count": str(os.cpu_count())}
    for pkg in ("scikit-learn", "numpy", "pandas", "pyarrow", "scipy", "joblib"):
        try:
            out[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            out[pkg] = "not installed"
    return out


def has_no_preprocessing(model) -> bool:
    """The protocol fits no scaler: the estimator must be the bare forest, not a Pipeline."""
    return isinstance(model, RandomForestClassifier) and not hasattr(model, "steps")


@dataclass
class FitResult:
    model: RandomForestClassifier
    threshold: float
    threshold_info: dict
    features: List[str]
    rf_params: dict
    seed: int
    n_train_rows: int
    n_val_rows: int
    fit_seconds: float
    peak_rss_mb: float
    versions: Dict[str, str] = field(default_factory=dict)


def fit_instantaneous(train: SplitTable, val: SplitTable) -> FitResult:
    """Fit on TRAIN, choose the probability threshold on VALIDATION (existing procedure:
    top 10 by train F1, best validation F1). Test data cannot be passed."""
    require_split(train, "train")
    require_split(val, "val")
    features = validate_feature_manifest(INSTANTANEOUS_FEATURES)
    tr_mask = pd.Series(usable_mask(train.df), index=train.df.index)
    va_mask = pd.Series(usable_mask(val.df), index=val.df.index)
    x_tr, y_tr, _ = get_xy(train.df, features, tr_mask)
    x_va, y_va, _ = get_xy(val.df, features, va_mask)
    t0 = time.perf_counter()
    model, threshold, info = fit_rf_and_threshold(x_tr, y_tr, x_va, y_va, RF_PARAMS)
    seconds = time.perf_counter() - t0
    if not has_no_preprocessing(model):  # pragma: no cover
        raise RuntimeError("fitted estimator is not a bare RandomForestClassifier")
    return FitResult(
        model=model, threshold=float(threshold), threshold_info=info, features=list(features), rf_params=dict(RF_PARAMS),
        seed=MODEL_SEED, n_train_rows=int(len(x_tr)), n_val_rows=int(len(x_va)), fit_seconds=float(seconds),
        peak_rss_mb=float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024.0, versions=library_versions(),
    )


def predict_scores(model, df: pd.DataFrame, mask, features: Sequence[str] = INSTANTANEOUS_FEATURES) -> np.ndarray:
    """Probability of the positive class on the masked rows, using exactly the manifest columns."""
    feats = list(features)
    if hasattr(model, "feature_names_in_") and list(model.feature_names_in_) != feats:
        raise ValueError("model feature names differ from the requested feature list")
    x, _, _ = get_xy(df, feats, pd.Series(np.asarray(mask, dtype=bool), index=df.index))
    return model.predict_proba(x)[:, 1]


def apply_threshold(score, threshold: float) -> np.ndarray:
    """Strict ``score > threshold`` as 0/1 ints (the canonical operator)."""
    return (np.asarray(score, dtype=float) > float(threshold)).astype(int)
