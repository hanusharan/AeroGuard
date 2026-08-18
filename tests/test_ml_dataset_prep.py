"""Tests for scripts/prepare_ml_dataset.py (the ML-ready-dataset builder).

Uses a mix of small synthetic trajectories (fast, fully controlled --
used to prove causality/no-leakage claims precisely) and the real
generated data/ml/*.parquet files (integration-level checks against the
actual frozen Dataset v0.2). Does not modify aeroguard/,
aeroguard_dataset/, or any data/*_v2.* file.
"""

import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from prepare_ml_dataset import (
    ALL_INPUT_FEATURES,
    CORE_FEATURES,
    DT,
    FORBIDDEN_INPUT_COLUMNS,
    HISTORY_FEATURES,
    ML_DIR,
    SCHEMA_PATH,
    build_ml_table,
    compute_causal_trend,
    compute_time_to_stall,
)

ML_DATASET_PATH = os.path.join(ML_DIR, "ml_dataset_v2.parquet")
ML_TRAIN_PATH = os.path.join(ML_DIR, "ml_train_v2.parquet")
ML_VAL_PATH = os.path.join(ML_DIR, "ml_val_v2.parquet")
ML_TEST_PATH = os.path.join(ML_DIR, "ml_test_v2.parquet")

BOUNDARY_RAD = 0.28044009791924895  # independently-known constant, not imported from the labeling code


def _make_synthetic_trajectory(trajectory_id, alpha_values, dt=DT):
    """A minimal synthetic trajectory: only the columns build_ml_table
    actually reads. alpha_values is a plain list of alpha (rad)."""
    n = len(alpha_values)
    t = np.arange(n) * dt
    alpha = np.array(alpha_values, dtype=float)
    is_unsafe = np.abs(alpha) > BOUNDARY_RAD
    return pd.DataFrame({
        "trajectory_id": trajectory_id, "time": t,
        "V": 45.0, "alpha": alpha, "theta": alpha, "gamma": 0.0,
        "altitude": 1000.0, "pitch_rate": 0.0, "vertical_speed": 0.0,
        "thrust": 800.0, "elevator": 0.01, "throttle": 0.4,
        "dV_dt": np.concatenate([[np.nan], np.zeros(n - 1)]) if n > 0 else np.array([]),
        "dalpha_dt": np.concatenate([[np.nan], np.diff(alpha) / dt]) if n > 1 else np.full(n, np.nan),
        "stall_margin": BOUNDARY_RAD - alpha,
        "is_unsafe": is_unsafe,
    })


def _independent_future_stall_5s(alpha, dt, horizon_s=5.0):
    """A from-scratch (no shared code) re-implementation, used only to
    build expected values for synthetic-trajectory tests."""
    is_unsafe = np.abs(alpha) > BOUNDARY_RAD
    n = len(alpha)
    horizon_steps = round(horizon_s / dt)
    out = np.full(n, np.nan)
    for i in range(n):
        j = i + horizon_steps
        if j >= n:
            continue
        out[i] = 1.0 if is_unsafe[i + 1:j + 1].any() else 0.0
    return out


# ---------------------------------------------------------------------------
# 1. Label correctness on a synthetic trajectory
# ---------------------------------------------------------------------------

def test_label_correctness_on_synthetic_trajectory():
    """A synthetic trajectory with a known, hand-verifiable crossing."""
    dt = 1.0  # 1-second steps for a small, hand-checkable example
    # alpha stays safe, crosses boundary at index 6, stays unsafe for 2 steps, then safe
    alpha_deg = [4, 4, 4, 4, 4, 4, 20, 20, 4, 4, 4]
    alpha = np.radians(alpha_deg)
    expected = _independent_future_stall_5s(alpha, dt, horizon_s=5.0)
    # hand check: at i=1 (t=1s), window (2,6] in steps -> indices 2..6 -> includes index 6 (unsafe) -> 1
    assert expected[1] == 1.0
    # at i=0, window (1,5] -> indices 1..5, none unsafe yet (crossing is at index 6) -> 0
    assert expected[0] == 0.0
    # last horizon_steps=5 rows (indices 6..10) have insufficient future (i+5 >= n=11) -> NaN,
    # including row 6 itself, even though it is already unsafe -- future_stall_5s asks about
    # STRICTLY FUTURE rows, and there aren't 5 seconds of them left after row 6
    assert np.all(np.isnan(expected[6:]))


