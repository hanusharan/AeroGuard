"""Synthetic known-answer tests for Items 37-39 (no research data)."""

import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "src"), str(HERE.parents[3])]
import items37_39 as m  # noqa: E402


def traj_block(n, name):
    return np.array([name] * n), np.arange(n) * m.DT


def test_episode_classes_and_rate_on_a_known_fixture():
    tr, t = traj_block(40, "a")
    score = np.zeros(40); score[[2, 3, 4, 10, 11, 20, 30, 31]] = 1.0          # 4 episodes: 2-4, 10-11, 20, 30-31
    label = np.zeros(40); label[10] = 1                                         # episode 10-11 is TRUE
    unsafe = np.zeros(40, dtype=bool); unsafe[20] = True                       # episode at 20 starts in a stall with label 0 -> ONGOING
    c = m.false_alarm_counts(tr, t, label, unsafe, score, 0.5)
    assert (c["total"][0], c["true"][0], c["ongoing"][0], c["false"][0]) == (4, 1, 1, 2)
    assert c["span_s"][0] == pytest.approx(0.39) and c["rows_s"][0] == pytest.approx(0.40)


def test_strict_threshold_and_gap_merging():
    tr, t = traj_block(300, "a")
    score = np.zeros(300); score[[0, 1]] = 0.5; score[10:12] = 1.0; score[150:152] = 1.0
    c0 = m.false_alarm_counts(tr, t, np.zeros(300), np.zeros(300, bool), score, 0.5)
    assert c0["total"][0] == 2                                                   # rows equal to the threshold are not warnings
    c1 = m.false_alarm_counts(tr, t, np.zeros(300), np.zeros(300, bool), score, 0.5, gap_s=1.0)
    assert c1["total"][0] == 2                                                   # gap 150-12-1 = 137 rows = 1.37 s > 1 s
    c2 = m.false_alarm_counts(tr, t, np.zeros(300), np.zeros(300, bool), score, 0.5, gap_s=2.0)
    assert c2["total"][0] == 1


def test_trajectories_are_never_merged_across_and_must_be_contiguous():
    a, ta = traj_block(5, "a"); b, tb = traj_block(5, "b")
    tr = np.concatenate([a, b]); t = np.concatenate([ta, tb]); s = np.ones(10)
    c = m.false_alarm_counts(tr, t, np.zeros(10), np.zeros(10, bool), s, 0.5, gap_s=2.0)
    assert c["total"].tolist() == [1, 1]
    with pytest.raises(ValueError):
        m.blocks(np.array(["a", "b", "a"]))


def test_event_table_lead_sustained_and_history():
    tr, t = traj_block(800, "a")
    unsafe = np.zeros(800, bool); unsafe[600:620] = True                        # crossing at t = 6.00 s
    score = np.zeros(800)
    score[150:160] = 1.0                                                        # warning 4.5 s ahead, short
    score[500:600] = 1.0                                                        # sustained 1.00 s before the crossing
    ev = m.event_table(tr, t, unsafe, score, 0.5)
    assert len(ev) == 1
    r = ev.iloc[0]
    assert r.crossing_time == pytest.approx(6.0) and r.warned and r.lead_s == pytest.approx(4.5)  # earliest qualifying episode
    assert r.sustained_rows == 100 and r.history_rows == 600 and r.first_event and not r.left_censored


def test_coverage_definitions_and_eligibility():
    tr, t = traj_block(800, "a")
    unsafe = np.zeros(800, bool); unsafe[600:620] = True
    score = np.zeros(800); score[150:160] = 1.0; score[500:600] = 1.0
    ev = m.event_table(tr, t, unsafe, score, 0.5)
    num, den = m.coverage_per_trajectory(ev, ["a"], 4.0)
    assert (num[0], den[0]) == (1, 1)                                           # existing definition: lead 4.5 >= 4
    num, den = m.coverage_per_trajectory(ev, ["a"], 4.0, sustained=True)
    assert (num[0], den[0]) == (0, 1)                                           # not on continuously for 4 s
    num, den = m.coverage_per_trajectory(ev, ["a"], 1.0, sustained=True)
    assert (num[0], den[0]) == (1, 1)
    ev2 = ev.copy(); ev2["history_rows"] = 150                                  # only 1.5 s of usable history before the crossing
    num, den = m.coverage_per_trajectory(ev2, ["a"], 2.0)
    assert den[0] == 0                                                          # not eligible at 2 s


def test_left_censored_event_is_flagged():
    tr, t = traj_block(50, "a")
    unsafe = np.zeros(50, bool); unsafe[:5] = True
    ev = m.event_table(tr, t, unsafe, np.zeros(50), 0.5)
    assert bool(ev.iloc[0].left_censored) and not ev.iloc[0].warned


def test_ratio_bootstrap_point_interval_and_undefined_replicates():
    num = np.array([2.0, 0.0, 1.0, 0.0]); den = np.array([10.0, 10.0, 10.0, 10.0])
    r = m.ratio_bootstrap(num, den, scale=3600.0, B_=200, seed=1)
    assert r["point"] == pytest.approx(3 / 40 * 3600) and r["ci_lo"] <= r["point"] <= r["ci_hi"]
    rng = np.random.default_rng(1); hand = []
    for _ in range(200):
        c = np.bincount(rng.integers(0, 4, size=4), minlength=4); hand.append((num * c).sum() / (den * c).sum() * 3600)
    assert r["ci_lo"] == pytest.approx(np.percentile(hand, 2.5))
    r2 = m.ratio_bootstrap(np.array([1.0, 0.0]), np.array([1.0, 0.0]), B_=300, seed=0)
    assert r2["n_undefined_replicates"] > 0
