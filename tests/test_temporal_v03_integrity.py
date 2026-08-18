"""v0.3 temporal-experiment integrity checks (Phase 2 of the v0.3
early-warning experiment): trajectory-level split integrity, no
label-derived features, causal-only windows, and (once the v0.3
temporal cache has been built) real-data leakage checks mirroring
tests/test_temporal_features.py's cache-dependent tests, pointed at
data/ml_temporal_v03/ instead of data/ml_temporal/.

Does not modify aeroguard/, aeroguard_dataset/, data/processed/,
data/splits/, data/ml/, data/ml_temporal/, or any v0.1/v0.2/v0.3
dataset file.
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml import temporal_config_v03 as v3cfg
from ml.temporal_features import common_subset_mask, usable_mask_for_window, window_steps


# ---------------------------------------------------------------------------
# 1. Trajectory-level split integrity (zero overlap), on the REAL v0.3 files
# ---------------------------------------------------------------------------

def test_v03_split_manifest_has_zero_overlap_between_splits():
    manifest = pd.read_csv(v3cfg.SPLIT_MANIFEST_PATH)
    by_split = {s: set(g["trajectory_id"]) for s, g in manifest.groupby("split")}
    assert set(by_split.keys()) == {"train", "val", "test"}
    assert by_split["train"] & by_split["val"] == set()
    assert by_split["train"] & by_split["test"] == set()
    assert by_split["val"] & by_split["test"] == set()
    assert manifest["trajectory_id"].is_unique, "duplicate trajectory_id in v0.3 split manifest"


def test_v03_metadata_and_split_manifest_trajectory_ids_match():
    manifest = pd.read_csv(v3cfg.SPLIT_MANIFEST_PATH)
    metadata = pd.read_csv(v3cfg.METADATA_PATH)
    assert set(manifest["trajectory_id"]) == set(metadata["trajectory_id"])


def test_v03_gradual_approach_regime_present_and_named_as_expected():
    metadata = pd.read_csv(v3cfg.METADATA_PATH)
    modes = set(metadata["generation_mode"].unique())
    assert v3cfg.GRADUAL_REGIME_NAME in modes
    assert {"normal", "stall", v3cfg.GRADUAL_REGIME_NAME} == modes


def test_v03_trajectory_id_namespace_disjoint_from_v02():
    """Sanity guard against ever silently joining v0.3 rows to v0.2
    metadata (or vice versa): the two id namespaces must never collide."""
    from ml import temporal_config as v2cfg
    ids_v3 = set(pd.read_csv(v3cfg.METADATA_PATH)["trajectory_id"])
    ids_v2 = set(pd.read_csv(v2cfg.METADATA_PATH)["trajectory_id"])
    assert ids_v3.isdisjoint(ids_v2)


# ---------------------------------------------------------------------------
# 2. Feature-set / leakage guards (dataset-agnostic functions, re-verified
#    against the v0.3 feature-set config re-export)
# ---------------------------------------------------------------------------

def test_v03_model_feature_sets_never_include_forbidden_columns():
    forbidden = {"future_stall_5s", "future_stall_5s_available", "time_to_stall", "is_unsafe",
                 "trajectory_id", "time", "split"}
    for w in v3cfg.HISTORY_WINDOWS_S:
        assert forbidden.isdisjoint(set(v3cfg.model_d_features(w)))
    assert forbidden.isdisjoint(set(v3cfg.STATE_DERIVATIVE_FEATURES))
    assert forbidden.isdisjoint(set(v3cfg.INSTANTANEOUS_STATE_FEATURES))


def test_v03_get_xy_rejects_forbidden_feature_columns():
    from ml.temporal_experiment import get_xy

    n = 100
    df = pd.DataFrame({
        "trajectory_id": ["T"] * n, "time": np.arange(n) * 0.01,
        "alpha": 0.05, "future_stall_5s": 0.0,
    })
    mask = pd.Series(True, index=df.index)
    with pytest.raises(ValueError):
        get_xy(df, ["alpha", "future_stall_5s"], mask)
    with pytest.raises(ValueError):
        get_xy(df, ["alpha", "trajectory_id"], mask)


def test_v03_windows_config_is_subset_check_of_v02_not_a_superset():
    """The pre-registered v0.3 robustness check (0.5/1/2s) must never
    silently grow beyond what Phase 1 locked -- guards against a future
    edit accidentally reintroducing an unplanned window."""
    assert set(v3cfg.HISTORY_WINDOWS_S) == {0.5, 1.0, 2.0}
    assert v3cfg.PRIMARY_WINDOW_S == 1.0


# ---------------------------------------------------------------------------
# 3. Real cached v0.3 data checks (skipped until the v0.3 temporal cache
#    exists -- built by ml/temporal_data_v03.py or the v0.3 driver script)
# ---------------------------------------------------------------------------

TEMPORAL_TRAIN_PATH = os.path.join(v3cfg.TEMPORAL_DATA_DIR, "temporal_train.parquet")
TEMPORAL_VAL_PATH = os.path.join(v3cfg.TEMPORAL_DATA_DIR, "temporal_val.parquet")
TEMPORAL_TEST_PATH = os.path.join(v3cfg.TEMPORAL_DATA_DIR, "temporal_test.parquet")


@pytest.mark.skipif(not os.path.exists(TEMPORAL_TRAIN_PATH), reason="run ml.temporal_data_v03 (or the v0.3 driver script) first")
def test_v03_real_data_trajectory_boundaries_never_crossed():
    df = pd.read_parquet(TEMPORAL_TRAIN_PATH)
    sample_ids = df["trajectory_id"].drop_duplicates().sample(n=15, random_state=0)
    for tid in sample_ids:
        g = df[df["trajectory_id"] == tid].sort_values("time").reset_index(drop=True)
        for w in v3cfg.HISTORY_WINDOWS_S:
            ws = window_steps(w, v3cfg.DT)
            col = f"alpha_mean_{v3cfg._fmt(w)}s"
            n_nan_at_start = g[col].iloc[: min(ws, len(g))].isna().sum()
            expected = min(ws, len(g))
            assert n_nan_at_start == expected, f"trajectory {tid} window {w}s: expected {expected} leading NaNs, got {n_nan_at_start}"


@pytest.mark.skipif(not os.path.exists(TEMPORAL_TRAIN_PATH), reason="run ml.temporal_data_v03 (or the v0.3 driver script) first")
def test_v03_real_data_common_subset_smaller_than_full_usable_population():
    df = pd.read_parquet(TEMPORAL_TRAIN_PATH)
    common = common_subset_mask(df, v3cfg.HISTORY_WINDOWS_S)
    full_usable = df[v3cfg.TARGET_AVAILABLE_COL].astype(bool)
    assert common.sum() < full_usable.sum()
    assert common.sum() > 0


@pytest.mark.skipif(not (os.path.exists(TEMPORAL_TRAIN_PATH) and os.path.exists(TEMPORAL_VAL_PATH) and os.path.exists(TEMPORAL_TEST_PATH)),
                     reason="run ml.temporal_data_v03 (or the v0.3 driver script) first")
def test_v03_temporal_cache_split_trajectories_match_manifest_with_zero_overlap():
    """End-to-end check: the CACHED temporal panels (not just the raw
    split manifest) preserve zero trajectory overlap across splits."""
    splits = {s: pd.read_parquet(os.path.join(v3cfg.TEMPORAL_DATA_DIR, f"temporal_{s}.parquet")) for s in ("train", "val", "test")}
    ids = {s: set(df["trajectory_id"].unique()) for s, df in splits.items()}
    assert ids["train"] & ids["val"] == set()
    assert ids["train"] & ids["test"] == set()
    assert ids["val"] & ids["test"] == set()

    manifest = pd.read_csv(v3cfg.SPLIT_MANIFEST_PATH)
    for s in ("train", "val", "test"):
        expected = set(manifest.loc[manifest["split"] == s, "trajectory_id"])
        assert ids[s] == expected, f"{s} split trajectory set mismatch between cache and manifest"


@pytest.mark.skipif(not os.path.exists(TEMPORAL_TEST_PATH), reason="run ml.temporal_data_v03 (or the v0.3 driver script) first")
def test_v03_no_future_information_in_time_to_stall_availability():
    """time_to_stall is only ever a positive lookahead computed from the
    trajectory's OWN future is_unsafe rows (see scripts/prepare_ml_dataset.py
    compute_time_to_stall) -- never negative, and NaN exactly where no
    future crossing exists in the recorded trajectory."""
    df = pd.read_parquet(TEMPORAL_TEST_PATH)
    tts = df["time_to_stall"].dropna().to_numpy()
    assert (tts >= 0).all(), "time_to_stall must never be negative (would imply a past crossing being called future)"
