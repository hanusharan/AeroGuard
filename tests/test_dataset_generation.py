"""Tests for the Stage 2 dataset-generation pipeline (aeroguard_dataset/).

These tests use small trajectory counts (not the full 1000) purely for
speed; the logic being tested is identical regardless of dataset size.
They must not modify, and do not touch, the core physics tests.
"""

import dataclasses
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aeroguard.aircraft import Aircraft
from aeroguard.dynamics import Controls

from aeroguard_dataset.audit import verify_causal_derivatives, verify_future_labels, verify_monotonic_time
from aeroguard_dataset.config import GenerationConfig, compute_validity_envelope
from aeroguard_dataset.dataset_builder import build_dataset, RAW_COLUMNS
from aeroguard_dataset.events import resolve_stall_boundary
from aeroguard_dataset.labeling import compute_future_stall_label
from aeroguard_dataset.splitting import split_trajectory_ids, verify_no_overlap
from aeroguard_dataset.trajectory_sim import (
    simulate_trajectory,
    TERMINATION_COMPLETED,
    TERMINATION_GAMMA_EXCEEDED,
    TERMINATION_GROUND_CONTACT,
    TERMINATION_LOW_AIRSPEED,
)

SMALL_N = 40


@pytest.fixture(scope="module")
def small_cfg():
    return dataclasses.replace(GenerationConfig(), n_trajectories=SMALL_N)


@pytest.fixture(scope="module")
def small_dataset(small_cfg):
    raw_df, processed_df, metadata_df, v0_check = build_dataset(small_cfg, verbose=False)
    return raw_df, processed_df, metadata_df, v0_check


# ---------------------------------------------------------------------------
# Deterministic generation / reproducibility
# ---------------------------------------------------------------------------

def test_deterministic_generation_same_seed(small_cfg):
    raw1, proc1, meta1, _ = build_dataset(small_cfg, verbose=False)
    raw2, proc2, meta2, _ = build_dataset(small_cfg, verbose=False)

    pd_testing_equal(raw1, raw2)
    pd_testing_equal(proc1, proc2)
    assert meta1["initial_airspeed"].tolist() == meta2["initial_airspeed"].tolist()
    assert meta1["generation_mode"].tolist() == meta2["generation_mode"].tolist()
    assert meta1["termination_reason"].tolist() == meta2["termination_reason"].tolist()


def test_different_seed_gives_different_generation():
    cfg_a = dataclasses.replace(GenerationConfig(), n_trajectories=10, seed=1)
    cfg_b = dataclasses.replace(GenerationConfig(), n_trajectories=10, seed=2)
    _, _, meta_a, _ = build_dataset(cfg_a, verbose=False)
    _, _, meta_b, _ = build_dataset(cfg_b, verbose=False)
    assert meta_a["initial_airspeed"].tolist() != meta_b["initial_airspeed"].tolist()


def pd_testing_equal(a, b):
    import pandas as pd
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))


# ---------------------------------------------------------------------------
# Unique trajectory IDs
# ---------------------------------------------------------------------------

def test_unique_trajectory_ids(small_dataset):
    raw_df, processed_df, metadata_df, _ = small_dataset
    assert metadata_df["trajectory_id"].nunique() == len(metadata_df) == SMALL_N
    assert set(raw_df["trajectory_id"].unique()) == set(metadata_df["trajectory_id"])
    assert set(processed_df["trajectory_id"].unique()) == set(metadata_df["trajectory_id"])


# ---------------------------------------------------------------------------
# Correct duration / telemetry columns
# ---------------------------------------------------------------------------

def test_completed_trajectories_reach_full_duration(small_cfg, small_dataset):
    _, _, metadata_df, _ = small_dataset
    completed = metadata_df[metadata_df["termination_reason"] == TERMINATION_COMPLETED]
    assert len(completed) > 0, "expected at least one trajectory to complete the full nominal duration"
    expected_steps = int(round(small_cfg.duration_s / small_cfg.dt)) + 1
    assert (completed["n_steps"] == expected_steps).all()
    assert np.allclose(completed["duration_actual_s"], small_cfg.duration_s, atol=small_cfg.dt)


def test_terminated_trajectories_are_shorter_than_nominal(small_cfg, small_dataset):
    _, _, metadata_df, _ = small_dataset
    terminated = metadata_df[metadata_df["termination_reason"] != TERMINATION_COMPLETED]
    if len(terminated) == 0:
        pytest.skip("no early-terminated trajectories in this small sample/seed")
    assert (terminated["duration_actual_s"] < small_cfg.duration_s).all()


