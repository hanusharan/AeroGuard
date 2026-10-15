"""Analysis helpers for Items 28, 29 and 32.

* ``negative_alpha_q1_q3`` / ``negative_alpha_q4``: the TRAIN-ONLY investigation of
  PROTOCOL.md 5.4 (the Q3 > 0 decision rule uses Q1-Q3 only; Q4 never influences it).
* ``threshold_free_metrics`` / ``operating_point``: the metrics of PROTOCOL.md 8.3,
  assembled from the EXISTING ``ml.evaluation``, ``ml.events`` and
  ``ml.temporal_experiment.run_false_alarm_analysis`` (reused unchanged).
* ``trajectory_bootstrap`` / ``run_protocol_bootstrap``: the paired trajectory bootstrap of
  PROTOCOL.md 9.3 (B = 1000, seed 20261013, percentile intervals). The resampling unit is the
  trajectory; one draw is shared by every method within a replicate.

Importing this module reads no data.
"""

from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from ml.evaluation import compute_classification_metrics  # reused unchanged
from ml.events import aggregate_event_results, compute_event_level_results  # reused unchanged
from ml.temporal_experiment import run_false_alarm_analysis  # reused unchanged

from . import BOOTSTRAP_B, BOOTSTRAP_INTERVAL_PCT, BOOTSTRAP_SEED, HORIZON_S, HORIZON_STEPS
from .population import (
    AVAILABLE_COL,
    TARGET_COL,
    WINDOW_COLUMNS,
    SplitTable,
    eligible_time,
    require_split,
    row_keys,
    trajectory_blocks,
    usable_mask,
)


class LabelSemanticsError(ValueError):
    """The stored label disagrees with the label recomputed from is_unsafe (PROTOCOL.md 5.1)."""


# ---------------------------------------------------------------------------------------
# Negative-alpha investigation (D4 / D16; TRAIN rows only)
# ---------------------------------------------------------------------------------------

NEGATIVE_ALPHA_COLUMNS = ["trajectory_id", "time", "alpha", "is_unsafe", TARGET_COL, AVAILABLE_COL] + WINDOW_COLUMNS


def q3_decision(q3: int) -> bool:
    """PROTOCOL.md 5.4 (approved): run the two-sided sensitivity analysis iff Q3 > 0.
    The argument is the count Q3 only; nothing else can influence the decision."""
    return int(q3) > 0


def negative_alpha_q1_q3(train: SplitTable) -> Dict[str, object]:
    """Q1: unsafe rows by sign of alpha; Q2: trajectories with a negative-side unsafe row;
    Q3: usable label-positive rows whose future window holds negative-side unsafe samples and
    no positive-side one. Refuses any split other than train."""
    require_split(train, "train")
    df = train.df
    missing = [c for c in NEGATIVE_ALPHA_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"train table lacks columns {missing}")
    row_keys(df)  # trajectories contiguous, steps strictly increasing
    alpha = df["alpha"].to_numpy(dtype=float)
    if not np.isfinite(alpha).all():
        raise ValueError("train alpha contains non-finite values")
    unsafe = df["is_unsafe"].to_numpy(dtype=bool)
    neg, pos = unsafe & (alpha < 0), unsafe & (alpha > 0)
    if (unsafe & (alpha == 0)).any():
        raise LabelSemanticsError("is_unsafe is true at alpha == 0, inconsistent with |alpha| > alpha_peak")
    starts, ends, codes = trajectory_blocks(df["trajectory_id"].to_numpy())
    n = len(df)
    h = HORIZON_STEPS
    derived_valid = np.zeros(n, dtype=bool)
    derived_any = np.zeros(n, dtype=bool)
    neg_only = np.zeros(n, dtype=bool)
    for s, e in zip(starts, ends):
        m = int(e - s)
        if m <= h:
            continue
        cn = np.concatenate([[0], np.cumsum(neg[s:e])])
        cp = np.concatenate([[0], np.cumsum(pos[s:e])])
        k = m - h
        i = np.arange(k)
        n_neg = cn[i + h + 1] - cn[i + 1]  # unsafe samples in (i, i + h]
        n_pos = cp[i + h + 1] - cp[i + 1]
        derived_valid[s:s + k] = True
        derived_any[s:s + k] = (n_neg + n_pos) > 0
        neg_only[s:s + k] = (n_neg > 0) & (n_pos == 0)
    avail = df[AVAILABLE_COL].to_numpy(dtype=bool)
    label = df[TARGET_COL].to_numpy(dtype=float)
    if not np.array_equal(avail, derived_valid):
        raise LabelSemanticsError("label availability differs from 'the first len - 500 rows of each trajectory'")
    if (avail & (label != derived_any.astype(float))).any():
        raise LabelSemanticsError("stored future_stall_5s differs from the label recomputed from is_unsafe")
    usable = usable_mask(df)
    q3 = int((usable & (label == 1.0) & neg_only).sum())
    return {
        "split": "train",
        "q1_unsafe_rows_alpha_positive": int(pos.sum()),
        "q1_unsafe_rows_alpha_negative": int(neg.sum()),
        "q2_trajectories_with_negative_side_unsafe_row": int(np.unique(codes[neg]).size),
        "q3_negative_only_positive_rows": q3,
        "n_usable_rows": int(usable.sum()),
        "n_usable_positive_rows": int((usable & (label == 1.0)).sum()),
        "n_trajectories": int(len(starts)),
        "decision_criterion": "run two-sided sensitivity analysis iff Q3 > 0",
        "run_two_sided": q3_decision(q3),
    }


