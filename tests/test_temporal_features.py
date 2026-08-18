"""Tests for the Stage 4 temporal early-warning feature pipeline
(ml/temporal_features.py, ml/temporal_config.py, ml/temporal_data.py,
ml/temporal_experiment.py's leakage guard).

Mirrors tests/test_ml_dataset_prep.py's approach: small, fully
hand-checkable synthetic trajectories for causality/no-leakage proofs,
plus a few checks against the real cached data/ml_temporal/*.parquet
files (skipped if that cache hasn't been built yet). Does not modify
aeroguard/, aeroguard_dataset/, or any data/*_v2.*/data/ml/* file.
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml import temporal_config as tcfg
from ml.temporal_features import (
    build_temporal_panel,
    common_subset_mask,
    compute_endpoint_diff,
    compute_endpoint_rate,
    compute_ols_slope,
    compute_rolling_stat,
    compute_second_derivative,
    usable_mask_for_window,
    window_steps,
)

DT = 0.01


def _make_trajectory(trajectory_id, alpha, V=None, gamma=None, elevator=None, pitch_rate=None, dt=DT):
    n = len(alpha)
    t = np.arange(n) * dt
    alpha = np.asarray(alpha, dtype=float)
    V = np.full(n, 45.0) if V is None else np.asarray(V, dtype=float)
    gamma = np.zeros(n) if gamma is None else np.asarray(gamma, dtype=float)
    elevator = np.full(n, 0.01) if elevator is None else np.asarray(elevator, dtype=float)
    pitch_rate = np.zeros(n) if pitch_rate is None else np.asarray(pitch_rate, dtype=float)
    dalpha_dt = np.concatenate([[np.nan], np.diff(alpha) / dt]) if n > 1 else np.full(n, np.nan)
    return pd.DataFrame({
        "trajectory_id": trajectory_id, "time": t,
        "V": V, "alpha": alpha, "gamma": gamma, "pitch_rate": pitch_rate,
        "altitude": 1000.0, "elevator": elevator, "throttle": 0.4,
        "stall_margin": 0.28044009791924895 - alpha,
        "dV_dt": np.full(n, 0.0), "dalpha_dt": dalpha_dt,
        "dgamma_dt": np.full(n, 0.0), "dq_dt": np.full(n, 0.0),
        "future_stall_5s": 0.0, "future_stall_5s_available": True,
        "time_to_stall": np.nan, "is_unsafe": False,
    })


# ---------------------------------------------------------------------------
# 1. Window length / step-count correctness
# ---------------------------------------------------------------------------

def test_window_steps_basic():
    assert window_steps(0.5, 0.01) == 50
    assert window_steps(1.0, 0.01) == 100
    assert window_steps(2.0, 0.01) == 200
    assert window_steps(3.0, 0.01) == 300


# ---------------------------------------------------------------------------
# 2. Causal rolling mean/min/max match a manual (closed-window) computation
# ---------------------------------------------------------------------------

def test_rolling_stats_match_manual_window_and_are_causal():
    n = 500
    rng = np.random.default_rng(0)
    alpha = rng.normal(0.05, 0.02, n)
    df = _make_trajectory("T", alpha)

    mean_ = compute_rolling_stat(df, "trajectory_id", "alpha", 1.0, DT, "mean")
    min_ = compute_rolling_stat(df, "trajectory_id", "alpha", 1.0, DT, "min")
    max_ = compute_rolling_stat(df, "trajectory_id", "alpha", 1.0, DT, "max")
    ws = window_steps(1.0, DT)

    for row in [ws, ws + 1, ws + 100, n - 1]:
        window = alpha[row - ws: row + 1]  # closed window [t-W, t] -- must NOT include row+1 (future)
        assert np.isclose(mean_.iloc[row], window.mean())
        assert np.isclose(min_.iloc[row], window.min())
        assert np.isclose(max_.iloc[row], window.max())

    # insufficient history -> NaN, exactly the first `ws` rows
    assert mean_.iloc[:ws].isna().all()
    assert mean_.iloc[ws:].notna().all()


def test_rolling_stat_never_uses_future_sample():
    """Perturbing a single FUTURE sample must not change today's rolling
    statistic -- the sharpest possible test of 'no future telemetry'."""
    n = 300
    alpha = np.linspace(0, 1, n)
    df_a = _make_trajectory("T", alpha)
    alpha_perturbed = alpha.copy()
    alpha_perturbed[250] = 999.0  # a future row relative to row 200
    df_b = _make_trajectory("T", alpha_perturbed)

    mean_a = compute_rolling_stat(df_a, "trajectory_id", "alpha", 1.0, DT, "mean")
    mean_b = compute_rolling_stat(df_b, "trajectory_id", "alpha", 1.0, DT, "mean")
    assert mean_a.iloc[200] == pytest.approx(mean_b.iloc[200])
    assert not np.isclose(mean_a.iloc[251], mean_b.iloc[251])  # row 251's window DOES include row 250 -- sanity check the setup is meaningful


# ---------------------------------------------------------------------------
# 3. OLS slope: closed form matches np.polyfit, causal, correct NaN region
# ---------------------------------------------------------------------------

def test_ols_slope_matches_polyfit_and_recovers_known_ramp():
    n = 400
    dt = DT
    t = np.arange(n) * dt
    true_slope = -3.5
    alpha = true_slope * t + 0.1
    df = _make_trajectory("T", alpha, dt=dt)

    slope = compute_ols_slope(df, "trajectory_id", "alpha", 2.0, dt)
    ws = window_steps(2.0, dt)

    assert np.allclose(slope.iloc[ws:], true_slope, atol=1e-6)
    assert slope.iloc[:ws].isna().all()

    rng = np.random.default_rng(1)
    noisy_alpha = alpha + rng.normal(0, 1e-4, n)
    df_noisy = _make_trajectory("T", noisy_alpha, dt=dt)
    slope_noisy = compute_ols_slope(df_noisy, "trajectory_id", "alpha", 1.0, dt)
    ws1 = window_steps(1.0, dt)
    for row in [ws1, ws1 + 77, n - 1]:
        window_y = noisy_alpha[row - ws1: row + 1]
        window_x = np.arange(len(window_y)) * dt
        manual = np.polyfit(window_x, window_y, 1)[0]
        assert slope_noisy.iloc[row] == pytest.approx(manual, abs=1e-6)


# ---------------------------------------------------------------------------
# 4. Endpoint difference / rate
# ---------------------------------------------------------------------------

def test_endpoint_diff_and_rate():
    n = 300
    alpha = np.arange(n) * 0.001
    df = _make_trajectory("T", alpha)
    ws = window_steps(1.0, DT)

    diff = compute_endpoint_diff(df, "trajectory_id", "alpha", 1.0, DT)
    rate = compute_endpoint_rate(df, "trajectory_id", "alpha", 1.0, DT)

    row = 150
    expected_diff = alpha[row] - alpha[row - ws]
    assert diff.iloc[row] == pytest.approx(expected_diff)
    assert rate.iloc[row] == pytest.approx(expected_diff / 1.0)
    assert diff.iloc[:ws].isna().all()


# ---------------------------------------------------------------------------
# 5. Second derivative: NaN for first two rows, matches manual double-diff
# ---------------------------------------------------------------------------

def test_second_derivative_stability_and_causality():
    n = 200
    t = np.arange(n) * DT
    alpha = 0.5 * t ** 2  # constant second derivative = 1.0 exactly
    df = _make_trajectory("T", alpha)
    d2 = compute_second_derivative(df, "trajectory_id", "dalpha_dt", DT)
    assert np.isnan(d2.iloc[0]) and np.isnan(d2.iloc[1])
    assert np.allclose(d2.iloc[2:], 1.0, atol=1e-6)


# ---------------------------------------------------------------------------
# 6/7. No leakage across trajectory boundaries (window stats, slope, diff)
# ---------------------------------------------------------------------------

def test_no_leakage_across_trajectory_boundary_in_full_panel():
    n = 400
    a_alpha = np.linspace(0, 5, n)  # trajectory A ends at a very different alpha
    b_alpha = np.linspace(0, 0.01, n)  # trajectory B starts near 0

    combined = pd.concat([_make_trajectory("A", a_alpha), _make_trajectory("B", b_alpha)], ignore_index=True)
    panel = build_temporal_panel(combined, windows_s=[1.0])

    b_start = panel.index[panel["trajectory_id"] == "B"][0]
    ws = window_steps(1.0, DT)
    window_cols = tcfg.temporal_feature_columns(1.0)
    early_b_rows = panel.loc[b_start: b_start + ws - 1, window_cols]
    assert early_b_rows.isna().all().all(), "some temporal feature leaked across the A->B trajectory boundary"

    # once B has its own full window of history, values must be finite
    # and consistent with B's OWN data only (sanity: alpha_mean should
    # be close to B's own near-zero alpha range, nowhere near A's ~5.0 tail)
    later_row = b_start + ws + 5
    assert abs(panel.loc[later_row, "alpha_mean_1s"]) < 0.1


def test_naive_ungrouped_computation_would_leak_but_ours_does_not():
    """Deliberate leakage attack (mirrors
    test_ml_dataset_prep.py::test_naive_ungrouped_shift_would_leak):
    proves the naive whole-column version DOES leak at the boundary and
    our grouped implementation does not reproduce that leak."""
    n = 300
    a_alpha = np.linspace(0, 5, n)
    b_alpha = np.linspace(0, 0.01, n)
    combined = pd.concat([_make_trajectory("A", a_alpha), _make_trajectory("B", b_alpha)], ignore_index=True)
    ws = window_steps(1.0, DT)

    naive_lagged = combined["alpha"].shift(ws)  # THE BUG: no groupby
    naive_diff = combined["alpha"] - naive_lagged

    correct_diff = compute_endpoint_diff(combined, "trajectory_id", "alpha", 1.0, DT)

    b_start = combined.index[combined["trajectory_id"] == "B"][0]
    check_idx = b_start + 5
    assert not np.isnan(naive_diff.iloc[check_idx]), "test setup error: naive version should be (wrongly) non-NaN here"
    assert np.isnan(correct_diff.iloc[check_idx]), "LEAKAGE: endpoint difference used a different trajectory's data"


# ---------------------------------------------------------------------------
# 8. Insufficient-history rows handled correctly (exact boundary, no off-by-one)
# ---------------------------------------------------------------------------

def test_insufficient_history_boundary_is_exact():
    n = 250
    alpha = np.arange(n) * 0.002
    df = _make_trajectory("T", alpha)
    panel = build_temporal_panel(df, windows_s=[0.5, 1.0])

    for w, tag in [(0.5, "0.5"), (1.0, "1")]:
        ws = window_steps(w, DT)
        col = f"alpha_mean_{tag}s"
        assert panel[col].iloc[:ws].isna().all(), f"{col}: rows before full history should be NaN"
        assert panel[col].iloc[ws:].notna().all(), f"{col}: rows with full history should NOT be NaN"


# ---------------------------------------------------------------------------
# 9. Deterministic feature construction
# ---------------------------------------------------------------------------

def test_build_temporal_panel_is_deterministic():
    n = 300
    rng = np.random.default_rng(2)
    alpha = rng.normal(0.05, 0.02, n)
    df = _make_trajectory("T", alpha)
    p1 = build_temporal_panel(df, windows_s=[0.5, 1.0])
    p2 = build_temporal_panel(df, windows_s=[0.5, 1.0])
    pd.testing.assert_frame_equal(p1, p2)


def test_build_temporal_panel_row_order_independent_of_input_order():
    """Feeding the same rows in a shuffled order must produce identical
    per-row results after the function's own internal sort."""
    n = 300
    rng = np.random.default_rng(3)
    alpha = rng.normal(0.05, 0.02, n)
    df = _make_trajectory("T", alpha)
    shuffled = df.sample(frac=1.0, random_state=7).reset_index(drop=True)

    p1 = build_temporal_panel(df, windows_s=[1.0]).sort_values("time").reset_index(drop=True)
    p2 = build_temporal_panel(shuffled, windows_s=[1.0]).sort_values("time").reset_index(drop=True)
    pd.testing.assert_series_equal(p1["alpha_mean_1s"], p2["alpha_mean_1s"])