def test_altitude_never_negative_in_generated_dataset(small_dataset):
    """Pipeline-level check of the ground-contact invariant (Section
    Task 2, item 2): no matter which trajectories happen to reach the
    ground in a given generation run, the recorded raw telemetry must
    never contain a non-positive altitude value."""
    raw_df, _, _, _ = small_dataset
    assert (raw_df["altitude"] > 0).all()


def test_raw_telemetry_columns(small_dataset):
    raw_df, _, _, _ = small_dataset
    assert list(raw_df.columns) == RAW_COLUMNS


def test_processed_table_has_raw_plus_derived_columns(small_dataset):
    _, processed_df, _, _ = small_dataset
    for col in RAW_COLUMNS:
        assert col in processed_df.columns
    for col in ["dV_dt", "dalpha_dt", "stall_margin", "is_unsafe", "future_stall_5s", "future_stall_5s_available"]:
        assert col in processed_df.columns


# ---------------------------------------------------------------------------
# No future leakage in derived features
# ---------------------------------------------------------------------------

def test_no_future_leakage_in_derived_features(small_cfg, small_dataset):
    raw_df, processed_df, _, _ = small_dataset
    result = verify_causal_derivatives(raw_df, processed_df, small_cfg.dt, sample_trajectories=SMALL_N)
    assert result["passed"], result["mismatches"]


def test_derivative_first_row_of_each_trajectory_is_nan(small_dataset):
    _, processed_df, _, _ = small_dataset
    first_rows = processed_df.sort_values("time").groupby("trajectory_id").head(1)
    assert first_rows["dV_dt"].isna().all()
    assert first_rows["dalpha_dt"].isna().all()


# ---------------------------------------------------------------------------
# Correct 5-second future labeling
# ---------------------------------------------------------------------------

def test_future_label_hand_constructed_example():
    dt = 1.0
    is_unsafe = np.array([False] * 6 + [True] + [False] * 3, dtype=bool)
    labels, available = compute_future_stall_label(is_unsafe, dt=dt, horizon_s=3.0)

    assert available[3] and labels[3] == 1.0  # window (4,5,6] contains the unsafe sample at 6
    assert available[6] and labels[6] == 0.0  # window (7,8,9] contains no unsafe sample
    assert not available[7] and np.isnan(labels[7])
    assert not available[9] and np.isnan(labels[9])


def test_future_label_excludes_current_sample():
    """The row at the unsafe sample itself should not count its own
    is_unsafe=True toward its own future label."""
    dt = 1.0
    is_unsafe = np.array([True, False, False, False], dtype=bool)
    labels, available = compute_future_stall_label(is_unsafe, dt=dt, horizon_s=2.0)
    assert available[0]
    assert labels[0] == 0.0  # future window (1,2] is all False


def test_future_labels_computed_from_future_trajectory_data(small_cfg, small_dataset):
    _, processed_df, _, _ = small_dataset
    result = verify_future_labels(processed_df, small_cfg.dt, small_cfg.labeling_horizon_s, sample_trajectories=SMALL_N)
    assert result["passed"], result["mismatches"]


def test_last_horizon_seconds_excluded_from_labeling(small_cfg, small_dataset):
    _, processed_df, _, _ = small_dataset
    horizon_steps = int(round(small_cfg.labeling_horizon_s / small_cfg.dt))
    for tid, g in processed_df.groupby("trajectory_id"):
        g = g.sort_values("time")
        tail = g.tail(horizon_steps)
        assert tail["future_stall_5s_available"].eq(False).all()
        assert tail["future_stall_5s"].isna().all()


# ---------------------------------------------------------------------------
# Train/validation/test trajectory separation
# ---------------------------------------------------------------------------

def test_split_by_trajectory_not_timestep(small_dataset):
    _, _, metadata_df, _ = small_dataset
    manifest = split_trajectory_ids(metadata_df["trajectory_id"].tolist(), seed=999)
    verify_no_overlap(manifest)  # raises on any violation

    assert set(manifest["trajectory_id"]) == set(metadata_df["trajectory_id"])
    assert set(manifest["split"].unique()) <= {"train", "val", "test"}


def test_split_fractions_approximately_70_15_15():
    ids = [f"traj_{i:04d}" for i in range(1000)]
    manifest = split_trajectory_ids(ids, seed=20260817)
    counts = manifest["split"].value_counts()
    assert counts["train"] == 700
    assert counts["val"] == 150
    assert counts["test"] == 150


