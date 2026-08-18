"""v0.3 temporal early-warning experiment configuration.

Additive companion to ml/temporal_config.py -- mirrors its structure
exactly but points at the v0.3 full-scale dataset
(processed_dataset_v3.parquet / split_manifest_v3.csv /
trajectory_metadata_v3.csv, generated and gated in
outputs/dataset_audit_v3/v03_generation_report.md). Feature-set
definitions (which columns each model uses) are DATASET-VERSION-
AGNOSTIC -- they are reused unchanged, by direct import, from
ml/temporal_config.py, so "same feature definitions" between the v0.2
and v0.3 experiments is enforced structurally, not just by convention.

Never modifies aeroguard/, data/processed/, data/splits/, data/ml/,
data/ml_temporal/, or outputs/ml_temporal/ (all v0.1/v0.2, read-only).
All new outputs live under outputs/ml_v03/; all new cached feature
tables live under data/ml_temporal_v03/ (both new, additive locations).
"""

import os

from . import config as base_config
from .temporal_config import (  # noqa: F401  (re-exported for the v0.3 driver/experiment modules)
    DT,
    ENDPOINT_DIFF_ONLY_VARS,
    INSTANTANEOUS_STATE_FEATURES,
    LABELING_HORIZON_S,
    SLOPE_ONLY_VARS,
    STATE_DERIVATIVE_FEATURES,
    TARGET_AVAILABLE_COL,
    TARGET_COL,
    _fmt,
    model_c_features,
    model_d_features,
    temporal_feature_columns,
)

PROJECT_ROOT = base_config.PROJECT_ROOT
DATA_DIR = base_config.DATA_DIR

# --- read-only inputs (v0.3 full-scale dataset, generated+gated; never modified here) ------
PROCESSED_DATASET_PATH = os.path.join(DATA_DIR, "processed", "processed_dataset_v3.parquet")
METADATA_PATH = os.path.join(DATA_DIR, "metadata", "trajectory_metadata_v3.csv")
SPLIT_MANIFEST_PATH = os.path.join(DATA_DIR, "splits", "split_manifest_v3.csv")
GENERATION_CONFIG_PATH = os.path.join(DATA_DIR, "metadata", "generation_config_v3.json")

# --- read-only reference (v0.2's own already-computed results; never rerun/modified) -------
V2_OUTPUTS_DIR = os.path.join(PROJECT_ROOT, "outputs", "ml_temporal")
V2_PRECURSOR_DIR = os.path.join(PROJECT_ROOT, "outputs", "dataset_audit_v3")  # v0.3 precursor classification (physical, dataset-side)

# --- new, additive locations ----------------------------------------------------------------
TEMPORAL_DATA_DIR = os.path.join(DATA_DIR, "ml_temporal_v03")
OUTPUTS_DIR = os.path.join(PROJECT_ROOT, "outputs", "ml_v03")
PLOTS_DIR = os.path.join(OUTPUTS_DIR, "plots")
MODELS_DIR = os.path.join(OUTPUTS_DIR, "models")
METRICS_DIR = os.path.join(OUTPUTS_DIR, "metrics")


def ensure_dirs() -> None:
    for d in (TEMPORAL_DATA_DIR, OUTPUTS_DIR, PLOTS_DIR, MODELS_DIR, METRICS_DIR):
        os.makedirs(d, exist_ok=True)


# --- reproducibility --------------------------------------------------------------------------
SEED = base_config.ML_SEED  # same seed as every other ML stage (v0.2 included), for consistency

# --- pre-registered v0.3 experiment lock (Phase 1) ---------------------------------------------
# Per the explicit efficiency instruction: a SMALL window robustness check only
# (0.5/1/2s), not the full v0.2 [0.5,1,2,3]s ablation -- v0.2 already showed
# longer windows don't help (temporal_experiment_report.md Sec 5/6), and Model
# C (temporal stats without derivatives) is skipped entirely for the same
# reason (v0.2 Sec 5: C is consistently worse than A at every window). 1s
# remains the PRIMARY model, exactly as in v0.2.
HISTORY_WINDOWS_S = [0.5, 1.0, 2.0]
PRIMARY_WINDOW_S = 1.0

# Frozen RF hyperparameters -- REUSED UNCHANGED from v0.2's own tuning result
# (outputs/ml_temporal/experiment_config.json: rf_hyperparameters_frozen).
# No re-tuning stage: "use the already validated RF configuration from the
# v0.2 study unless there is a concrete reason it cannot be applied" -- there
# is none here (same feature dimensionality, same target, same row scale).
FROZEN_RF_PARAMS = {
    "n_estimators": 200,
    "max_depth": 12,
    "min_samples_leaf": 5,
    "class_weight": "balanced_subsample",
}

# The regime this whole dataset iteration was built to test (replaces v0.2's
# "near_boundary"). Never a model input -- used only for post-hoc regime
# breakdown and the Phase 7 generalization check.
GRADUAL_REGIME_NAME = "gradual_approach_v3"

LARGEST_WINDOW_S = max(HISTORY_WINDOWS_S)
