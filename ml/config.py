"""All Stage 3 ML-experiment parameters, in one documented place.

Mirrors aeroguard_dataset/config.py's philosophy: every path, seed, and
feature-set definition used anywhere in the ML pipeline is defined here.
"""

import os
from dataclasses import dataclass, field
from typing import List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUTS_ML_DIR = os.path.join(PROJECT_ROOT, "outputs", "ml")

# --- frozen dataset inputs (v0.2, do not regenerate/modify) -----------------
PROCESSED_DATASET_PATH = os.path.join(DATA_DIR, "processed", "processed_dataset_v2.parquet")
RAW_DATASET_PATH = os.path.join(DATA_DIR, "raw", "raw_telemetry_v2.parquet")
METADATA_PATH = os.path.join(DATA_DIR, "metadata", "trajectory_metadata_v2.csv")
GENERATION_CONFIG_PATH = os.path.join(DATA_DIR, "metadata", "generation_config_v2.json")
FEATURE_SCHEMA_PATH = os.path.join(DATA_DIR, "metadata", "feature_schema_v2.json")
SPLIT_MANIFEST_PATH = os.path.join(DATA_DIR, "splits", "split_manifest_v2.csv")

# --- outputs ------------------------------------------------------------------
METRICS_DIR = os.path.join(OUTPUTS_ML_DIR, "metrics")
PLOTS_DIR = os.path.join(OUTPUTS_ML_DIR, "plots")
MODELS_DIR = os.path.join(OUTPUTS_ML_DIR, "models")
REPORTS_DIR = os.path.join(OUTPUTS_ML_DIR, "reports")


def ensure_output_dirs() -> None:
    for d in (METRICS_DIR, PLOTS_DIR, MODELS_DIR, REPORTS_DIR):
        os.makedirs(d, exist_ok=True)


# --- reproducibility -----------------------------------------------------------
# Same value as the dataset-generation seed, reused here for consistency
# (this is the ML pipeline's own seed for model random_state / grid
# search / any stochastic step -- it does not affect the frozen dataset).
ML_SEED = 20260817

# --- target -----------------------------------------------------------------
TARGET_COL = "future_stall_5s"
TARGET_AVAILABLE_COL = "future_stall_5s_available"
LABELING_HORIZON_S = 5.0  # matches data/metadata/generation_config_v2.json

# Columns that must NEVER appear in a feature set (future-derived or the
# event flag itself -- guarded programmatically in features.py).
FORBIDDEN_FEATURE_COLUMNS = frozenset({
    TARGET_COL, TARGET_AVAILABLE_COL, "is_unsafe",
})

# --- feature sets (Section 2) ------------------------------------------------
FEATURE_SET_A: List[str] = ["alpha"]

FEATURE_SET_B: List[str] = [
    "V", "alpha", "theta", "gamma", "altitude", "vertical_speed",
    "pitch_rate", "thrust", "elevator", "throttle", "stall_margin",
]

FEATURE_SET_C: List[str] = FEATURE_SET_B + ["dV_dt", "dalpha_dt"]

FEATURE_SETS = {"A_alpha_only": FEATURE_SET_A, "B_state": FEATURE_SET_B, "C_state_dynamics": FEATURE_SET_C}

# Columns whose NaN-ness defines the "common subset" (Section 5): both
# derivative features are NaN on exactly the first row of every
# trajectory (by construction, see aeroguard_dataset/features.py). All
# of FEATURE_SET_B's other columns are never NaN (confirmed in the
# Stage-2 dataset audit). Restricting to rows where these are available
# lets Model Group A/B/C be compared on an identical row population,
# even though A/B don't themselves need these two columns.
COMMON_SUBSET_REQUIRED_COLUMNS: List[str] = ["dV_dt", "dalpha_dt"]

STALL_BOUNDARY_ALPHA_DEG = 16.068034017008504  # from generation_config_v2.json, for reference/plots only


@dataclass(frozen=True)
class MLConfig:
    seed: int = ML_SEED
    target_col: str = TARGET_COL
    target_available_col: str = TARGET_AVAILABLE_COL
    labeling_horizon_s: float = LABELING_HORIZON_S
    dt: float = 0.01  # matches generation_config_v2.json
    dataset_version: str = "stage2-v0.2-calibration"
    primary_feature_set_name: str = "C_state_dynamics"  # Section 2: "the primary AeroGuard feature set"
