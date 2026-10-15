"""Models of PROTOCOL.md section 2: retrained RFs, rule baselines and the frozen v0.3 model.

Fitting uses only training-configuration TRAIN rows; thresholds use only
training-configuration VAL rows (``ml.calibration.select_threshold_train_then_val``,
strict ``score > threshold``). No function here accepts evaluation rows for fitting.
"""

import hashlib
from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from ml.baselines import AoAThresholdRule, StallMarginThresholdRule  # reused unchanged
from ml.calibration import select_threshold_train_then_val            # reused unchanged
from ml.temporal_config_v03 import FROZEN_RF_PARAMS                   # reused unchanged

from . import FROZEN_MODEL_RELPATH, FROZEN_MODEL_SHA256, FROZEN_THRESHOLD
from .panel import FEATURES_A, FEATURES_D, FEATURES_D_NOSM, FEATURES_XD, FEATURES_XD_NOSM

RF_FEATURES: Dict[str, List[str]] = {"M_D": FEATURES_D, "M_D_noSM": FEATURES_D_NOSM, "M_A": FEATURES_A,
                                     "X_D": FEATURES_XD, "X_D_noSM": FEATURES_XD_NOSM}


def X(df: pd.DataFrame, cols: List[str]) -> np.ndarray:
    return df[cols].to_numpy(dtype=np.float32)


def fit_rf(name: str, train: pd.DataFrame, val: pd.DataFrame, seed: int, n_jobs: int = -1) -> dict:
    cols = RF_FEATURES[name]
    clf = RandomForestClassifier(**FROZEN_RF_PARAMS, random_state=seed, n_jobs=n_jobs)
    clf.fit(X(train, cols), train["future_stall_5s"].to_numpy())
    s_tr = clf.predict_proba(X(train, cols))[:, 1]
    s_va = clf.predict_proba(X(val, cols))[:, 1]
    thr, info = select_threshold_train_then_val(train["future_stall_5s"].to_numpy(), s_tr, val["future_stall_5s"].to_numpy(), s_va)
    return {"name": name, "seed": seed, "features": cols, "model": clf, "threshold": float(thr), "threshold_info": info}


def score_rf(fitted: dict, df: pd.DataFrame) -> np.ndarray:
    return fitted["model"].predict_proba(X(df, fitted["features"]))[:, 1]


def fit_rules(train: pd.DataFrame, val: pd.DataFrame) -> Dict[str, dict]:
    ytr, yva = train["future_stall_5s"].to_numpy(), val["future_stall_5s"].to_numpy()
    aoa = AoAThresholdRule().fit(train["alpha"].to_numpy(dtype=float), ytr, val["alpha"].to_numpy(dtype=float), yva)
    sm = StallMarginThresholdRule().fit(train["stall_margin"].to_numpy(dtype=float), ytr, val["stall_margin"].to_numpy(dtype=float), yva)
    # As scores: alpha for R_AoA (warn if alpha > thr); -stall_margin for R_SM (warn if -sm > -thr, i.e. sm < thr).
    return {"R_AoA": {"threshold": float(aoa.threshold_rad), "info": aoa.calibration_info},
            "R_SM": {"threshold": float(-sm.threshold_rad), "info": sm.calibration_info}}


def score_rule(name: str, df: pd.DataFrame) -> np.ndarray:
    if name == "R_AoA":
        return df["alpha"].to_numpy(dtype=float)
    if name == "R_SM":
        return -df["stall_margin"].to_numpy(dtype=float)
    raise ValueError(name)


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_frozen(repo: Path) -> dict:
    p = Path(repo) / FROZEN_MODEL_RELPATH
    got = sha256(p)
    if got != FROZEN_MODEL_SHA256:
        raise SystemExit(f"STOP: frozen model hash differs ({got})")
    obj = joblib.load(p)
    model = obj["model"] if isinstance(obj, dict) and "model" in obj else obj
    feats = list(getattr(model, "feature_names_in_", FEATURES_D))
    return {"name": "F_v03", "model": model, "features": feats if len(feats) == 23 else FEATURES_D,
            "threshold": FROZEN_THRESHOLD}


def score_frozen(frozen: dict, df: pd.DataFrame) -> np.ndarray:
    m = frozen["model"]
    Xf = df[frozen["features"]]
    if hasattr(m, "feature_names_in_"):
        return m.predict_proba(Xf.astype(np.float64))[:, 1]
    return m.predict_proba(Xf.to_numpy(dtype=np.float32))[:, 1]