# ---------------------------------------------------------------------------
# 10. Row-population masks: correct nesting, target-availability guard
# ---------------------------------------------------------------------------

def test_common_subset_is_subset_of_every_individual_window_mask():
    n = 500
    rng = np.random.default_rng(4)
    alpha = rng.normal(0.05, 0.02, n)
    df = _make_trajectory("T", alpha)
    panel = build_temporal_panel(df, windows_s=tcfg.HISTORY_WINDOWS_S)

    common = common_subset_mask(panel)
    for w in tcfg.HISTORY_WINDOWS_S:
        individual = usable_mask_for_window(panel, w)
        assert (common & ~individual).sum() == 0, f"common subset includes rows not usable for window {w}s"
    assert common.sum() <= usable_mask_for_window(panel, min(tcfg.HISTORY_WINDOWS_S)).sum()


def test_common_subset_equals_largest_window_mask():
    n = 500
    rng = np.random.default_rng(5)
    alpha = rng.normal(0.05, 0.02, n)
    df = _make_trajectory("T", alpha)
    panel = build_temporal_panel(df, windows_s=tcfg.HISTORY_WINDOWS_S)
    common = common_subset_mask(panel)
    largest = usable_mask_for_window(panel, max(tcfg.HISTORY_WINDOWS_S))
    assert (common == largest).all()


