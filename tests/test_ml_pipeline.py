"""Tests for the Stage 3 ML pipeline (ml/).

Uses the real frozen Dataset v0.2 for loading/integrity tests (it's
already generated and fast to read), but keeps any model-fitting tests
on small subsamples for speed. Does not modify aeroguard/,
aeroguard_dataset/, or any data/*_v2.* file.
"""

import inspect
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml import config
from ml.baselines import AoAThresholdRule, TrendRule
from ml.calibration import select_threshold_train_then_val
from ml.data import SplitIntegrityError, load_dataset, verify_split_integrity
from ml.events import (
    aggregate_event_results,
    compute_event_level_results,
    compute_false_alarm_stats,
    compute_lead_times_for_trajectory,
    group_boolean_into_episodes,
)
from ml.features import FeatureLeakageError, assert_feature_set_is_causal, common_subset_mask, get_xy, target_available_mask
from ml.models import build_logistic_regression


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dataset():
    return load_dataset()


def test_load_dataset_basic(dataset):
    assert len(dataset.processed) > 0
    for col in ["trajectory_id", "time", "alpha", config.TARGET_COL, config.TARGET_AVAILABLE_COL, "split"]:
        assert col in dataset.processed.columns
    assert set(dataset.processed["split"].unique()) == {"train", "val", "test"}


def test_dataset_version_matches_frozen_v2(dataset):
    assert dataset.generation_config["dataset_version"] == "stage2-v0.2-calibration"


# ---------------------------------------------------------------------------
# Train/validation/test separation (Section 4)
# ---------------------------------------------------------------------------

def test_train_val_test_separation(dataset):
    train_ids = dataset.trajectory_ids("train")
    val_ids = dataset.trajectory_ids("val")
    test_ids = dataset.trajectory_ids("test")
    assert len(train_ids & val_ids) == 0
    assert len(train_ids & test_ids) == 0
    assert len(val_ids & test_ids) == 0
    assert len(train_ids) == 700 and len(val_ids) == 150 and len(test_ids) == 150


def test_verify_split_integrity_raises_on_overlap():
    bad_manifest = pd.DataFrame({
        "trajectory_id": ["a", "b", "c"],
        "split": ["train", "train", "train"],
    })
    # duplicate id across two rows in different splits
    bad_manifest = pd.concat([bad_manifest, pd.DataFrame({"trajectory_id": ["a"], "split": ["test"]})], ignore_index=True)
    with pytest.raises(SplitIntegrityError):
        verify_split_integrity(bad_manifest)


def test_verify_split_integrity_passes_on_clean_manifest():
    manifest = pd.DataFrame({"trajectory_id": ["a", "b", "c", "d"], "split": ["train", "train", "val", "test"]})
    verify_split_integrity(manifest)  # must not raise


# ---------------------------------------------------------------------------
# Feature selection / no future features (Section 2/3)
# ---------------------------------------------------------------------------

def test_feature_set_definitions():
    assert config.FEATURE_SET_A == ["alpha"]
    assert set(config.FEATURE_SET_C) - set(config.FEATURE_SET_B) == {"dV_dt", "dalpha_dt"}
    assert "dV_dt" not in config.FEATURE_SET_B
    assert "dalpha_dt" not in config.FEATURE_SET_B


def test_no_future_features_in_any_feature_set():
    for name, cols in config.FEATURE_SETS.items():
        assert_feature_set_is_causal(cols)  # must not raise


def test_forbidden_columns_are_rejected():
    with pytest.raises(FeatureLeakageError):
        assert_feature_set_is_causal(["alpha", config.TARGET_COL])
    with pytest.raises(FeatureLeakageError):
        assert_feature_set_is_causal(["alpha", "is_unsafe"])
    with pytest.raises(FeatureLeakageError):
        assert_feature_set_is_causal(["alpha", "trajectory_id"])


def test_get_xy_matches_requested_feature_columns(dataset):
    train_df = dataset.split_df("train").head(5000)
    # Ensure at least some rows have available derivatives by using full train instead if head is too small
    train_df = dataset.split_df("train")
    X, y = get_xy(train_df, config.FEATURE_SET_B)
    assert list(X.columns) == config.FEATURE_SET_B
    assert "dV_dt" not in X.columns and "dalpha_dt" not in X.columns


# ---------------------------------------------------------------------------
# NaN / target handling (Section 1, 5)
# ---------------------------------------------------------------------------

def test_target_available_mask_excludes_nan(dataset):
    train_df = dataset.split_df("train")
    mask = target_available_mask(train_df)
    y_available = train_df.loc[mask, config.TARGET_COL]
    assert not y_available.isna().any()
    assert set(y_available.unique()) <= {0.0, 1.0}


