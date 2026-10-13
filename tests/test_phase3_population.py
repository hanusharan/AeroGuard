"""Phase 3 tests: common evaluation population, row identity and integrity helpers
(PROTOCOL.md sections 8.1, 8.4 and 13).

SYNTHETIC ONLY. Every fixture is generated in memory or in pytest's tmp_path. No test in this
file (or any other Phase 3 test) opens, hashes or reads the regenerated v0.3 dataset, and no
test is enabled by an environment variable. ``make_panel`` below is also used by the other
Phase 3 test files.
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aeroguard_dataset.features import causal_backward_difference
from aeroguard_dataset.labeling import compute_future_stall_label
from ml.temporal_features import build_temporal_panel
from phase3 import A_PEAK_RAD, DT, HORIZON_STEPS, WARMUP_STEPS
from phase3 import population as pop

PULSES = {"normal": [], "pos": [(650, 1)], "neg": [(650, -1)], "double": [(300, 1), (650, 1)], "mixed": [(300, -1), (650, 1)]}


def _time_to_stall(time, is_unsafe):
    out = np.full(len(time), np.nan)
    unsafe_idx = np.flatnonzero(is_unsafe)
    for i in range(len(time)):
        later = unsafe_idx[unsafe_idx > i]
        if later.size:
            out[i] = time[later[0]] - time[i]
    return out


def make_panel(prefix, kinds, seed=0, length=1200):
    """Synthetic trajectories with the real panel's columns (windows built by the project's own
    ``build_temporal_panel``). Each pulse is a Gaussian excursion of alpha past +/-alpha_peak."""
    rng = np.random.default_rng(seed)
    idx = np.arange(length)
    frames = []
    for n, kind in enumerate(kinds):
        alpha = 0.01 * np.sin(idx / 80.0 + n) + 0.0005 * rng.standard_normal(length)
        for centre, sign in PULSES[kind]:
            alpha = alpha + sign * 0.33 * np.exp(-0.5 * ((idx - centre) / 60.0) ** 2)
        time = idx * DT
        is_unsafe = np.abs(alpha) > A_PEAK_RAD
        gamma = 0.02 * np.sin(idx / 150.0) + 0.001 * rng.standard_normal(length)
        pitch_rate = 0.01 * rng.standard_normal(length)
        label, avail = compute_future_stall_label(is_unsafe, DT, 5.0)
        frames.append(pd.DataFrame({
            "trajectory_id": f"{prefix}_{n:03d}", "time": time, "V": 40.0 + 0.3 * rng.standard_normal(length), "alpha": alpha,
            "gamma": gamma, "altitude": 500.0 + np.cumsum(0.01 * rng.standard_normal(length)), "pitch_rate": pitch_rate,
            "elevator": -0.02 + 0.005 * rng.standard_normal(length), "throttle": 0.5 + 0.01 * rng.standard_normal(length),
            "stall_margin": A_PEAK_RAD - alpha, "is_unsafe": is_unsafe,
            "dV_dt": causal_backward_difference(40.0 + 0.0 * time, DT), "dalpha_dt": causal_backward_difference(alpha, DT),
            "dgamma_dt": causal_backward_difference(gamma, DT), "dq_dt": causal_backward_difference(pitch_rate, DT),
            "future_stall_5s": label, "future_stall_5s_available": avail, "time_to_stall": _time_to_stall(time, is_unsafe),
        }))
    df = pd.concat(frames, ignore_index=True)
    return build_temporal_panel(df, windows_s=[0.5, 1.0, 2.0], dt=DT).sort_values(["trajectory_id", "time"]).reset_index(drop=True)


KINDS = ["normal", "normal", "pos", "neg", "double", "mixed"]


@pytest.fixture(scope="module")
def panel():
    return make_panel("p", KINDS, seed=1)


def test_the_test_tree_contains_no_real_dataset_files():
    """Fail closed: if regenerated parquet files exist in the tree running the tests, stop here."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    found = []
    for base, _dirs, files in os.walk(os.path.join(root, "data")):
        found += [os.path.join(base, f) for f in files if f.endswith(".parquet")]
    assert not found, f"real data files present in the Phase 3 test tree: {found[:3]}"


