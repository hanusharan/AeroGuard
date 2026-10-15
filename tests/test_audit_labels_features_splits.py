"""Audit tests for train/test separation, temporal-feature causality and
future-event label semantics (roadmap items 20-22).

These add coverage for gaps found while auditing the existing suite; they do
not replace it. Everything uses tiny in-memory arrays or the small tracked
manifest/metadata CSVs, and the frozen v0.3 model is only *read*. No dataset
is generated or loaded, and no scientific code or artifact is modified.

Where a test pins down the behavior of the current implementation (for
example how rows inside an unsafe run are labeled), it documents what the code
does today; it is not a statement that the behavior is the best design.
"""

import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aeroguard_dataset.features import causal_backward_difference
from aeroguard_dataset.labeling import compute_future_stall_label
from aeroguard_dataset.splitting import split_trajectory_ids, verify_no_overlap
from ml import temporal_config as tcfg
from ml.temporal_features import build_temporal_panel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DT = 0.01
ALPHA_PEAK = 0.28044009791924895  # same constant the existing feature tests use


# ---------------------------------------------------------------------------
# Item 22: future-event label semantics, boundary behavior
# ---------------------------------------------------------------------------

def _labels(unsafe_idx, n, horizon_s=3.0, dt=1.0):
    u = np.zeros(n, dtype=bool)
    u[list(unsafe_idx)] = True
    return compute_future_stall_label(u, dt, horizon_s)


def test_label_window_is_exclusive_of_now_and_inclusive_of_horizon():
    # unsafe sample at index 10, horizon 3 steps -> window for row i is (i, i+3]
    labels, available = _labels([10], n=20)
    assert labels[7] == 1.0   # exactly at the horizon: (7, 10] contains 10
    assert labels[9] == 1.0   # just before the event
    assert labels[6] == 0.0   # one step beyond the horizon: (6, 9] misses 10
    assert labels[10] == 0.0  # the unsafe row does not count itself
    assert labels[11] == 0.0  # after the event, nothing further ahead
    assert available[:17].all() and not available[17:].any()  # last 3 rows lack a full window
    assert np.isnan(labels[17:]).all()


def test_label_is_positive_inside_a_persistent_unsafe_run():
    # Documents current behavior: rows already inside an unsafe run are labeled
    # 1 while at least one *later* unsafe sample is within the horizon.
    labels, _ = _labels([10, 11, 12], n=20)
    assert labels[10] == 1.0 and labels[11] == 1.0  # later unsafe samples exist
    assert labels[12] == 0.0 and labels[13] == 0.0  # run ended, nothing ahead


def test_label_handles_two_separate_unsafe_runs():
    labels, _ = _labels([5, 12], n=20)
    assert labels[2] == 1.0 and labels[3] == 1.0  # first event ahead
    assert labels[5] == 0.0 and labels[8] == 0.0  # between events, outside both windows
    assert labels[9] == 1.0                       # second event ahead (10, 11, 12]
    assert labels[1] == 0.0                       # (1, 4] is clear


def test_label_for_event_inside_the_trailing_unlabeled_region():
    # n=20, horizon 3 -> rows 0..16 are labeled; an event at index 18 is still
    # visible to row 16 ((16, 19]) but the event's own row has no label.
    labels, available = _labels([18], n=20)
    assert labels[16] == 1.0 and available[16]
    assert not available[18] and np.isnan(labels[18])


def test_label_is_all_unavailable_when_trajectory_is_not_longer_than_horizon():
    labels, available = _labels([1], n=3)
    assert np.isnan(labels).all() and not available.any()


def test_label_boundary_with_the_real_timestep_and_horizon():
    n = 1001
    u = np.zeros(n, dtype=bool)
    u[700] = True
    labels, _ = compute_future_stall_label(u, 0.01, 5.0)  # 500 steps
    assert labels[200] == 1.0   # (200, 700] contains 700
    assert labels[199] == 0.0   # (199, 699] does not


# ---------------------------------------------------------------------------
# Item 21: model inputs use only current and past samples (whole pipeline)
# ---------------------------------------------------------------------------

def _trajectory_frame(alpha, V, gamma, pitch_rate, elevator, tid="T"):
    """Builds the base + derived columns the same way the real pipeline does
    (backward differences, stall_margin), then lets build_temporal_panel add
    the windowed and second-derivative columns."""
    n = len(alpha)
    return pd.DataFrame({
        "trajectory_id": tid, "time": np.arange(n) * DT,
        "V": V, "alpha": alpha, "gamma": gamma, "pitch_rate": pitch_rate,
        "altitude": 1000.0, "elevator": elevator, "throttle": 0.4,
        "stall_margin": ALPHA_PEAK - alpha,
        "dV_dt": causal_backward_difference(V, DT),
        "dalpha_dt": causal_backward_difference(alpha, DT),
        "dgamma_dt": causal_backward_difference(gamma, DT),
        "dq_dt": causal_backward_difference(pitch_rate, DT),
    })


def _random_channels(n, seed=0):
    rng = np.random.default_rng(seed)
    return (
        0.1 + np.cumsum(rng.normal(0, 1e-3, n)),   # alpha
        45.0 + np.cumsum(rng.normal(0, 1e-2, n)),  # V
        np.cumsum(rng.normal(0, 1e-3, n)),         # gamma
        rng.normal(0, 1e-2, n),                    # pitch_rate
        0.01 + np.cumsum(rng.normal(0, 1e-4, n)),  # elevator
    )


