"""Event-level warning evaluation (Section 14/15/16).

Precise procedure (documented here AND in the report):

STALL EVENTS: a maximal contiguous run of is_unsafe==True within a
    trajectory is one "stall event". Its crossing_time is the time of
    the run's FIRST row (the actual physics-boundary crossing).

WARNING EPISODES: a maximal contiguous run of predicted-positive
    timesteps (using the frozen probability threshold) is one "warning
    episode". Grouping consecutive positive timesteps this way (Section
    15) avoids counting hundreds of individual positive rows as
    hundreds of independent warnings.

EVENT-LEVEL LEAD TIME: for a stall event with crossing_time t_c, we
    look for warning episodes that were ACTIVE at any point during the
    horizon window (t_c - 5s, t_c) -- i.e. episodes that overlap that
    window and start before t_c. Among qualifying episodes we take the
    one with the earliest start (maximizing credited lead time), and
    define:
        effective_start = max(episode.start, t_c - horizon_s)
        lead_time = t_c - effective_start
    The lead time is capped at the labeling horizon (5s) even if the
    episode started earlier: the model was only ever trained to predict
    "stall within the next 5s", so a warning issued more than 5s before
    the crossing was not verified against this specific event by the
    training target, and crediting more than 5s of lead time would
    overclaim what the model was asked (and shown) to do. If no
    qualifying episode exists, the event is MISSED.

FALSE ALARMS: for every warning episode (regardless of whether it was
    used to credit an event above), we check the true future_stall_5s
    label AT THE EPISODE'S START ROW (this reuses the exact,
    already-verified target computation from Stage 2 -- no separate
    "was a crossing nearby" logic is reimplemented). future_stall_5s==1
    there means a real crossing was indeed within the next 5s (a valid/
    true warning); ==0 means no crossing followed within 5s (a false
    alarm); NaN (insufficient trailing data) is excluded from the rate,
    not counted either way.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd


def group_boolean_into_episodes(times: np.ndarray, flags: np.ndarray) -> List[Tuple[float, float, int, int]]:
    """Maximal contiguous runs of flags==True. Returns
    (start_time, end_time, start_idx, end_idx) tuples, index into the
    given (already sorted-by-time) arrays. O(n)."""
    flags = np.asarray(flags, dtype=bool)
    times = np.asarray(times)
    n = len(flags)
    if n == 0:
        return []
    diff = np.diff(flags.astype(int))
    start_idx = np.where(diff == 1)[0] + 1
    if flags[0]:
        start_idx = np.concatenate([[0], start_idx])
    end_idx = np.where(diff == -1)[0]
    if flags[-1]:
        end_idx = np.concatenate([end_idx, [n - 1]])
    return [(float(times[s]), float(times[e]), int(s), int(e)) for s, e in zip(start_idx, end_idx)]


@dataclass
class StallEventResult:
    trajectory_id: str
    crossing_time: float
    warned: bool
    lead_time_s: Optional[float]
    warning_episode_start_s: Optional[float]


def compute_lead_times_for_trajectory(
    trajectory_id: str,
    full_times: np.ndarray, is_unsafe: np.ndarray,
    pred_times: np.ndarray, pred_flags: np.ndarray,
    horizon_s: float,
) -> List[StallEventResult]:
    """full_times/is_unsafe cover the WHOLE trajectory (event detection
    should see every actual crossing, not just rows with a prediction).
    pred_times/pred_flags cover only the rows where a prediction exists
    (may be a subset, e.g. missing each trajectory's first row for
    Feature Set C models -- documented in ml/features.py)."""
    stall_episodes = group_boolean_into_episodes(full_times, is_unsafe)
    warning_episodes = group_boolean_into_episodes(pred_times, pred_flags)

    results = []
    for cross_start, _cross_end, _si, _ei in stall_episodes:
        window_lo = cross_start - horizon_s
        qualifying = [we for we in warning_episodes if we[0] < cross_start and we[1] >= window_lo]
        if qualifying:
            best = min(qualifying, key=lambda we: we[0])  # earliest-starting qualifying episode
            effective_start = max(best[0], window_lo)
            lead_time = cross_start - effective_start
            results.append(StallEventResult(trajectory_id, cross_start, True, lead_time, best[0]))
        else:
            results.append(StallEventResult(trajectory_id, cross_start, False, None, None))
    return results


def compute_event_level_results(
    df: pd.DataFrame, pred_flags: np.ndarray, horizon_s: float,
    time_col: str = "time", traj_col: str = "trajectory_id", is_unsafe_col: str = "is_unsafe",
) -> List[StallEventResult]:
    """df: the TEST rows a model produced predictions for (already
    restricted to that model's valid/common-subset rows), with
    pred_flags aligned 1:1 with df's rows (same order). Stall events are
    still detected from each trajectory's FULL is_unsafe history
    (df must contain the complete trajectory's is_unsafe/time columns
    for event detection to see every real crossing -- see docstring)."""
    df = df.copy()
    df["_pred"] = np.asarray(pred_flags).astype(bool)

    all_results: List[StallEventResult] = []
    for tid, g in df.groupby(traj_col, sort=False):
        g = g.sort_values(time_col)
        results = compute_lead_times_for_trajectory(
            tid, g[time_col].to_numpy(), g[is_unsafe_col].to_numpy().astype(bool),
            g[time_col].to_numpy(), g["_pred"].to_numpy(), horizon_s,
        )
        all_results.extend(results)
    return all_results


def aggregate_event_results(results: List[StallEventResult]) -> dict:
    n_events = len(results)
    warned = [r for r in results if r.warned]
    lead_times = np.array([r.lead_time_s for r in warned], dtype=float)
    return {
        "n_events": n_events,
        "n_warned": len(warned),
        "n_missed": n_events - len(warned),
        "event_recall": (len(warned) / n_events) if n_events > 0 else float("nan"),
        "median_lead_time_s": float(np.median(lead_times)) if len(lead_times) else None,
        "mean_lead_time_s": float(np.mean(lead_times)) if len(lead_times) else None,
        "std_lead_time_s": float(np.std(lead_times)) if len(lead_times) > 1 else None,
        "min_lead_time_s": float(np.min(lead_times)) if len(lead_times) else None,
        "max_lead_time_s": float(np.max(lead_times)) if len(lead_times) else None,
        "lead_times_s": lead_times.tolist(),
    }


def compute_false_alarm_stats(
    df: pd.DataFrame, pred_flags: np.ndarray, n_test_trajectories: int,
    time_col: str = "time", traj_col: str = "trajectory_id", target_col: str = "future_stall_5s",
) -> dict:
    """See module docstring for the FALSE ALARMS definition."""
    df = df.copy()
    df["_pred"] = np.asarray(pred_flags).astype(bool)

    n_episodes = n_true = n_false = n_undetermined = 0
    for tid, g in df.groupby(traj_col, sort=False):
        g = g.sort_values(time_col).reset_index(drop=True)
        episodes = group_boolean_into_episodes(g[time_col].to_numpy(), g["_pred"].to_numpy())
        for _s, _e, start_idx, _ei in episodes:
            n_episodes += 1
            val = g.loc[start_idx, target_col]
            if pd.isna(val):
                n_undetermined += 1
            elif val == 1.0:
                n_true += 1
            else:
                n_false += 1

    denom = n_true + n_false
    return {
        "n_warning_episodes": n_episodes,
        "n_true_warning_episodes": n_true,
        "n_false_alarm_episodes": n_false,
        "n_undetermined_episodes": n_undetermined,
        "false_warning_rate": (n_false / denom) if denom > 0 else float("nan"),
        "precision_at_operating_point_episode_level": (n_true / denom) if denom > 0 else float("nan"),
        "warnings_per_trajectory": (n_episodes / n_test_trajectories) if n_test_trajectories else None,
    }