def test_split_is_deterministic():
    ids = [f"traj_{i:04d}" for i in range(200)]
    m1 = split_trajectory_ids(ids, seed=5)
    m2 = split_trajectory_ids(ids, seed=5)
    assert m1.equals(m2)


# ---------------------------------------------------------------------------
# Validity-envelope detection
# ---------------------------------------------------------------------------

def test_validity_envelope_low_airspeed_detected():
    """Note: for this aircraft, v_floor (0.5*V_stall) sits well below
    V_stall itself, so any state that close to v_floor is already in
    insufficient-lift territory -- exploratory testing found the
    dynamics reliably dive (and so trip the gamma cap) before airspeed
    can gently decay across that much of a gap under any hand-crafted
    control profile tried. Rather than hunt for an unrealistic profile,
    this test directly verifies the low-airspeed check itself: starting
    already below the floor must be caught and terminate at the very
    first recorded step, not several steps in and not silently."""
    aircraft = Aircraft()
    cfg = GenerationConfig()
    _, v_floor, gamma_max = compute_validity_envelope(aircraft, cfg)

    def profile(t):
        return Controls(throttle=0.5, elevator=0.0)

    result = simulate_trajectory("test_low_v", aircraft, profile, V0=v_floor - 1.0, gamma0=0.0, alpha0=0.03, h0=1000.0, q0=0.0, duration_s=20.0, dt=0.01, v_floor=v_floor, gamma_max_rad=gamma_max)
    assert result.termination_reason == TERMINATION_LOW_AIRSPEED
    assert result.validity_envelope_exceeded
    assert len(result.t) == 1  # caught on the very first recorded step
    assert result.V[-1] < v_floor


def test_validity_envelope_gamma_exceeded_detected():
    aircraft = Aircraft()
    cfg = GenerationConfig()
    _, v_floor, gamma_max = compute_validity_envelope(aircraft, cfg)

    # Large sustained elevator: pitches up hard enough to exceed the
    # 45 deg gamma cap well within 20s (checked empirically: 0.35 rad
    # was not consistently enough, 0.5 rad reliably is).
    def profile(t):
        return Controls(throttle=0.6, elevator=0.5)

    result = simulate_trajectory("test_gamma", aircraft, profile, V0=50.0, gamma0=0.0, alpha0=0.05, h0=1000.0, q0=0.0, duration_s=20.0, dt=0.01, v_floor=v_floor, gamma_max_rad=gamma_max)
    assert result.termination_reason == TERMINATION_GAMMA_EXCEEDED
    assert result.validity_envelope_exceeded
    assert abs(result.gamma[-1]) > gamma_max


def test_validity_envelope_ground_contact_detected():
    """Direct, deterministic check of the ground-contact condition
    itself: starting already at/below h=0 must be caught before that
    (physically impossible) state is ever recorded. Unlike the
    low-airspeed/gamma checks (which record the violating sample and
    THEN stop), ground contact is a hard physical floor -- the
    trajectory has zero valid samples here, since it starts invalid."""
    aircraft = Aircraft()
    cfg = GenerationConfig()
    _, v_floor, gamma_max = compute_validity_envelope(aircraft, cfg)

    def profile(t):
        return Controls(throttle=0.5, elevator=0.0)

    result = simulate_trajectory("test_ground", aircraft, profile, V0=45.0, gamma0=0.0, alpha0=0.05, h0=-5.0, q0=0.0, duration_s=20.0, dt=0.01, v_floor=v_floor, gamma_max_rad=gamma_max)
    assert result.termination_reason == TERMINATION_GROUND_CONTACT
    assert result.validity_envelope_exceeded
    assert len(result.t) == 0
    assert len(result.altitude) == 0


def test_validity_envelope_ground_contact_from_sustained_descent():
    """A dynamic (not instantaneous) case: a gentle sustained sub-gamma-cap
    descent from a low starting altitude reaches h<=0 well before gamma
    or airspeed would ever trip -- this is the actual mechanism found in
    the v0.2 audit (2 trajectories reached negative altitude while
    staying inside the V/gamma envelope throughout). The recorded
    telemetry must stop at the last physically valid (h>0) sample --
    never record a negative altitude, and don't clip it to zero either."""
    aircraft = Aircraft()
    cfg = GenerationConfig()
    _, v_floor, gamma_max = compute_validity_envelope(aircraft, cfg)

    def profile(t):
        return Controls(throttle=0.1, elevator=-0.03)

    result = simulate_trajectory("test_ground_dynamic", aircraft, profile, V0=45.0, gamma0=0.0, alpha0=0.05, h0=5.0, q0=0.0, duration_s=20.0, dt=0.01, v_floor=v_floor, gamma_max_rad=gamma_max)
    assert result.termination_reason == TERMINATION_GROUND_CONTACT
    assert result.validity_envelope_exceeded
    assert len(result.altitude) > 0
    assert result.altitude[-1] > 0  # last recorded sample is pre-contact, never negative or zero
    assert np.all(result.altitude > 0)  # no negative/zero altitude anywhere in the recorded telemetry
    assert result.V[-1] >= v_floor  # confirms this wasn't secretly a low-airspeed case
    assert abs(result.gamma[-1]) <= gamma_max  # confirms this wasn't secretly a gamma case