@pytest.mark.parametrize("k", [150, 250, 399])
def test_every_model_d_input_before_a_future_sample_is_unchanged_by_it(k):
    n = 400
    base = _random_channels(n)
    perturbed = [c.copy() for c in base]
    for c in perturbed:
        c[k] += 5.0  # a large change to one *future* sample in every raw channel

    cols = tcfg.model_d_features(1.0)
    panel_a = build_temporal_panel(_trajectory_frame(*base), windows_s=[1.0])
    panel_b = build_temporal_panel(_trajectory_frame(*perturbed), windows_s=[1.0])

    before_a, before_b = panel_a.loc[: k - 1, cols], panel_b.loc[: k - 1, cols]
    np.testing.assert_array_equal(before_a.to_numpy(), before_b.to_numpy())  # NaNs compare equal
    # sanity: the perturbation really is visible at and after k, so the check can fail
    assert not np.array_equal(panel_a.loc[k:, cols].to_numpy(), panel_b.loc[k:, cols].to_numpy(), equal_nan=True)


def test_the_future_perturbation_check_detects_a_non_causal_feature():
    # Positive control: a centered rolling mean is not causal and must be caught.
    n, k = 400, 300
    alpha = _random_channels(n)[0]
    altered = alpha.copy()
    altered[k] += 5.0
    centered_a = pd.Series(alpha).rolling(101, center=True, min_periods=1).mean()
    centered_b = pd.Series(altered).rolling(101, center=True, min_periods=1).mean()
    assert not np.array_equal(centered_a[:k].to_numpy(), centered_b[:k].to_numpy())


def test_model_d_feature_columns_are_all_produced_and_label_free():
    cols = tcfg.model_d_features(1.0)
    assert len(cols) == 23 and len(set(cols)) == 23
    panel = build_temporal_panel(_trajectory_frame(*_random_channels(300)), windows_s=[1.0])
    assert set(cols) <= set(panel.columns)
    forbidden = {"future_stall_5s", "future_stall_5s_available", "is_unsafe",
                 "trajectory_id", "time", "split", "time_to_stall", "generation_mode"}
    assert not (set(cols) & forbidden)


FROZEN_MODEL = os.path.join(ROOT, "outputs", "ml_v03", "models", "primary_model_D_1s.joblib")


@pytest.mark.skipif(not os.path.exists(FROZEN_MODEL), reason="frozen v0.3 model not present")
def test_frozen_v03_model_inputs_are_exactly_the_documented_causal_features():
    joblib = pytest.importorskip("joblib")
    model = joblib.load(FROZEN_MODEL)  # read-only
    assert list(model.feature_names_in_) == tcfg.model_d_features(1.0)
    assert model.n_features_in_ == 23


# ---------------------------------------------------------------------------
# Item 20: trajectory-level splits, checked on the tracked manifests only
# ---------------------------------------------------------------------------

MANIFESTS = [
    ("v0.1", "split_manifest.csv", "trajectory_metadata.csv", "generation_config.json"),
    ("v0.2", "split_manifest_v2.csv", "trajectory_metadata_v2.csv", "generation_config_v2.json"),
    ("v0.3", "split_manifest_v3.csv", "trajectory_metadata_v3.csv", "generation_config_v3.json"),
]


def _load(manifest, metadata, config):
    m = pd.read_csv(os.path.join(ROOT, "data", "splits", manifest))
    md = pd.read_csv(os.path.join(ROOT, "data", "metadata", metadata))
    with open(os.path.join(ROOT, "data", "metadata", config)) as f:
        cfg = json.load(f)
    seed = cfg.get("seed", cfg.get("generation_config", {}).get("seed"))
    return m, md, seed


@pytest.mark.parametrize("version,manifest,metadata,config", MANIFESTS)
def test_tracked_manifest_assigns_each_trajectory_to_exactly_one_split(version, manifest, metadata, config):
    m, md, _ = _load(manifest, metadata, config)
    verify_no_overlap(m)
    assert set(m["split"]) == {"train", "val", "test"}
    assert set(m["trajectory_id"]) == set(md["trajectory_id"])  # covers every generated trajectory
    n = len(m)
    counts = m["split"].value_counts()
    n_train, n_val = int(round(0.70 * n)), int(round(0.15 * n))
    assert counts["train"] == n_train and counts["val"] == n_val and counts["test"] == n - n_train - n_val


@pytest.mark.parametrize("version,manifest,metadata,config", MANIFESTS)
def test_tracked_manifest_is_reproducible_from_ids_and_seed(version, manifest, metadata, config):
    m, md, seed = _load(manifest, metadata, config)
    assert seed is not None
    rebuilt = split_trajectory_ids(md["trajectory_id"].tolist(), seed)
    tracked = m.sort_values("trajectory_id").reset_index(drop=True)[["trajectory_id", "split"]]
    pd.testing.assert_frame_equal(rebuilt, tracked)


def test_v03_has_no_duplicate_initial_conditions_across_trajectories():
    _, md, _ = _load("split_manifest_v3.csv", "trajectory_metadata_v3.csv", "generation_config_v3.json")
    cols = ["initial_airspeed", "initial_altitude", "initial_alpha"]
    assert not md.duplicated(cols).any()