def test_common_subset_excludes_first_row_derivative_nans(dataset):
    train_df = dataset.split_df("train")
    mask = common_subset_mask(train_df)
    sub = train_df.loc[mask]
    assert not sub["dV_dt"].isna().any()
    assert not sub["dalpha_dt"].isna().any()
    assert mask.sum() <= target_available_mask(train_df).sum()


def test_get_xy_never_returns_nan_features_or_targets(dataset):
    train_df = dataset.split_df("train")
    X, y = get_xy(train_df, config.FEATURE_SET_C)
    assert not X.isna().any().any()
    assert not np.isnan(y).any()
    assert set(np.unique(y)) <= {0, 1}


# ---------------------------------------------------------------------------
# Causal feature verification (Section 3)
# ---------------------------------------------------------------------------

def test_derivatives_are_causal_backward_difference(dataset):
    """Recompute dV_dt/dalpha_dt independently from raw V/alpha for one
    trajectory and confirm they match the stored (already Stage-2-
    audited) values -- i.e. row i's derivative uses only rows <= i."""
    train_df = dataset.split_df("train")
    tid = train_df["trajectory_id"].iloc[0]
    g = train_df[train_df["trajectory_id"] == tid].sort_values("time").reset_index(drop=True)
    dt = config.LABELING_HORIZON_S and 0.01  # matches generation_config_v2.json

    expected_dV = np.full(len(g), np.nan)
    expected_dV[1:] = (g["V"].to_numpy()[1:] - g["V"].to_numpy()[:-1]) / dt
    assert np.allclose(expected_dV, g["dV_dt"].to_numpy(), equal_nan=True, atol=1e-8)

    expected_dalpha = np.full(len(g), np.nan)
    expected_dalpha[1:] = (g["alpha"].to_numpy()[1:] - g["alpha"].to_numpy()[:-1]) / dt
    assert np.allclose(expected_dalpha, g["dalpha_dt"].to_numpy(), equal_nan=True, atol=1e-8)


# ---------------------------------------------------------------------------
# Deterministic training
# ---------------------------------------------------------------------------

def test_logistic_regression_is_deterministic(dataset):
    train_df = dataset.split_df("train")
    X, y = get_xy(train_df, config.FEATURE_SET_A)
    rng = np.random.default_rng(0)
    idx = rng.choice(len(X), size=5000, replace=False)
    Xs, ys = X.iloc[idx], y[idx]

    m1 = build_logistic_regression(C=1.0, class_weight="balanced").fit(Xs, ys)
    m2 = build_logistic_regression(C=1.0, class_weight="balanced").fit(Xs, ys)
    p1 = m1.predict_proba(Xs)[:, 1]
    p2 = m2.predict_proba(Xs)[:, 1]
    assert np.allclose(p1, p2)


# ---------------------------------------------------------------------------
# Threshold calibration never touches TEST
# ---------------------------------------------------------------------------

def test_calibration_functions_do_not_accept_test_arguments():
    """Structural guard: the calibration APIs literally have no
    parameter that could carry a TEST set in."""
    for fn in [AoAThresholdRule.fit, TrendRule.fit, select_threshold_train_then_val]:
        params = list(inspect.signature(fn).parameters)
        assert not any("test" in p.lower() for p in params), f"{fn} has a suspicious test-like parameter: {params}"


def test_threshold_calibration_deterministic_given_train_val():
    rng = np.random.default_rng(1)
    y_train = rng.integers(0, 2, size=2000)
    score_train = rng.random(2000) + y_train * 0.5
    y_val = rng.integers(0, 2, size=500)
    score_val = rng.random(500) + y_val * 0.5

    t1, info1 = select_threshold_train_then_val(y_train, score_train, y_val, score_val)
    t2, info2 = select_threshold_train_then_val(y_train, score_train, y_val, score_val)
    assert t1 == t2
    assert info1 == info2


# ---------------------------------------------------------------------------
# Warning-episode grouping (Section 15)
# ---------------------------------------------------------------------------

def test_group_boolean_into_episodes_basic():
    times = np.arange(10, dtype=float)
    flags = np.array([0, 0, 1, 1, 1, 0, 0, 1, 0, 0], dtype=bool)
    episodes = group_boolean_into_episodes(times, flags)
    assert episodes == [(2.0, 4.0, 2, 4), (7.0, 7.0, 7, 7)]


def test_group_boolean_into_episodes_edges():
    times = np.arange(5, dtype=float)
    # starts True, ends True
    flags = np.array([1, 1, 0, 1, 1], dtype=bool)
    episodes = group_boolean_into_episodes(times, flags)
    assert episodes == [(0.0, 1.0, 0, 1), (3.0, 4.0, 3, 4)]

    # all False -> no episodes
    assert group_boolean_into_episodes(times, np.zeros(5, dtype=bool)) == []

    # all True -> one episode covering everything
    assert group_boolean_into_episodes(times, np.ones(5, dtype=bool)) == [(0.0, 4.0, 0, 4)]

    # empty input
    assert group_boolean_into_episodes(np.array([]), np.array([], dtype=bool)) == []


