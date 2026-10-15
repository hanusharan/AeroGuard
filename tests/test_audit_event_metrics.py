"""Audit tests for event-level metrics and warning lead time (roadmap items
23 and 24), written as small hand-calculable cases.

Every expected value below is derived by hand from the documented rules in
ml/events.py: a stall event is the first row of a maximal run of is_unsafe; a
warning episode is a maximal run of positive predictions; an event is detected
if some episode starts strictly before the crossing time and ends no earlier
than (crossing - horizon); the credited lead time is
min(crossing - episode_start, horizon) for the earliest-starting such episode;
missed events carry no lead time and are left out of the lead-time statistics.

Several tests pin down behavior that is a *design property* of the current
implementation (for example, that a one-sample warning earns full credit). They
document what the code does; they do not claim it is the best definition. No
scientific code, dataset or published number is touched.
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.events import (
    aggregate_event_results,
    compute_event_level_results,
    compute_false_alarm_stats,
    compute_lead_times_for_trajectory,
)

HORIZON = 5.0


def _run(unsafe, warn_runs, n=20, horizon=HORIZON):
    """unsafe: indices where is_unsafe is True. warn_runs: (first, last)
    inclusive index pairs of positive predictions. Time is 1 s per index."""
    times = np.arange(n, dtype=float)
    is_unsafe = np.zeros(n, dtype=bool)
    is_unsafe[list(unsafe)] = True
    pred = np.zeros(n, dtype=bool)
    for a, b in warn_runs:
        pred[a:b + 1] = True
    return compute_lead_times_for_trajectory("t", times, is_unsafe, times, pred, horizon)


# crossing at t=10, horizon 5 -> the eligible warning window starts at t=5

def test_lead_time_for_a_warning_comfortably_before_the_event():
    (r,) = _run([10], [(7, 8)])
    assert r.warned and r.crossing_time == 10.0
    assert r.lead_time_s == pytest.approx(3.0)
    assert r.warning_episode_start_s == 7.0


def test_warning_starting_exactly_on_the_horizon_boundary_gets_the_full_horizon():
    (r,) = _run([10], [(5, 6)])
    assert r.warned and r.lead_time_s == pytest.approx(5.0)


def test_warning_that_began_before_the_horizon_and_persists_is_capped_at_the_horizon():
    (r,) = _run([10], [(2, 7)])
    assert r.warned and r.lead_time_s == pytest.approx(5.0)  # not 8.0
    assert r.warning_episode_start_s == 2.0                  # true onset is still reported


def test_warning_ending_exactly_at_the_window_start_still_counts_as_boundary_behavior():
    # The comparison is `end >= crossing - horizon` (closed), so an episode that
    # ends at t=5 qualifies even though it never overlaps the open window (5, 10).
    (r,) = _run([10], [(2, 5)])
    assert r.warned and r.lead_time_s == pytest.approx(5.0)


def test_warning_ending_just_before_the_window_does_not_count():
    (r,) = _run([10], [(2, 4)])
    assert not r.warned and r.lead_time_s is None


def test_warning_starting_at_the_crossing_is_too_late_and_one_step_earlier_gets_one_step_of_lead():
    (late,) = _run([10], [(10, 12)])
    assert not late.warned
    (barely,) = _run([10], [(9, 12)])
    assert barely.warned and barely.lead_time_s == pytest.approx(1.0)  # one sample counts as a detection


def test_event_with_no_qualifying_warning_is_missed():
    (r,) = _run([10], [(1, 2)])  # too early: ends before the window
    assert not r.warned and r.lead_time_s is None and r.warning_episode_start_s is None


def test_with_several_qualifying_episodes_the_earliest_start_sets_the_lead_time():
    (r,) = _run([10], [(1, 2), (7, 8), (9, 9)])  # (1,2) is outside the window
    assert r.warned and r.lead_time_s == pytest.approx(3.0)


def test_a_one_sample_early_warning_earns_credit_even_if_it_does_not_persist():
    # Design property: there is no persistence or hysteresis requirement.
    (r,) = _run([10], [(6, 6), (8, 11)])
    assert r.warned and r.lead_time_s == pytest.approx(4.0)


def test_one_long_warning_is_credited_to_every_event_it_covers():
    # Two events (re-entry): crossings at t=6 and t=14, one episode over t=3..10.
    results = _run([6, 14], [(3, 10)])
    assert [r.crossing_time for r in results] == [6.0, 14.0]
    assert results[0].lead_time_s == pytest.approx(3.0)
    assert results[1].warned and results[1].lead_time_s == pytest.approx(5.0)  # episode still overlaps (9, 14)


def test_an_unsafe_run_is_one_event_not_one_event_per_row():
    results = _run([10, 11, 12], [(8, 9)])
    assert len(results) == 1 and results[0].crossing_time == 10.0


# --- events and rows removed by evaluation masks ---------------------------------

def _frame(times, unsafe):
    return pd.DataFrame({"trajectory_id": "t", "time": times, "is_unsafe": unsafe})


def test_an_event_whose_rows_are_all_masked_out_is_not_counted_at_all():
    # compute_event_level_results only sees the rows it is given. If the crossing
    # and everything after it were removed by a mask (as happens for crossings in
    # the last 5 s of a trajectory, whose label is unavailable), the event is
    # neither detected nor counted as missed.
    visible = _frame(np.arange(10, dtype=float), np.zeros(10, dtype=bool))
    assert compute_event_level_results(visible, np.ones(10, dtype=bool), HORIZON) == []


def test_an_event_that_starts_before_the_first_visible_row_is_dated_at_that_row():
    # Rows t<10 removed; the unsafe run really began at t=8. The event is reported
    # at the first visible row (t=10), so its crossing time and lead time are
    # measured from there.
    times = np.arange(10, 20, dtype=float)
    unsafe = np.array([1, 1, 1, 0, 0, 0, 0, 0, 0, 0], dtype=bool)
    results = compute_event_level_results(_frame(times, unsafe), np.zeros(10, dtype=bool), HORIZON)
    assert len(results) == 1 and results[0].crossing_time == 10.0 and not results[0].warned


def test_predictions_may_cover_fewer_rows_than_the_event_timeline():
    full_times = np.arange(20, dtype=float)
    is_unsafe = np.zeros(20, dtype=bool)
    is_unsafe[10] = True
    pred_times = np.arange(3, 20, dtype=float)             # no predictions for t < 3
    pred = np.zeros(len(pred_times), dtype=bool)
    pred[pred_times == 7.0] = True
    (r,) = compute_lead_times_for_trajectory("t", full_times, is_unsafe, pred_times, pred, HORIZON)
    assert r.warned and r.lead_time_s == pytest.approx(3.0)


# --- aggregation: the median lead time is conditional on detected events ---------

def _result(tid, lead):
    from ml.events import StallEventResult
    return StallEventResult(tid, 10.0, lead is not None, lead, None if lead is None else 10.0 - lead)


def test_median_lead_time_ignores_missed_events_while_recall_counts_them():
    agg = aggregate_event_results([_result("a", 1.0), _result("b", 5.0), _result("c", None), _result("d", None)])
    assert agg["n_events"] == 4 and agg["n_warned"] == 2 and agg["n_missed"] == 2
    assert agg["event_recall"] == pytest.approx(0.5)
    assert agg["median_lead_time_s"] == pytest.approx(3.0)  # median of [1, 5] only
    assert agg["lead_times_s"] == [1.0, 5.0]


def test_aggregate_with_no_detections_and_with_no_events():
    none_warned = aggregate_event_results([_result("a", None), _result("b", None)])
    assert none_warned["event_recall"] == 0.0 and none_warned["median_lead_time_s"] is None
    no_events = aggregate_event_results([])
    assert np.isnan(no_events["event_recall"]) and no_events["median_lead_time_s"] is None


# --- false alarms are judged by the label at the episode start -------------------

def test_false_alarm_episodes_are_classified_by_the_label_at_their_first_row():
    n = 12
    df = pd.DataFrame({
        "trajectory_id": "t", "time": np.arange(n, dtype=float),
        # label at each row: true warning (1.0) at t=1, false alarm (0.0) at t=5, unavailable (NaN) at t=9
        "future_stall_5s": [0, 1, 1, 0, 0, 0, 0, 0, 0, np.nan, np.nan, np.nan],
    })
    pred = np.zeros(n, dtype=bool)
    pred[[1, 2]] = True   # episode starting at t=1 -> label 1.0
    pred[[5]] = True      # episode starting at t=5 -> label 0.0
    pred[[9, 10]] = True  # episode starting at t=9 -> label NaN, excluded from the rate
    stats = compute_false_alarm_stats(df, pred, n_test_trajectories=1)
    assert stats["n_warning_episodes"] == 3
    assert stats["n_true_warning_episodes"] == 1
    assert stats["n_false_alarm_episodes"] == 1
    assert stats["n_undetermined_episodes"] == 1
    assert stats["false_warning_rate"] == pytest.approx(0.5)