def test_row_keys_are_unique_contiguous_and_ordered(panel):
    keys = pop.row_keys(panel)
    assert len(keys) == len(panel)
    assert len(set(zip(keys.traj, keys.step))) == len(panel)


def test_duplicate_rows_are_rejected(panel):
    dup = pd.concat([panel.iloc[:5], panel.iloc[[4]], panel.iloc[5:]], ignore_index=True)
    with pytest.raises(pop.KeyMismatchError):
        pop.row_keys(dup)


def test_interleaved_trajectories_are_rejected(panel):
    mixed = panel.sample(frac=1.0, random_state=0).reset_index(drop=True)
    with pytest.raises(pop.KeyMismatchError):
        pop.row_keys(mixed)


def test_time_off_the_grid_is_rejected(panel):
    bad = panel.iloc[:20].copy()
    bad["time"] = bad["time"] + 0.003
    with pytest.raises(pop.KeyMismatchError):
        pop.row_keys(bad)


def test_assert_same_keys_detects_reordering_missing_rows_and_relabelling(panel):
    sub = panel.loc[pop.usable_mask(panel)].reset_index(drop=True)
    keys = pop.row_keys(sub)
    pop.assert_same_keys(keys, pop.row_keys(sub))
    swapped = sub.copy()
    swapped.iloc[[3, 4]] = swapped.iloc[[4, 3]].to_numpy()
    with pytest.raises(pop.KeyMismatchError):
        pop.assert_same_keys(keys, pop.row_keys(swapped))   # silent reordering is detected
    with pytest.raises(pop.KeyMismatchError):
        pop.assert_same_keys(keys, pop.row_keys(sub.iloc[1:]))  # a missing row is detected
    renamed = pop.RowKeys(traj=np.array(["x"] * len(keys)), step=keys.step)
    with pytest.raises(pop.KeyMismatchError):
        pop.assert_same_keys(keys, renamed)


def test_prediction_sets_require_one_finite_score_per_eligible_row(panel):
    sub = panel.loc[pop.usable_mask(panel)].reset_index(drop=True)
    keys = pop.row_keys(sub)
    s = np.linspace(0, 1, len(keys))
    pop.make_prediction_set("ok", keys, s)
    with pytest.raises(pop.MissingPredictionError):
        pop.make_prediction_set("short", keys, s[:-1])
    bad = s.copy()
    bad[7] = np.nan
    with pytest.raises(pop.MissingPredictionError):
        pop.make_prediction_set("nan", keys, bad)
    bad[7] = np.inf
    with pytest.raises(pop.MissingPredictionError):
        pop.make_prediction_set("inf", keys, bad)


def test_common_population_requires_identical_keys_and_labels_for_every_method(panel):
    sub = panel.loc[pop.usable_mask(panel)].reset_index(drop=True)
    keys, labels = pop.row_keys(sub), sub["future_stall_5s"].to_numpy().astype(int)
    a = pop.make_prediction_set("a", keys, np.zeros(len(keys)))
    b = pop.make_prediction_set("b", keys, np.ones(len(keys)))
    pop.assert_common_population(keys, labels, [a, b])
    shifted = pop.RowKeys(traj=keys.traj, step=keys.step + 1)
    with pytest.raises(pop.KeyMismatchError):
        pop.assert_common_population(keys, labels, [a, pop.make_prediction_set("c", shifted, np.ones(len(keys)))])
    with pytest.raises(pop.KeyMismatchError):
        pop.assert_common_population(keys, labels[:-1], [a])


def test_usable_rows_are_exactly_after_warmup_and_before_the_unlabelled_tail(panel):
    mask = pop.usable_mask(panel)
    for tid, g in panel.groupby("trajectory_id"):
        pos = np.flatnonzero(mask[g.index.to_numpy()])
        n = len(g)
        assert pos.min() == WARMUP_STEPS and pos.max() == n - HORIZON_STEPS - 1 and len(pos) == pos.max() - pos.min() + 1


