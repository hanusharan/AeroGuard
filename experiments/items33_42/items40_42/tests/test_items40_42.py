"""Synthetic known-answer tests for Items 40-42 (no research data)."""

import inspect
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(HERE.parent / "src"), str(ROOT / "experiments/items33_42/items37_39/src"), str(ROOT)]
import items40_42 as m  # noqa: E402
import items37_39 as m37  # noqa: E402


def fixture(seed=0, T=6, n=400):
    rng = np.random.default_rng(seed)
    traj = np.repeat([f"t{i}" for i in range(T)], n)
    times = np.tile(np.arange(n) * 0.01, T)
    score = rng.random(T * n)
    label = (rng.random(T * n) < 0.2).astype(int)
    unsafe = rng.random(T * n) < 0.05
    return traj, times, score, label, unsafe


def test_fast_false_episode_count_equals_items37_39_definition():
    traj, times, score, label, unsafe = fixture()
    for thr in (0.3, 0.7, 0.95):
        ref = m37.false_alarm_counts(traj, times, label, unsafe, score, thr)["false"].sum()
        fast = m.false_episode_starts(m.first_rows(traj), label, unsafe, score > thr).sum()
        assert fast == ref


def test_episode_never_continues_across_a_trajectory_boundary():
    traj = np.array(["a"] * 3 + ["b"] * 3)
    pred = np.ones(6, bool)
    starts = m.false_episode_starts(m.first_rows(traj), np.zeros(6), np.zeros(6, bool), pred)
    assert starts.tolist() == [True, False, False, True, False, False]


def test_matched_threshold_is_first_candidate_meeting_the_target_and_uses_validation_only():
    traj, times, score, label, unsafe = fixture(1)
    first = m.first_rows(traj); hours = 6 * 3.99 / 3600
    r = m.matched_threshold(score, first, label, unsafe, hours, 2000.0)
    assert r["val_rate"] <= 2000.0
    cands = np.quantile(score, m.QUANTILE_LEVELS)
    earlier = cands[cands < r["threshold"]]
    rates = [m.false_episode_starts(first, label, unsafe, score > t).sum() / hours for t in earlier]
    assert all(x > 2000.0 for x in rates)
    assert list(inspect.signature(m.matched_threshold).parameters)[:4] == ["val_score", "val_first", "val_label", "val_unsafe"]
    assert m.matched_threshold(score, first, label, unsafe, hours, 0.0)["val_false_episodes"] == 0


def test_paired_draws_reproduce_items37_39_bootstrap():
    num = np.array([2.0, 0.0, 1.0, 3.0, 0.0]); den = np.array([10.0, 5.0, 10.0, 20.0, 0.0])
    ref = m37.ratio_bootstrap(num, den, scale=3600.0, B_=300, seed=7)
    C = m.draw_counts(5, 300, 7)
    got = m.interval(num.sum() / den.sum() * 3600, m.ratio_reps(num, den, C, 3600.0))
    assert got["ci_lo"] == pytest.approx(ref["ci_lo"]) and got["ci_hi"] == pytest.approx(ref["ci_hi"])
    assert got["n_undefined_replicates"] == ref["n_undefined_replicates"]


def test_wording_scan_flags_only_unqualified_lines():
    out = m.wording_scan(["This is not blind.", "Results are confirmatory.", "Plain line."])
    assert [(o["line_no"], o["flag"]) for o in out] == [(1, False), (2, True)]
