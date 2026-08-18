"""Feature-set selection, leakage guards, and the common-subset mask.

Every function here only READS the already-computed processed table
(data/processed/processed_dataset_v2.parquet). dV_dt/dalpha_dt were
already verified causal (backward-difference, no future samples) during
Stage 2's dataset audit (aeroguard_dataset/audit.py:
verify_causal_derivatives, verify_future_labels) -- this module adds a
second, independent layer of guards specific to how the ML pipeline
consumes those columns, so a future change to a feature-set definition
can't silently reintroduce leakage.
"""

from typing import List, Tuple

import numpy as np
import pandas as pd

from . import config


class FeatureLeakageError(Exception):
    """Raised when a feature set includes a forbidden (future-derived or
    target-adjacent) column."""


def assert_feature_set_is_causal(feature_columns: List[str]) -> None:
    forbidden = set(feature_columns) & config.FORBIDDEN_FEATURE_COLUMNS
    if forbidden:
        raise FeatureLeakageError(f"Feature set includes forbidden column(s): {sorted(forbidden)}")
    # trajectory_id/time/split are identifiers, not physics features --
    # including them as model inputs would let a model key on trajectory
    # identity rather than physical state.
    identifier_leak = set(feature_columns) & {"trajectory_id", "time", "split"}
    if identifier_leak:
        raise FeatureLeakageError(f"Feature set includes identifier column(s), not a physics feature: {sorted(identifier_leak)}")


for _name, _cols in config.FEATURE_SETS.items():
    assert_feature_set_is_causal(_cols)


def target_available_mask(df: pd.DataFrame) -> pd.Series:
    """Rows where the supervised target itself is defined (Section 1:
    exclude NaN/unavailable labels from training/evaluation)."""
    return df[config.TARGET_AVAILABLE_COL].astype(bool)


def common_subset_mask(df: pd.DataFrame) -> pd.Series:
    """Section 5: the row population usable for a FAIR comparison across
    Feature Sets A/B/C -- target available AND every derivative feature
    (needed only by C, but held out for all three so they're compared
    on literally the same rows) is available."""
    mask = target_available_mask(df)
    for col in config.COMMON_SUBSET_REQUIRED_COLUMNS:
        mask = mask & df[col].notna()
    return mask


def get_xy(df: pd.DataFrame, feature_columns: List[str], require_common_subset: bool = True) -> Tuple[pd.DataFrame, np.ndarray]:
    """Extract (X, y) for the given feature set from an already-split
    DataFrame slice (e.g. dataset.split_df('train')).

    require_common_subset=True (the default, and what Section 5 calls
    for in the primary/ablation comparisons) restricts to
    common_subset_mask(df); pass False only for a feature-set-specific
    "how many extra rows would Model A get on its own" accounting
    computation, never for a cross-feature-set comparison.
    """
    assert_feature_set_is_causal(feature_columns)
    mask = common_subset_mask(df) if require_common_subset else target_available_mask(df)
    sub = df.loc[mask]
    X = sub[feature_columns].copy()
    y = sub[config.TARGET_COL].to_numpy().astype(int)
    if X.isna().any().any():
        bad_cols = X.columns[X.isna().any()].tolist()
        raise FeatureLeakageError(f"Unexpected NaN in feature columns after masking: {bad_cols}")
    return X, y
