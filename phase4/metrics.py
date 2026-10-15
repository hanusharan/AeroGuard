"""Row, event, false-warning and coverage metrics with a trajectory bootstrap (PROTOCOL.md section 3).

Event and lead-time definitions are the existing ones (``ml.events``); false-warning
episodes and coverage reuse the Items 37-39 functions unchanged. The bootstrap
resamples whole trajectories; each replicate is expressed as integer multiplicity
weights per trajectory so that PR-AUC can be recomputed in O(n) from one sort.
"""

import sys
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from . import BOOT_B, BOOT_SEED, DT, HORIZON_S

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments/items33_42/items37_39/src"))
import items37_39 as i3739  # noqa: E402  (reused unchanged)

PCT = (2.5, 97.5)


# ------------------------------------------------------------------------------------------- weighted PR-AUC / ECE
class SortedScores:
    """Scores sorted once (descending) with tie groups, for fast weighted average precision."""

    def __init__(self, y, score):
        y = np.asarray(y, dtype=float); score = np.asarray(score, dtype=float)
        self.order = np.argsort(-score, kind="mergesort")
        s = score[self.order]
        self.y = y[self.order]
        self.last_of_group = np.r_[np.flatnonzero(s[1:] != s[:-1]), len(s) - 1]

    def ap(self, w: Optional[np.ndarray] = None) -> float:
        """sklearn-equivalent average precision with optional row weights (already in original order)."""
        ww = np.ones_like(self.y) if w is None else np.asarray(w, dtype=float)[self.order]
        tp = np.cumsum(ww * self.y)[self.last_of_group]
        fp = np.cumsum(ww * (1 - self.y))[self.last_of_group]
        P = tp[-1]
        if P <= 0:
            return float("nan")
        with np.errstate(invalid="ignore", divide="ignore"):
            prec = np.where(tp + fp > 0, tp / (tp + fp), 0.0)
        rec = tp / P
        return float(np.sum(np.diff(np.r_[0.0, rec]) * prec))


def ece(y, p, n_bins: int = 10, w=None) -> float:
    y = np.asarray(y, dtype=float); p = np.asarray(p, dtype=float)
    w = np.ones_like(p) if w is None else np.asarray(w, dtype=float)
    b = np.clip((p * n_bins).astype(int), 0, n_bins - 1)
    tot = np.bincount(b, w, n_bins); sp = np.bincount(b, w * p, n_bins); sy = np.bincount(b, w * y, n_bins)
    nz = tot > 0
    return float(np.sum(np.abs(sp[nz] - sy[nz])) / tot.sum())


def row_metrics(y, score, prob=None) -> Dict[str, float]:
    y = np.asarray(y); out = {"n_rows": int(len(y)), "n_pos": int(y.sum()), "prevalence": float(y.mean()) if len(y) else float("nan")}
    both = 0 < y.sum() < len(y)
    out["pr_auc"] = float(average_precision_score(y, score)) if both else float("nan")
    out["roc_auc"] = float(roc_auc_score(y, score)) if both else float("nan")
    if prob is not None:
        out["brier"] = float(brier_score_loss(y, prob)); out["ece"] = ece(y, prob)
    return out


# ------------------------------------------------------------------------------------------- events
def traj_codes(traj) -> tuple:
    codes, uniq = pd.factorize(np.asarray(traj))
    return codes, uniq


def event_table(traj, times, unsafe, score, threshold) -> pd.DataFrame:
    return i3739.event_table(traj, times, unsafe, score, threshold)


def event_summary(ev: pd.DataFrame, dt_eff: float = DT) -> Dict[str, float]:
    n = len(ev); w = ev[ev["warned"]]
    lead = w["lead_s"].to_numpy()
    out = {"n_events": int(n), "n_warned": int(len(w)), "event_recall": float(len(w) / n) if n else float("nan"),
           "median_lead_s": float(np.median(lead)) if len(lead) else float("nan"),
           "mean_lead_s": float(np.mean(lead)) if len(lead) else float("nan"),
           "n_first_events": int(ev["first_event"].sum()) if n else 0}
    for L in (2.0, 4.0):
        elig = ev["history_rows"] >= int(round(L / dt_eff))
        cov = (ev["lead_s"] >= L - 1e-9) & elig
        out[f"coverage_ge_{int(L)}s"] = float(cov.sum() / elig.sum()) if elig.sum() else float("nan")
    return out


def false_warnings(traj, times, label, unsafe, score, threshold) -> Dict[str, float]:
    fa = i3739.false_alarm_counts(traj, times, label, unsafe, score, threshold)
    hours = fa["span_s"].sum() / 3600.0
    tot_true, tot_false = fa["true"].sum(), fa["false"].sum()
    return {"false_episodes": int(tot_false), "true_episodes": int(tot_true), "eligible_hours": float(hours),
            "false_per_hour": float(tot_false / hours) if hours > 0 else float("nan"),
            "episode_precision": float(tot_true / (tot_true + tot_false)) if (tot_true + tot_false) else float("nan"),
            "_per_traj_false": fa["false"], "_per_traj_span": fa["span_s"]}