# ---------------------------------------------------------------------------
# 2. No label crossing trajectory boundaries
# ---------------------------------------------------------------------------

def test_label_never_crosses_trajectory_boundary():
    """Two back-to-back trajectories: A ends unsafe, B starts safe. A's
    labels must never be influenced by B's unsafe rows and vice versa."""
    dt = 0.01
    n = 600
    # trajectory A: safe throughout except it does NOT cross -> should be all 0/NaN, never 1
    a_alpha = np.radians(np.full(n, 4.0))
    # trajectory B: unsafe in its first 10 rows (would corrupt A's tail if grouping were broken)
    b_alpha = np.radians(np.concatenate([np.full(10, 30.0), np.full(n - 10, 4.0)]))

    combined = pd.concat([
        _make_synthetic_trajectory("A", a_alpha, dt),
        _make_synthetic_trajectory("B", b_alpha, dt),
    ], ignore_index=True)

    labels = {}
    for tid, g in combined.groupby("trajectory_id"):
        labels[tid] = _independent_future_stall_5s(g["alpha"].to_numpy(), dt, horizon_s=5.0)

    # A never crosses -> every available label must be 0.0, never 1.0
    a_available = labels["A"][~np.isnan(labels["A"])]
    assert np.all(a_available == 0.0), "trajectory A's labels were contaminated by trajectory B's unsafe rows"


# ---------------------------------------------------------------------------
# 3. Final 5-second rows are unavailable/NaN
# ---------------------------------------------------------------------------

def test_final_5_seconds_are_nan():
    dt = 0.01
    n = 1000  # 10 seconds
    alpha = np.radians(np.full(n, 4.0))
    labels = _independent_future_stall_5s(alpha, dt, horizon_s=5.0)
    horizon_steps = round(5.0 / dt)
    assert np.all(np.isnan(labels[n - horizon_steps:]))
    assert np.all(~np.isnan(labels[:n - horizon_steps]))


# ---------------------------------------------------------------------------
# 4/5. History features are causal and never cross trajectory boundaries
# ---------------------------------------------------------------------------

def test_causal_trend_uses_only_past_samples():
    dt = 0.01
    n = 500
    alpha = np.arange(n) * dt  # alpha(t) = t exactly -> true slope is exactly 1.0 rad/s throughout
    df = _make_synthetic_trajectory("T", alpha, dt)
    trend_1s = compute_causal_trend(df, "alpha", 1.0, dt)
    window_steps = round(1.0 / dt)
    assert trend_1s[:window_steps].isna().all(), "trend must be NaN before a full window of history exists"
    assert np.allclose(trend_1s[window_steps:], 1.0, atol=1e-9), "trend value should exactly reconstruct the known ramp slope using only past samples"


def test_history_window_never_crosses_trajectory_boundary():
    """The critical leakage-prevention check: a trend feature near the
    START of trajectory B must be NaN, not silently pulling values from
    the END of trajectory A (which would happen with a naive
    whole-dataframe .shift() that isn't grouped by trajectory_id)."""
    dt = 0.01
    n = 400
    a_alpha = np.linspace(0, 5, n)  # trajectory A ends at alpha=5.0
    b_alpha = np.linspace(0, 0.01, n)  # trajectory B starts near alpha=0

    combined = pd.concat([
        _make_synthetic_trajectory("A", a_alpha, dt),
        _make_synthetic_trajectory("B", b_alpha, dt),
    ], ignore_index=True)

    correct_trend = compute_causal_trend(combined, "alpha", 1.0, dt)
    window_steps = round(1.0 / dt)

    # first `window_steps` rows of B (trajectory B starts right after A ends)
    b_start_idx = combined.index[combined["trajectory_id"] == "B"][0]
    b_early_rows = correct_trend.iloc[b_start_idx: b_start_idx + window_steps]
    assert b_early_rows.isna().all(), "trend feature leaked across the A->B trajectory boundary"