def test_normal_trim_hold_does_not_exceed_envelope():
    """Sanity check: a genuinely-trimmed, unperturbed flight must not
    spuriously trip the validity envelope."""
    from aeroguard_dataset.paths import trim_level_flight

    aircraft = Aircraft()
    cfg = GenerationConfig()
    _, v_floor, gamma_max = compute_validity_envelope(aircraft, cfg)
    alpha_trim, throttle_trim, elevator_trim = trim_level_flight(aircraft, 45.0)

    def profile(t):
        return Controls(throttle=throttle_trim, elevator=elevator_trim)

    result = simulate_trajectory("test_trim_hold", aircraft, profile, V0=45.0, gamma0=0.0, alpha0=alpha_trim, h0=1000.0, q0=0.0, duration_s=20.0, dt=0.01, v_floor=v_floor, gamma_max_rad=gamma_max)
    assert result.termination_reason == TERMINATION_COMPLETED
    assert not result.validity_envelope_exceeded


# ---------------------------------------------------------------------------
# Metadata generation
# ---------------------------------------------------------------------------

REQUIRED_METADATA_COLUMNS = [
    "trajectory_id", "generation_mode", "random_seed", "initial_airspeed",
    "initial_altitude", "initial_alpha", "trim_throttle", "trim_elevator",
    "maximum_alpha", "minimum_airspeed", "maximum_airspeed", "maximum_abs_gamma",
    "whether_stall_occurred", "time_of_first_stall", "whether_validity_envelope_was_exceeded",
    "termination_reason",
]


def test_metadata_has_all_required_columns(small_dataset):
    _, _, metadata_df, _ = small_dataset
    for col in REQUIRED_METADATA_COLUMNS:
        assert col in metadata_df.columns, f"missing required metadata column: {col}"


def test_metadata_time_of_first_stall_consistent_with_stall_flag(small_dataset):
    _, _, metadata_df, _ = small_dataset
    stalled = metadata_df[metadata_df["whether_stall_occurred"]]
    not_stalled = metadata_df[~metadata_df["whether_stall_occurred"]]
    assert stalled["time_of_first_stall"].notna().all()
    assert not_stalled["time_of_first_stall"].isna().all()


# ---------------------------------------------------------------------------
# Temporal correctness
# ---------------------------------------------------------------------------

def test_timestamps_monotonic_within_each_trajectory(small_dataset):
    raw_df, _, _, _ = small_dataset
    result = verify_monotonic_time(raw_df)
    assert result["passed"], result["non_monotonic_trajectory_ids"]


# ---------------------------------------------------------------------------
# Stall boundary uses the actual physics model
# ---------------------------------------------------------------------------

def test_stall_boundary_matches_actual_cl_peak():
    from aeroguard.aerodynamics import lift_coefficient

    aircraft = Aircraft()
    boundary = resolve_stall_boundary(aircraft)

    # CL just below the located peak should be lower than CL at the peak
    # (confirms it really is a peak of the actual lift_coefficient()).
    cl_at_peak = lift_coefficient(boundary.alpha_at_cl_peak, aircraft)
    cl_below = lift_coefficient(boundary.alpha_at_cl_peak - np.radians(1.0), aircraft)
    cl_above = lift_coefficient(boundary.alpha_at_cl_peak + np.radians(1.0), aircraft)
    assert cl_at_peak >= cl_below
    assert cl_at_peak >= cl_above


# ---------------------------------------------------------------------------
# v0 range validation (Section 4)
# ---------------------------------------------------------------------------

def test_v0_range_checked_against_stall_speed(small_dataset):
    _, _, _, v0_check = small_dataset
    assert v0_check["v0_min_above_vstall"]
    assert v0_check["v0_min_above_v_floor"]