# ------------------------------------------------------------------------------------------- bootstrap
def boot_weights(n_traj: int, B: int = BOOT_B, seed: int = BOOT_SEED):
    rng = np.random.default_rng(seed)
    for _ in range(B):
        yield np.bincount(rng.integers(0, n_traj, size=n_traj), minlength=n_traj).astype(float)


def ci(reps) -> list:
    r = np.asarray(reps, dtype=float); r = r[np.isfinite(r)]
    return np.percentile(r, PCT).tolist() if r.size else [None, None]


def weighted_median(x, w) -> float:
    x = np.asarray(x, dtype=float); w = np.asarray(w, dtype=float)
    m = w > 0
    if not m.any():
        return float("nan")
    o = np.argsort(x[m]); xs, cw = x[m][o], np.cumsum(w[m][o])
    half = cw[-1] / 2.0
    i = np.searchsorted(cw, half)
    if np.isclose(cw[i], half) and i + 1 < len(xs):
        return float((xs[i] + xs[i + 1]) / 2.0)
    return float(xs[i])


def evaluate(df: pd.DataFrame, score: np.ndarray, threshold: float, prob: Optional[np.ndarray] = None,
             boot: bool = True, B: int = BOOT_B, dt_eff: float = DT) -> Dict[str, object]:
    """All section-3 metrics for one model on one evaluation population (rows sorted by trajectory, time).
    ``dt_eff`` is the row spacing; false-warning rates (defined on consecutive 0.01 s rows) are computed only at full resolution."""
    full_resolution = abs(dt_eff - DT) < 1e-12
    y = df["future_stall_5s"].to_numpy().astype(int)
    traj = df["trajectory_id"].to_numpy(); times = df["time"].to_numpy(dtype=float); unsafe = df["is_unsafe"].to_numpy()
    out = {"row": row_metrics(y, score, prob)}
    ev = event_table(traj, times, unsafe, score, threshold)
    out["event"] = event_summary(ev, dt_eff)
    if full_resolution:
        fw = false_warnings(traj, times, y, unsafe, score, threshold)
        out["false_warning"] = {k: v for k, v in fw.items() if not k.startswith("_")}
    if not boot:
        return out
    codes, uniq = traj_codes(traj)
    T = len(uniq)
    ss = SortedScores(y, score)
    ev_code = pd.Index(uniq).get_indexer(ev["trajectory_id"]) if len(ev) else np.array([], dtype=int)
    warned = ev["warned"].to_numpy() if len(ev) else np.array([], dtype=bool)
    lead = ev["lead_s"].to_numpy() if len(ev) else np.array([])
    reps = {"pr_auc": [], "event_recall": [], "median_lead_s": []}
    if full_resolution:
        reps["false_per_hour"] = []
        pf, ps = fw["_per_traj_false"], fw["_per_traj_span"]
    for w_t in boot_weights(T, B):
        reps["pr_auc"].append(ss.ap(w_t[codes]))
        we = w_t[ev_code] if len(ev) else np.array([])
        reps["event_recall"].append((we * warned).sum() / we.sum() if we.sum() > 0 else np.nan)
        reps["median_lead_s"].append(weighted_median(lead[warned], we[warned]) if warned.any() else np.nan)
        if full_resolution:
            hrs = (w_t * ps).sum() / 3600.0
            reps["false_per_hour"].append((w_t * pf).sum() / hrs if hrs > 0 else np.nan)
    out["ci95"] = {k: ci(v) for k, v in reps.items()}
    out["n_trajectories"] = int(T)
    return out


def paired_diff_ci(df: pd.DataFrame, score_a, thr_a, score_b, thr_b, B: int = BOOT_B) -> Dict[str, object]:
    """Paired trajectory bootstrap of (A - B) for PR-AUC, event recall and median lead on the same rows."""
    y = df["future_stall_5s"].to_numpy().astype(int)
    traj = df["trajectory_id"].to_numpy(); times = df["time"].to_numpy(dtype=float); unsafe = df["is_unsafe"].to_numpy()
    codes, uniq = traj_codes(traj); T = len(uniq)
    sa, sb = SortedScores(y, score_a), SortedScores(y, score_b)
    eva, evb = event_table(traj, times, unsafe, score_a, thr_a), event_table(traj, times, unsafe, score_b, thr_b)

    def ev_parts(ev):
        return (pd.Index(uniq).get_indexer(ev["trajectory_id"]), ev["warned"].to_numpy(), ev["lead_s"].to_numpy())

    (ca, wa, la), (cb, wb, lb) = ev_parts(eva), ev_parts(evb)

    def stats(w_t):
        r = {"pr_auc": sa.ap(w_t[codes]) - sb.ap(w_t[codes])}
        ea, eb = w_t[ca], w_t[cb]
        r["event_recall"] = (ea * wa).sum() / ea.sum() - (eb * wb).sum() / eb.sum() if ea.sum() > 0 else np.nan
        r["median_lead_s"] = (weighted_median(la[wa], ea[wa]) - weighted_median(lb[wb], eb[wb])) if wa.any() and wb.any() else np.nan
        return r

    point = stats(np.ones(T))
    reps = {k: [] for k in point}
    for w_t in boot_weights(T, B):
        for k, v in stats(w_t).items():
            reps[k].append(v)
    return {k: {"diff": float(point[k]), "ci95": ci(reps[k])} for k in point}
