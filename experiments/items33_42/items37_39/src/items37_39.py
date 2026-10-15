"""Items 37-39: false-warning episodes per simulated hour, warning coverage at lead times, trajectory and event counts.

Implements experiments/items33_42/items37_39/PROTOCOL.md. Pure functions over arrays of ONE common population
(usable test rows sorted by trajectory then time, each trajectory a contiguous block of consecutive steps).
Reuses ml.events.group_boolean_into_episodes and the existing lead-time definition unchanged. Reads no data itself.
"""

from typing import Dict, List, Sequence

import numpy as np
import pandas as pd

from ml.events import compute_lead_times_for_trajectory, group_boolean_into_episodes  # reused unchanged

DT = 0.01
HORIZON_S = 5.0
LEADS_S = (0.5, 1.0, 2.0, 3.0, 4.0, 5.0)
HEADLINE_LEADS_S = (2.0, 4.0)
MERGE_GAPS_S = (0.0, 1.0, 2.0)          # 0.0 is the primary (no merging)
B, SEED, PCT = 1000, 20261013, (2.5, 97.5)


def blocks(traj) -> tuple:
    """(starts, ends) of contiguous trajectory blocks; raises if a trajectory is split."""
    traj = np.asarray(traj)
    codes, uniq = pd.factorize(traj)
    change = np.flatnonzero(codes[1:] != codes[:-1]) + 1
    starts = np.concatenate([[0], change]).astype(int)
    ends = np.concatenate([change, [len(traj)]]).astype(int)
    if len(starts) != len(uniq):
        raise ValueError("rows of a trajectory are not contiguous")
    return starts, ends


def merge_episodes(eps: List[tuple], times: np.ndarray, gap_s: float) -> List[tuple]:
    """Merge (start_idx, end_idx) episodes whose gap (next start - previous end - DT) is <= gap_s."""
    if gap_s <= 0 or not eps:
        return list(eps)
    out = [list(eps[0])]
    for s, e in eps[1:]:
        if times[s] - times[out[-1][1]] - DT <= gap_s + 1e-9:
            out[-1][1] = e
        else:
            out.append([s, e])
    return [tuple(x) for x in out]


def false_alarm_counts(traj, times, label, unsafe, score, threshold: float, gap_s: float = 0.0) -> Dict[str, np.ndarray]:
    """Per-trajectory episode counts by class (TRUE / ONGOING / FALSE) and eligible seconds."""
    starts, ends = blocks(traj)
    pred = np.asarray(score, dtype=float) > float(threshold)
    label = np.asarray(label); unsafe = np.asarray(unsafe, dtype=bool); times = np.asarray(times, dtype=float)
    T = len(starts)
    out = {k: np.zeros(T, dtype=np.int64) for k in ("total", "true", "ongoing", "false")}
    span = np.zeros(T); rows = np.zeros(T)
    for t, (a, b) in enumerate(zip(starts, ends)):
        span[t] = times[b - 1] - times[a]
        rows[t] = (b - a) * DT
        eps = [(a + s, a + e) for _, _, s, e in group_boolean_into_episodes(times[a:b], pred[a:b])]
        for s, e in merge_episodes(eps, times, gap_s):
            out["total"][t] += 1
            if label[s] == 1:
                out["true"][t] += 1
            elif unsafe[s]:
                out["ongoing"][t] += 1
            else:
                out["false"][t] += 1
    out["span_s"] = span
    out["rows_s"] = rows
    return out


def event_table(traj, times, unsafe, score, threshold: float) -> pd.DataFrame:
    """One row per stall event in the usable rows: crossing time, existing-definition lead time, sustained-warning
    rows before the crossing, usable history rows before the crossing, first-event flag, left-censoring flag."""
    starts, ends = blocks(traj)
    traj = np.asarray(traj); times = np.asarray(times, dtype=float); unsafe = np.asarray(unsafe, dtype=bool)
    pred = np.asarray(score, dtype=float) > float(threshold)
    rows = []
    for a, b in zip(starts, ends):
        tt, uu, pp = times[a:b], unsafe[a:b], pred[a:b]
        res = compute_lead_times_for_trajectory(traj[a], tt, uu, tt, pp, HORIZON_S)
        runs = group_boolean_into_episodes(tt, uu)
        for k, (r, (_, _, si, _)) in enumerate(zip(res, runs)):
            sustained = 0
            j = si - 1
            while j >= 0 and pp[j]:
                sustained += 1
                j -= 1
            rows.append({"trajectory_id": traj[a], "crossing_time": r.crossing_time, "first_event": k == 0,
                         "left_censored": si == 0, "warned": r.warned, "lead_s": r.lead_time_s if r.warned else np.nan,
                         "sustained_rows": sustained, "history_rows": si})
    return pd.DataFrame(rows)


def coverage_per_trajectory(ev: pd.DataFrame, traj_order: Sequence, L: float, sustained: bool = False, first_only: bool = False):
    """Per-trajectory (covered, eligible) event counts at lead L, in the order of ``traj_order``."""
    need = int(round(L / DT))
    e = ev[ev["first_event"]] if first_only else ev
    elig = e["history_rows"] >= need
    cov = (e["sustained_rows"] >= need) if sustained else (e["lead_s"] >= L - 1e-9)
    idx = {t: i for i, t in enumerate(traj_order)}
    num = np.zeros(len(traj_order)); den = np.zeros(len(traj_order))
    for t, c, g in zip(e["trajectory_id"], cov & elig, elig):
        num[idx[t]] += bool(c); den[idx[t]] += bool(g)
    return num, den


def ratio_bootstrap(num, den, scale: float = 1.0, B_: int = B, seed: int = SEED) -> Dict[str, object]:
    """Trajectory bootstrap of sum(num)/sum(den) * scale; one draw of whole trajectories per replicate."""
    num = np.asarray(num, dtype=float); den = np.asarray(den, dtype=float)
    T = len(num)
    point = float(num.sum() / den.sum() * scale) if den.sum() > 0 else float("nan")
    rng = np.random.default_rng(seed)
    reps = np.full(B_, np.nan)
    for b in range(B_):
        c = np.bincount(rng.integers(0, T, size=T), minlength=T)
        d = (den * c).sum()
        if d > 0:
            reps[b] = (num * c).sum() / d * scale
    fin = reps[np.isfinite(reps)]
    lo, hi = (np.percentile(fin, PCT).tolist() if fin.size else (None, None))
    return {"point": point, "ci_lo": lo, "ci_hi": hi, "n_undefined_replicates": int(B_ - fin.size), "numerator": float(num.sum()), "denominator": float(den.sum())}