def test_usable_mask_excludes_target_unavailable_rows():
    n = 200
    alpha = np.full(n, 0.05)
    df = _make_trajectory("T", alpha)
    df.loc[190:, "future_stall_5s_available"] = False
    panel = build_temporal_panel(df, windows_s=[0.5])
    mask = usable_mask_for_window(panel, 0.5)
    assert not mask.iloc[190:].any()


# ---------------------------------------------------------------------------
# 11. No accidental use of future_stall_5s (or other forbidden columns) as an input
# ---------------------------------------------------------------------------

def test_model_feature_sets_never_include_forbidden_columns():
    forbidden = {"future_stall_5s", "future_stall_5s_available", "time_to_stall", "is_unsafe",
                 "trajectory_id", "time", "split"}
    for w in tcfg.HISTORY_WINDOWS_S:
        assert forbidden.isdisjoint(set(tcfg.model_c_features(w)))
        assert forbidden.isdisjoint(set(tcfg.model_d_features(w)))
    assert forbidden.isdisjoint(set(tcfg.STATE_DERIVATIVE_FEATURES))
    assert forbidden.isdisjoint(set(tcfg.INSTANTANEOUS_STATE_FEATURES))


def test_get_xy_rejects_forbidden_feature_columns():
    from ml.temporal_experiment import get_xy

    n = 100
    df = _make_trajectory("T", np.full(n, 0.05))
    df["future_stall_5s"] = 0.0
    mask = pd.Series(True, index=df.index)
    with pytest.raises(ValueError):
        get_xy(df, ["alpha", "future_stall_5s"], mask)
    with pytest.raises(ValueError):
        get_xy(df, ["alpha", "time_to_stall"], mask)
    with pytest.raises(ValueError):
        get_xy(df, ["alpha", "trajectory_id"], mask)