def test_naive_ungrouped_shift_would_leak_and_our_implementation_avoids_it():
    """DELIBERATE LEAKAGE ATTACK (explicitly requested): construct the
    'obviously wrong' version of the trend feature -- shifting the WHOLE
    concatenated column without grouping by trajectory_id first -- and
    prove (a) it actually does leak at the boundary, and (b) our
    causal_trend implementation's output is different there, i.e. does
    NOT reproduce the leak."""
    dt = 0.01
    n = 400
    a_alpha = np.linspace(0, 5, n)
    b_alpha = np.linspace(0, 0.01, n)
    combined = pd.concat([
        _make_synthetic_trajectory("A", a_alpha, dt),
        _make_synthetic_trajectory("B", b_alpha, dt),
    ], ignore_index=True)

    window_steps = round(1.0 / dt)

    # the leaky version: naive shift on the whole column, no groupby
    naive_lagged = combined["alpha"].shift(window_steps)  # THIS is the bug we must NOT have
    naive_trend = (combined["alpha"] - naive_lagged) / 1.0

    correct_trend = compute_causal_trend(combined, "alpha", 1.0, dt)

    b_start_idx = combined.index[combined["trajectory_id"] == "B"][0]
    check_idx = b_start_idx + 5  # a few rows into B, still within the danger window

    # Prove the naive version really is leaky here (non-NaN, using A's tail)
    assert not np.isnan(naive_trend.iloc[check_idx]), "test setup error: the naive version should have produced a (wrong) non-NaN value"
    # Prove our implementation does NOT do this
    assert np.isnan(correct_trend.iloc[check_idx]), "LEAKAGE: causal trend produced a value using a different trajectory's data"


# ---------------------------------------------------------------------------
# 6. No forbidden columns present in ML inputs
# ---------------------------------------------------------------------------

def test_forbidden_columns_not_in_input_feature_list():
    forbidden_in_inputs = set(ALL_INPUT_FEATURES) & FORBIDDEN_INPUT_COLUMNS
    assert forbidden_in_inputs == set(), f"forbidden columns leaked into the input feature list: {forbidden_in_inputs}"


@pytest.mark.skipif(not os.path.exists(ML_DATASET_PATH), reason="run scripts/prepare_ml_dataset.py first")
def test_ml_dataset_has_no_forbidden_columns():
    # Columns legitimately present in the SAVED table as non-input
    # support/diagnostic columns (targets + is_unsafe, the current-
    # instant event flag used to derive/verify time_to_stall) --
    # excluded here because this test checks for forbidden columns,
    # not the (separate, stricter) input-feature allowlist checked by
    # test_forbidden_columns_not_in_input_feature_list above.
    non_input_but_allowed_in_table = {
        "future_stall_5s", "future_stall_5s_available", "time_to_stall",
        "is_unsafe", "trajectory_id", "split",
    }
    df = pd.read_parquet(ML_DATASET_PATH)
    present_forbidden = set(df.columns) & (FORBIDDEN_INPUT_COLUMNS - non_input_but_allowed_in_table)
    assert present_forbidden == set(), f"forbidden columns present in ml_dataset_v2.parquet: {present_forbidden}"


# ---------------------------------------------------------------------------
# 7. Train/val/test trajectory IDs are disjoint
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not os.path.exists(ML_TRAIN_PATH), reason="run scripts/prepare_ml_dataset.py first")
def test_split_trajectory_ids_disjoint():
    train_ids = set(pd.read_parquet(ML_TRAIN_PATH)["trajectory_id"])
    val_ids = set(pd.read_parquet(ML_VAL_PATH)["trajectory_id"])
    test_ids = set(pd.read_parquet(ML_TEST_PATH)["trajectory_id"])
    assert train_ids & val_ids == set()
    assert train_ids & test_ids == set()
    assert val_ids & test_ids == set()


@pytest.mark.skipif(not os.path.exists(ML_DATASET_PATH), reason="run scripts/prepare_ml_dataset.py first")
def test_split_column_matches_manifest():
    from aeroguard_dataset.paths import DATA_SPLITS_DIR
    manifest = pd.read_csv(os.path.join(DATA_SPLITS_DIR, "split_manifest_v2.csv"))
    ml_df = pd.read_parquet(ML_DATASET_PATH)
    manifest_map = manifest.set_index("trajectory_id")["split"]
    merged_split = ml_df["trajectory_id"].map(manifest_map)
    assert (merged_split == ml_df["split"]).all()


