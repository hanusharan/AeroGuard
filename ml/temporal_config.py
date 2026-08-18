"""Stage 4 (temporal early-warning experiment) configuration.

Separate from ml/config.py (Stage 3, frozen) so nothing here can ever
overwrite a Stage-3 baseline path/constant. All new outputs live under
outputs/ml_temporal/; all new cached feature tables live under
data/ml_temporal/ -- both new, additive locations. data/ml/, data/
processed/, data/splits/, and outputs/ml_baseline/ are read-only inputs
to this module and are never written to.
"""

import os
from typing import List

from . import config as base_config

PROJECT_ROOT = base_config.PROJECT_ROOT
DATA_DIR = base_config.DATA_DIR

# --- read-only inputs (Stage 3, frozen) --------------------------------------
ML_V2_DIR = os.path.join(DATA_DIR, "ml")  # ml_{train,val,test}_v2.parquet
METADATA_PATH = base_config.METADATA_PATH  # trajectory_metadata_v2.csv (regime, initial_airspeed)
BASELINE_OUTPUTS_DIR = os.path.join(PROJECT_ROOT, "outputs", "ml_baseline")
BASELINE_MODELS_DIR = os.path.join(BASELINE_OUTPUTS_DIR, "models")

# --- new, additive locations --------------------------------------------------
TEMPORAL_DATA_DIR = os.path.join(DATA_DIR, "ml_temporal")
OUTPUTS_DIR = os.path.join(PROJECT_ROOT, "outputs", "ml_temporal")
PLOTS_DIR = os.path.join(OUTPUTS_DIR, "plots")
MODELS_DIR = os.path.join(OUTPUTS_DIR, "models")
METRICS_DIR = os.path.join(OUTPUTS_DIR, "metrics")


def ensure_dirs() -> None:
    for d in (TEMPORAL_DATA_DIR, OUTPUTS_DIR, PLOTS_DIR, MODELS_DIR, METRICS_DIR):
        os.makedirs(d, exist_ok=True)


# --- reproducibility ----------------------------------------------------------
SEED = base_config.ML_SEED  # same seed as every other ML stage, for consistency
DT = 0.01  # matches generation_config_v2.json

# --- target ---------------------------------------------------------------------
TARGET_COL = base_config.TARGET_COL  # "future_stall_5s"
TARGET_AVAILABLE_COL = base_config.TARGET_AVAILABLE_COL  # "future_stall_5s_available"
LABELING_HORIZON_S = base_config.LABELING_HORIZON_S  # 5.0

# --- temporal observation windows under investigation (Task 2) ----------------
HISTORY_WINDOWS_S: List[float] = [0.5, 1.0, 2.0, 3.0]

# --- feature-set building blocks (Task 3/4) ------------------------------------
# Model A/B "instantaneous state" -- current-value-only physics quantities,
# identical set to evaluate_baseline.py's ABLATION_A_state_only.
INSTANTANEOUS_STATE_FEATURES: List[str] = [
    "V", "alpha", "gamma", "pitch_rate", "altitude", "elevator", "throttle", "stall_margin",
]

# Model B/D "state + 1-step causal derivatives" -- identical definition to
# ml/train_baseline.py's CORE_FEATURES, plus the new (numerically-checked,
# see build_temporal_panel docstring) alpha second derivative.
STATE_DERIVATIVE_FEATURES: List[str] = INSTANTANEOUS_STATE_FEATURES + [
    "dV_dt", "dalpha_dt", "dgamma_dt", "dq_dt", "d2alpha_dt2",
]

# Variables given the FULL causal-statistic panel (mean/min/max/range/slope/
# trend) per window -- alpha only. stall_margin is an exact algebraic
# transform of alpha (stall_margin = alpha_at_cl_peak - alpha, Task
# constraint), so computing a second, redundant window-stat panel for it
# would just relabel the same information under new column names.
ALPHA_FULL_PANEL_VAR = "alpha"

# Variables given ONLY a causal OLS slope per window (Task 3: "V slope",
# "gamma slope", pitch rate / dq_dt already covered as a 1-step derivative
# in STATE_DERIVATIVE_FEATURES, so here we add its own *windowed* slope too).
SLOPE_ONLY_VARS: List[str] = ["V", "gamma", "pitch_rate"]

# Variables given ONLY a raw endpoint difference per window (Task 3:
# "elevator recent change" -- a control-input step size, not a rate).
ENDPOINT_DIFF_ONLY_VARS: List[str] = ["elevator"]


def _fmt(window_s: float) -> str:
    """0.5 -> '0.5', 1.0 -> '1', 2.0 -> '2', 3.0 -> '3' (matches the
    naming already used by the existing alpha_trend_1s/2s/3s columns)."""
    return f"{window_s:g}"


def temporal_feature_columns(window_s: float) -> List[str]:
    """The Task-3 causal temporal summary features for ONE history
    window: alpha's full statistic panel (6 features) + V/gamma/
    pitch_rate slopes (3) + elevator's recent change (1) = 10 features
    per window. Deliberately NOT hundreds of features (Task 3)."""
    w = _fmt(window_s)
    cols = [
        f"alpha_mean_{w}s", f"alpha_min_{w}s", f"alpha_max_{w}s", f"alpha_range_{w}s",
        f"alpha_slope_{w}s", f"alpha_trend_{w}s",
    ]
    cols += [f"{v}_slope_{w}s" for v in SLOPE_ONLY_VARS]
    cols += [f"{v}_change_{w}s" for v in ENDPOINT_DIFF_ONLY_VARS]
    return cols


def model_c_features(window_s: float) -> List[str]:
    """Model C: instantaneous state + causal temporal summary features
    for ONE window. Deliberately excludes the 1-step derivatives (those
    belong to Model B/D) so the marginal effect of *window* temporal
    structure is isolated from the effect of 1-step derivatives."""
    return INSTANTANEOUS_STATE_FEATURES + temporal_feature_columns(window_s)


def model_d_features(window_s: float) -> List[str]:
    """Model D: state + 1-step derivatives + causal temporal summary
    features for ONE window (the full stack)."""
    return STATE_DERIVATIVE_FEATURES + temporal_feature_columns(window_s)


# Row-population columns required by the LARGEST window subsume every
# smaller window (uniform dt, same trajectory -- see
# ml/temporal_features.py:common_subset_mask for the nesting argument).
LARGEST_WINDOW_S = max(HISTORY_WINDOWS_S)