# ---------------------------------------------------------------------------
# 12. alpha & stall_margin redundancy: window stats computed for alpha only
# ---------------------------------------------------------------------------

def test_window_features_computed_for_alpha_not_stall_margin():
    for w in tcfg.HISTORY_WINDOWS_S:
        cols = tcfg.temporal_feature_columns(w)
        assert not any("stall_margin" in c for c in cols), (
            "stall_margin is an exact algebraic transform of alpha; a separate window-stat "
            "panel for it would just relabel the same information"
        )
        assert any(c.startswith("alpha_") for c in cols)


# ---------------------------------------------------------------------------
# 13. Label alignment: future_stall_5s and time_to_stall are untouched
#     passthrough columns, never recomputed or shifted by this module
# ---------------------------------------------------------------------------

def test_labels_pass_through_unchanged():
    n = 200
    alpha = np.full(n, 0.05)
    df = _make_trajectory("T", alpha)
    df["future_stall_5s"] = np.arange(n) % 2  # arbitrary marker pattern
    panel = build_temporal_panel(df, windows_s=[0.5])
    assert (panel["future_stall_5s"].to_numpy() == df["future_stall_5s"].to_numpy()).all()


# ---------------------------------------------------------------------------
# 14. Real cached data checks (skipped if the cache hasn't been built)
# ---------------------------------------------------------------------------