# ---------------------------------------------------------------------------
# Event-level lead-time calculation (Section 14)
# ---------------------------------------------------------------------------

def test_event_level_lead_time_normal_case():
    times = np.arange(11, dtype=float)
    is_unsafe = np.array([0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0], dtype=bool)
    pred = np.array([0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0], dtype=bool)
    results = compute_lead_times_for_trajectory("t", times, is_unsafe, times, pred, horizon_s=5.0)
    assert len(results) == 1
    assert results[0].warned
    assert results[0].crossing_time == 6.0
    assert results[0].lead_time_s == pytest.approx(4.0)


def test_event_level_lead_time_is_capped_at_horizon():
    times = np.arange(11, dtype=float)
    is_unsafe = np.array([0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0], dtype=bool)
    pred = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=bool)  # warning starts at t=0, well before the 5s horizon
    results = compute_lead_times_for_trajectory("t", times, is_unsafe, times, pred, horizon_s=5.0)
    assert results[0].warned
    assert results[0].lead_time_s == pytest.approx(5.0)  # capped, not 6.0


def test_event_level_missed_event_when_no_prior_warning():
    times = np.arange(11, dtype=float)
    is_unsafe = np.array([0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0], dtype=bool)
    pred = np.zeros(11, dtype=bool)
    results = compute_lead_times_for_trajectory("t", times, is_unsafe, times, pred, horizon_s=5.0)
    assert not results[0].warned
    assert results[0].lead_time_s is None


def test_event_level_warning_after_crossing_does_not_count():
    times = np.arange(11, dtype=float)
    is_unsafe = np.array([0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0], dtype=bool)
    pred = np.array([0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0], dtype=bool)  # warning only after the crossing
    results = compute_lead_times_for_trajectory("t", times, is_unsafe, times, pred, horizon_s=5.0)
    assert not results[0].warned  # a post-crossing "warning" must not count as a successful early warning


def test_aggregate_event_results_summary():
    times = np.arange(11, dtype=float)
    is_unsafe = np.array([0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0], dtype=bool)
    pred_good = np.array([0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0], dtype=bool)
    pred_none = np.zeros(11, dtype=bool)
    results = (
        compute_lead_times_for_trajectory("t1", times, is_unsafe, times, pred_good, horizon_s=5.0)
        + compute_lead_times_for_trajectory("t2", times, is_unsafe, times, pred_none, horizon_s=5.0)
    )
    agg = aggregate_event_results(results)
    assert agg["n_events"] == 2
    assert agg["n_warned"] == 1
    assert agg["n_missed"] == 1
    assert agg["event_recall"] == pytest.approx(0.5)
    assert agg["median_lead_time_s"] == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# False-alarm calculation (Section 15)
# ---------------------------------------------------------------------------

def test_false_alarm_calculation_basic():
    df = pd.DataFrame({
        "trajectory_id": ["a"] * 6,
        "time": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
        "future_stall_5s": [1.0, np.nan, 0.0, np.nan, np.nan, np.nan],
    })
    # two separate warning episodes: index 0 (true), index 2 (false)
    pred = np.array([1, 0, 1, 0, 0, 0], dtype=bool)
    stats = compute_false_alarm_stats(df, pred, n_test_trajectories=1)
    assert stats["n_warning_episodes"] == 2
    assert stats["n_true_warning_episodes"] == 1
    assert stats["n_false_alarm_episodes"] == 1
    assert stats["n_undetermined_episodes"] == 0
    assert stats["false_warning_rate"] == pytest.approx(0.5)
    assert stats["warnings_per_trajectory"] == pytest.approx(2.0)


def test_false_alarm_calculation_excludes_undetermined():
    df = pd.DataFrame({
        "trajectory_id": ["a"] * 3,
        "time": [0.0, 1.0, 2.0],
        "future_stall_5s": [np.nan, 0.0, 0.0],
    })
    pred = np.array([1, 0, 0], dtype=bool)  # the one episode's start row has an undetermined label
    stats = compute_false_alarm_stats(df, pred, n_test_trajectories=1)
    assert stats["n_warning_episodes"] == 1
    assert stats["n_undetermined_episodes"] == 1
    assert stats["n_true_warning_episodes"] == 0
    assert stats["n_false_alarm_episodes"] == 0
    assert np.isnan(stats["false_warning_rate"])  # 0/0, correctly undefined rather than fabricated