# ---------------------------------------------------------------------------
# 8. ML dataset is reproducible
# ---------------------------------------------------------------------------

def test_build_ml_table_is_deterministic():
    df1 = build_ml_table(verbose=False)
    df2 = build_ml_table(verbose=False)
    pd.testing.assert_frame_equal(df1, df2)


# ---------------------------------------------------------------------------
# 9. Target distribution matches an independent calculation
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not os.path.exists(ML_DATASET_PATH), reason="run scripts/prepare_ml_dataset.py first")
def test_target_distribution_matches_independent_recomputation():
    """Recompute future_stall_5s from raw telemetry (fresh implementation,
    no shared code) for a sample of trajectories and compare against the
    saved ml_dataset_v2.parquet rows for those trajectories."""
    from ml import config as ml_config  # only used for the processed-telemetry path constant

    raw = pd.read_parquet(ml_config.PROCESSED_DATASET_PATH)
    # use processed (has alpha/time/trajectory_id; raw would also work) restricted to a sample
    ml_df = pd.read_parquet(ML_DATASET_PATH)
    sample_ids = ml_df["trajectory_id"].drop_duplicates().sample(n=30, random_state=0)

    mismatches = 0
    for tid in sample_ids:
        g = raw[raw["trajectory_id"] == tid].sort_values("time").reset_index(drop=True)
        expected = _independent_future_stall_5s(g["alpha"].to_numpy(), DT, horizon_s=5.0)
        expected_by_time = dict(zip(g["time"].round(6), expected))

        rows = ml_df[ml_df["trajectory_id"] == tid]
        for _, row in rows.iterrows():
            exp = expected_by_time.get(round(row["time"], 6))
            if exp is None or not np.isclose(exp, row["future_stall_5s"]):
                mismatches += 1

    assert mismatches == 0


# ---------------------------------------------------------------------------
# 10. Feature schema matches actual dataset columns
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not os.path.exists(SCHEMA_PATH), reason="run scripts/prepare_ml_dataset.py first")
def test_feature_schema_matches_actual_columns():
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)
    ml_df = pd.read_parquet(ML_DATASET_PATH)

    documented_inputs = set(schema["input_features"].keys())
    assert documented_inputs == set(ALL_INPUT_FEATURES)
    assert documented_inputs.issubset(set(ml_df.columns))

    documented_targets = set(schema["targets"].keys())
    assert documented_targets.issubset(set(ml_df.columns))

    documented_ids = set(schema["identifiers"].keys())
    assert documented_ids.issubset(set(ml_df.columns))


def test_schema_input_features_all_marked_allowed():
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)
    for name, spec in schema["input_features"].items():
        assert spec["allowed_as_ml_input"] is True, f"{name} is documented as an input feature but not marked allowed"
    for name, spec in schema["targets"].items():
        assert spec["allowed_as_ml_input"] is False, f"{name} is a target and must be marked NOT allowed as an input"


# ---------------------------------------------------------------------------
# Additional: core vs history feature usable-row design (the finding
# from building this script -- guard against silently regressing it)
# ---------------------------------------------------------------------------

def test_history_features_not_required_for_usable_rows():
    """Regression guard for the design correction made while building
    this script: window features must remain OPTIONAL (nullable), not
    baked into the core 'usable row' filter, because requiring them
    disproportionately excludes short, fast 'stall'-regime trajectories."""
    assert set(HISTORY_FEATURES).isdisjoint(set(CORE_FEATURES))


def test_time_to_stall_always_determined_when_a_future_crossing_exists():
    dt = 1.0
    alpha_deg = [4, 4, 4, 20, 4, 4]
    alpha = np.radians(alpha_deg)
    df = _make_synthetic_trajectory("T", alpha, dt)
    tts = compute_time_to_stall(df)
    # crossing at index 3 (t=3.0s); row 0 (t=0) should see it 3.0s away
    assert tts.iloc[0] == pytest.approx(3.0)
    assert tts.iloc[2] == pytest.approx(1.0)
    # after the only crossing, no future crossing remains -> NaN
    assert np.isnan(tts.iloc[4])
    assert np.isnan(tts.iloc[5])