def negative_alpha_q4(train: SplitTable, tau_rad: float) -> Dict[str, object]:
    """Q4 (computed at G6 after tau is frozen): usable train rows with alpha < -tau, by label.
    Descriptive only; it has no path into ``q3_decision``."""
    require_split(train, "train")
    df = train.df
    usable = usable_mask(df)
    alpha = df["alpha"].to_numpy(dtype=float)
    label = df[TARGET_COL].to_numpy(dtype=float)
    sel = usable & (alpha < -float(tau_rad))
    return {
        "split": "train",
        "tau_rad": float(tau_rad),
        "q4_usable_rows_alpha_below_minus_tau": int(sel.sum()),
        "q4_of_which_label_1": int((sel & (label == 1.0)).sum()),
        "q4_of_which_label_0": int((sel & (label == 0.0)).sum()),
        "influences_q3_decision": False,
    }


# ---------------------------------------------------------------------------------------
# Metrics (PROTOCOL.md 8.3)
# ---------------------------------------------------------------------------------------

def threshold_free_metrics(y, score) -> Dict[str, float]:
    y = np.asarray(y).astype(int)
    s = np.asarray(score, dtype=float)
    if not np.isfinite(s).all():
        raise ValueError("scores must be finite")
    n_pos = int(y.sum())
    return {
        "pr_auc": float(average_precision_score(y, s)) if n_pos > 0 else float("nan"),
        "roc_auc": float(roc_auc_score(y, s)) if 0 < n_pos < len(y) else float("nan"),
    }