def test_history_windows_never_cross_a_trajectory_boundary(panel):
    for _, g in panel.groupby("trajectory_id"):
        head = g.iloc[:WARMUP_STEPS]
        assert head[pop.WINDOW_COLUMNS].isna().any(axis=1).all(), "a window was filled with rows of another trajectory"
        assert g.iloc[WARMUP_STEPS][pop.WINDOW_COLUMNS].notna().all()


def test_eligible_rows_are_consecutive_steps_and_a_gap_is_detected(panel):
    sub = panel.loc[pop.usable_mask(panel)].reset_index(drop=True)
    assert pop.assert_consecutive_steps(pop.row_keys(sub)) == len(KINDS)
    gapped = sub.drop(index=[10]).reset_index(drop=True)
    with pytest.raises(pop.KeyMismatchError):
        pop.assert_consecutive_steps(pop.row_keys(gapped))


def test_eligible_time_matches_the_existing_span_definition(panel):
    sub = panel.loc[pop.usable_mask(panel)].reset_index(drop=True)
    et = pop.eligible_time(pop.row_keys(sub))
    existing = float(sub.groupby("trajectory_id")["time"].apply(lambda s: s.max() - s.min()).sum())  # run_false_alarm_analysis
    assert et["span_seconds"] == pytest.approx(existing, abs=1e-9)
    assert et["rows_times_dt_seconds"] - et["span_seconds"] == pytest.approx(et["n_trajectories"] * DT, abs=1e-9)


def test_population_summary_and_event_counts_match_independent_counts(panel):
    n_traj = len(KINDS)
    summ = pop.summarize_population(panel)
    assert summ["rows_total"] == n_traj * 1200 and summ["trajectories_total"] == n_traj
    usable_per_traj = 1200 - HORIZON_STEPS - WARMUP_STEPS
    assert summ["rows_usable"] == n_traj * usable_per_traj
    assert summ["positives"] + summ["negatives"] == summ["rows_usable"]
    assert summ["trajectories_with_any_unsafe_run"] == 4  # pos, neg, double, mixed
    # independent event count: maximal runs of unsafe rows among usable rows
    mask = pop.usable_mask(panel)
    expected_events = 0
    for _, g in panel.loc[mask].groupby("trajectory_id"):
        u = g["is_unsafe"].to_numpy().astype(int)
        expected_events += int(((np.diff(np.concatenate([[0], u])) == 1)).sum())
    ev = pop.count_events(panel, mask)
    assert ev["events"] == expected_events == 1 + 1 + 2 + 2
    assert ev["first_events"] == 4 and ev["later_events"] == 2 and ev["trajectories_with_events"] == 4


def test_compare_counts_reports_mismatches_and_missing_keys():
    expected = {"a": 1, "b": 2}
    assert pop.compare_counts({"a": 1, "b": 2}, expected) == []
    assert any("b" in p for p in pop.compare_counts({"a": 1, "b": 3}, expected))
    assert any("not observed" in p for p in pop.compare_counts({"a": 1}, expected))


def test_reported_counts_are_internally_consistent_with_the_protocol():
    c = pop.REPORTED_COUNTS
    assert c["panel_rows_train"] + c["panel_rows_val"] + c["panel_rows_test"] == c["dataset_rows"] == 5_340_865
    assert c["trajectories_train"] + c["trajectories_val"] + c["trajectories_test"] == c["dataset_trajectories"] == 3_150
    assert c["test_positive_rows"] + c["test_negative_rows"] == c["usable_rows_test"] == 538_034
    assert c["test_first_events"] + c["test_later_events"] == c["test_events"] == 76


def test_no_trajectory_may_appear_in_two_splits():
    pop.assert_no_trajectory_overlap({"train": {"a", "b"}, "val": {"c"}, "test": {"d"}})
    with pytest.raises(pop.KeyMismatchError):
        pop.assert_no_trajectory_overlap({"train": {"a", "b"}, "val": {"b"}, "test": {"d"}})