TEMPORAL_TRAIN_PATH = os.path.join(tcfg.TEMPORAL_DATA_DIR, "temporal_train.parquet")


@pytest.mark.skipif(not os.path.exists(TEMPORAL_TRAIN_PATH), reason="run scripts/run_temporal_experiment.py (or ml.temporal_data) first")
def test_recomputed_alpha_trend_matches_original_ml_v2_columns():
    """alpha_trend_1s/2s/3s recomputed by this module must EXACTLY match
    the already-validated columns already shipped in ml_train_v2.parquet
    -- an end-to-end consistency check between Stage 3 and Stage 4.

    ml_train_v2.parquet is already restricted to Stage 3's "usable"
    rows (a strict subset of this module's temporal_train.parquet,
    which is built from every row of the full processed table, row 0
    of each trajectory included -- see ml/temporal_data.py's module
    docstring), so the two tables are aligned by (trajectory_id, time)
    rather than assumed to be the same length/order.
    """
    orig = pd.read_parquet(os.path.join(tcfg.ML_V2_DIR, "ml_train_v2.parquet"))
    temporal = pd.read_parquet(TEMPORAL_TRAIN_PATH)
    merged = orig[["trajectory_id", "time", "alpha_trend_1s", "alpha_trend_2s", "alpha_trend_3s"]].merge(
        temporal[["trajectory_id", "time", "alpha_trend_1s", "alpha_trend_2s", "alpha_trend_3s"]],
        on=["trajectory_id", "time"], suffixes=("_orig", "_temporal"), how="left",
    )
    assert len(merged) == len(orig), "every ml_train_v2 row should have a matching row in temporal_train.parquet"
    for c in ["alpha_trend_1s", "alpha_trend_2s", "alpha_trend_3s"]:
        assert np.allclose(merged[f"{c}_orig"].to_numpy(), merged[f"{c}_temporal"].to_numpy(), equal_nan=True, atol=1e-10)


@pytest.mark.skipif(not os.path.exists(TEMPORAL_TRAIN_PATH), reason="run scripts/run_temporal_experiment.py (or ml.temporal_data) first")
def test_real_data_trajectory_boundaries_never_crossed():
    """For every window, the number of NaN rows per trajectory at the
    START of that trajectory must be exactly window_steps (never fewer
    -- which would indicate a leak from the previous trajectory in
    sorted order -- and never more)."""
    df = pd.read_parquet(TEMPORAL_TRAIN_PATH)
    sample_ids = df["trajectory_id"].drop_duplicates().sample(n=15, random_state=0)
    for tid in sample_ids:
        g = df[df["trajectory_id"] == tid].sort_values("time").reset_index(drop=True)
        for w in tcfg.HISTORY_WINDOWS_S:
            ws = window_steps(w, tcfg.DT)
            col = f"alpha_mean_{tcfg._fmt(w)}s"
            n_nan_at_start = g[col].iloc[: min(ws, len(g))].isna().sum()
            expected = min(ws, len(g))
            assert n_nan_at_start == expected, f"trajectory {tid} window {w}s: expected {expected} leading NaNs, got {n_nan_at_start}"


@pytest.mark.skipif(not os.path.exists(TEMPORAL_TRAIN_PATH), reason="run scripts/run_temporal_experiment.py (or ml.temporal_data) first")
def test_real_data_common_subset_smaller_than_full_usable_population():
    df = pd.read_parquet(TEMPORAL_TRAIN_PATH)
    common = common_subset_mask(df)
    full_usable = df[tcfg.TARGET_AVAILABLE_COL].astype(bool)
    assert common.sum() < full_usable.sum(), "the common (largest-window) subset should be strictly smaller than the full usable population"
    assert common.sum() > 0