def operating_point(eligible: pd.DataFrame, y, score, threshold: float) -> Dict[str, object]:
    """Threshold-dependent metrics at ``score > threshold`` (strict). ``eligible`` holds the
    eligible rows in the same order as ``y`` / ``score`` (columns trajectory_id, time,
    is_unsafe, future_stall_5s, time_to_stall)."""
    y = np.asarray(y).astype(int)
    s = np.asarray(score, dtype=float)
    if not (len(eligible) == len(y) == len(s)):
        raise ValueError("eligible table, labels and scores must have the same length")
    pred = (s > float(threshold)).astype(int)
    cls = compute_classification_metrics(y, pred, s)
    results = compute_event_level_results(eligible, pred, HORIZON_S)
    agg = aggregate_event_results(results)
    at_cap = int(sum(1 for r in results if r.warned and r.lead_time_s is not None and r.lead_time_s >= HORIZON_S - 1e-12))
    fa = run_false_alarm_analysis(eligible, y, pred)
    seconds = float(fa["total_test_trajectory_seconds"])
    ep = fa["episode_level"]
    return {
        "threshold": float(threshold),
        "operator": "strict >",
        "classification": cls,
        "events": {**{k: agg[k] for k in agg if k != "lead_times_s"}, "n_lead_at_5s_cap": at_cap, "lead_times_s": list(agg["lead_times_s"])},
        "false_alarms": {
            "episodes": ep,
            "eligible_seconds_span": seconds,
            "eligible_hours_span": seconds / 3600.0,
            "false_alarm_episodes_per_eligible_hour": (ep["n_false_alarm_episodes"] / (seconds / 3600.0)) if seconds > 0 else float("nan"),
            "row_level_false_positive_rate": fa["row_level_false_positive_rate"],
        },
        "n_rows_where_gt_and_ge_differ": int(((s >= float(threshold)) != (s > float(threshold))).sum()),
        "eligible_time": eligible_time(row_keys(eligible)),
    }


def events_by_trajectory(results) -> Dict[object, List[Tuple[bool, float]]]:
    out: Dict[object, List[Tuple[bool, float]]] = {}
    for r in results:
        out.setdefault(r.trajectory_id, []).append((bool(r.warned), float(r.lead_time_s) if r.lead_time_s is not None else float("nan")))
    return out


# ---------------------------------------------------------------------------------------
# Paired trajectory bootstrap (PROTOCOL.md 9.3)
# ---------------------------------------------------------------------------------------

def draw_rows(draw: np.ndarray, starts: np.ndarray, ends: np.ndarray) -> np.ndarray:
    """Row indices of the drawn trajectories, each trajectory kept whole, repeated as often as drawn."""
    lengths = (ends - starts)[draw]
    total = int(lengths.sum())
    if total == 0:
        return np.zeros(0, dtype=np.int64)
    first = np.repeat(starts[draw] - np.concatenate([[0], np.cumsum(lengths)[:-1]]), lengths)
    return (first + np.arange(total)).astype(np.int64)


def _interval(values: np.ndarray) -> Tuple[Optional[float], Optional[float], int]:
    finite = values[np.isfinite(values)]
    n_undefined = int(values.size - finite.size)
    if finite.size == 0:
        return None, None, n_undefined
    lo, hi = np.percentile(finite, BOOTSTRAP_INTERVAL_PCT)
    return float(lo), float(hi), n_undefined