def test_load_split_refuses_a_disallowed_split_before_touching_any_file(tmp_path):
    with pytest.raises(pop.GateViolation):
        pop.load_split(tmp_path / "does_not_exist", "test", ["alpha"], allowed_splits=("train", "val"))
    with pytest.raises(ValueError):
        pop.load_split(tmp_path, "holdout", ["alpha"], allowed_splits=("train", "val", "test"))


def test_load_split_reads_only_the_requested_columns_of_one_split(tmp_path, panel):
    d = tmp_path / "ml_temporal_v03"
    d.mkdir()
    panel.to_parquet(d / "temporal_train.parquet", index=False)
    tab = pop.load_split(tmp_path, "train", ["trajectory_id", "alpha"], allowed_splits=("train",))
    assert tab.split == "train" and list(tab.df.columns) == ["trajectory_id", "alpha"] and len(tab.df) == len(panel)
    with pytest.raises(pop.DataIntegrityError):
        pop.load_split(tmp_path, "val", ["alpha"], allowed_splits=("train", "val"))  # file absent -> error, never a fallback
    assert pop.schema_missing_columns(d / "temporal_train.parquet", ["alpha", "nonexistent"]) == ["nonexistent"]


def test_hash_verification_detects_changed_and_missing_files(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"abc")
    good = {"a.bin": pop.sha256_file(tmp_path / "a.bin")}
    assert pop.verify_file_hashes(tmp_path, good)[0]["ok"]
    (tmp_path / "a.bin").write_bytes(b"abd")
    with pytest.raises(pop.DataIntegrityError):
        pop.verify_file_hashes(tmp_path, good)
    with pytest.raises(pop.DataIntegrityError):
        pop.verify_file_hashes(tmp_path, {"missing.bin": "0" * 64})


def test_protocol_hash_must_match(tmp_path):
    p = tmp_path / "PROTOCOL.md"
    p.write_text("locked text")
    ok = pop.sha256_file(p)
    assert pop.verify_protocol(p, ok) == ok
    p.write_text("edited text")
    with pytest.raises(pop.DataIntegrityError):
        pop.verify_protocol(p, ok)


def test_item26_cross_check_requires_equal_keys_and_labels_and_fails_closed_on_unknown_schema(panel):
    sub = panel.loc[pop.usable_mask(panel)].reset_index(drop=True)
    keys, labels = pop.row_keys(sub), sub["future_stall_5s"].to_numpy().astype(int)
    other = pd.DataFrame({"trajectory_id": keys.traj, "step": keys.step})
    assert pop.compare_with_item26(keys, labels, other, labels)["keys_equal"]
    flipped = labels.copy()
    flipped[0] = 1 - flipped[0]
    assert not pop.compare_with_item26(keys, labels, other, flipped)["labels_equal"]
    assert pop.compare_with_item26(keys, labels, pd.DataFrame({"trajectory_id": keys.traj, "time": keys.step * DT}), labels)["keys_equal"]
    with pytest.raises(ValueError):
        pop.compare_with_item26(keys, labels, pd.DataFrame({"trajectory_id": keys.traj}), labels)


def test_output_paths_are_confined_to_the_phase3_directory(tmp_path):
    root = tmp_path
    ok = pop.assert_phase3_output_path(root / "outputs" / "phase3" / "run_x" / "f.json", root)
    assert ok.name == "f.json"
    for bad in (root / "outputs" / "ml_v03" / "metrics" / "x.json", root / "outputs" / "ml_v03" / "models" / "primary_model_D_1s.joblib",
                root / "outputs" / "analysis_v11" / "x.json", root / "data" / "x.json", root / "outputs" / "x.json",
                root / "outputs" / "phase3" / "x.json", root / "outputs" / "phase3" / "not_a_run" / "x.json"):  # must be inside run_<UTC>/
        with pytest.raises(pop.GateViolation):
            pop.assert_phase3_output_path(bad, root)