def trajectory_bootstrap(
    traj_ids, y, scores: Mapping[str, np.ndarray], pairs: Sequence[Tuple[str, str]],
    B: int, seed: int, events: Optional[Mapping[str, Mapping[object, List[Tuple[bool, float]]]]] = None,
) -> Tuple[Dict[str, object], Dict[str, np.ndarray]]:
    """Resample trajectories (never rows) with replacement; within one replicate the same draw
    is applied to every method (paired). Returns (summary, replicate arrays)."""
    traj_ids = np.asarray(traj_ids)
    y = np.asarray(y).astype(int)
    names = list(scores)
    for nm in names:
        if len(scores[nm]) != len(y):
            raise ValueError(f"scores[{nm}] and labels differ in length")
    if len(traj_ids) != len(y):
        raise ValueError("trajectory ids and labels differ in length")
    starts, ends, codes = trajectory_blocks(traj_ids)
    uniques = pd.unique(traj_ids)
    n_traj = len(starts)
    if n_traj != len(uniques):
        raise ValueError("rows of a trajectory are not contiguous")
    for a, b in pairs:
        if a not in scores or b not in scores:
            raise ValueError(f"unknown method in pair {(a, b)}")
    ev_prep = None
    if events is not None:
        ev_prep = {}
        for nm in names:
            n_ev = np.zeros(n_traj, dtype=np.int64)
            n_w = np.zeros(n_traj, dtype=np.int64)
            leads = [np.zeros(0) for _ in range(n_traj)]
            for t, tid in enumerate(uniques):
                lst = events[nm].get(tid, [])
                n_ev[t] = len(lst)
                w = [lead for warned, lead in lst if warned]
                n_w[t] = len(w)
                leads[t] = np.asarray(w, dtype=float)
            ev_prep[nm] = (n_ev, n_w, leads)

    metrics = ("pr_auc", "roc_auc")
    reps: Dict[str, np.ndarray] = {f"{nm}|{mt}": np.full(B, np.nan) for nm in names for mt in metrics}
    if ev_prep is not None:
        for nm in names:
            reps[f"{nm}|event_recall"] = np.full(B, np.nan)
            reps[f"{nm}|median_lead_s"] = np.full(B, np.nan)
    rng = np.random.default_rng(seed)
    for b in range(B):
        draw = rng.integers(0, n_traj, size=n_traj)
        rows = draw_rows(draw, starts, ends)
        yb = y[rows]
        n_pos = int(yb.sum())
        for nm in names:
            sb = np.asarray(scores[nm])[rows]
            if n_pos > 0:
                reps[f"{nm}|pr_auc"][b] = average_precision_score(yb, sb)
            if 0 < n_pos < len(yb):
                reps[f"{nm}|roc_auc"][b] = roc_auc_score(yb, sb)
            if ev_prep is not None:
                n_ev, n_w, leads = ev_prep[nm]
                tot, warned = int(n_ev[draw].sum()), int(n_w[draw].sum())
                if tot > 0:
                    reps[f"{nm}|event_recall"][b] = warned / tot
                if warned > 0:
                    reps[f"{nm}|median_lead_s"][b] = float(np.median(np.concatenate([leads[t] for t in draw])))

    point: Dict[str, float] = {}
    for nm in names:
        for mt, val in threshold_free_metrics(y, scores[nm]).items():
            point[f"{nm}|{mt}"] = val
        if ev_prep is not None:
            n_ev, n_w, leads = ev_prep[nm]
            point[f"{nm}|event_recall"] = float(n_w.sum() / n_ev.sum()) if n_ev.sum() > 0 else float("nan")
            all_leads = np.concatenate(leads) if leads else np.zeros(0)
            point[f"{nm}|median_lead_s"] = float(np.median(all_leads)) if all_leads.size else float("nan")

    per_method = {}
    for key, arr in reps.items():
        lo, hi, n_undef = _interval(arr)
        per_method[key] = {"point": point[key], "ci_lo": lo, "ci_hi": hi, "n_undefined_replicates": n_undef}
    diffs = {}
    for a, b in pairs:
        for mt in metrics:
            d = reps[f"{a}|{mt}"] - reps[f"{b}|{mt}"]
            lo, hi, n_undef = _interval(d)
            diffs[f"{a} - {b} | {mt}"] = {
                "point": point[f"{a}|{mt}"] - point[f"{b}|{mt}"], "ci_lo": lo, "ci_hi": hi, "n_undefined_replicates": n_undef,
                "ci_includes_zero": (lo is not None and lo <= 0.0 <= hi),
            }
    summary = {
        "config": {
            "unit": "trajectory", "n_trajectories": int(n_traj), "n_rows": int(len(y)), "B": int(B), "seed": int(seed),
            "interval": f"percentile {BOOTSTRAP_INTERVAL_PCT[0]}/{BOOTSTRAP_INTERVAL_PCT[1]}",
            "pairing": "one trajectory draw per replicate, shared by every method",
            "undefined_replicates": "counted, not dropped silently",
        },
        "per_method": per_method,
        "paired_differences": diffs,
    }
    return summary, reps


def run_protocol_bootstrap(traj_ids, y, scores, pairs, events=None):
    """The approved configuration only: B = 1000, seed 20261013 (D15). No B / seed arguments."""
    return trajectory_bootstrap(traj_ids, y, scores, pairs, B=BOOTSTRAP_B, seed=BOOTSTRAP_SEED, events=events)
