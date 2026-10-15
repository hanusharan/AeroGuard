"""Paired trajectory bootstrap (PROTOCOL.md section 9.1-9.3).

Unit: the trajectory. One draw per replicate is shared by every (condition, seed) method, so every
difference is paired. Rows are never resampled independently. Seed-averaged contrasts are the mean over
seeds, within a replicate, of the paired difference. Undefined replicates are counted, never dropped silently.
Stratified resampling (sensitivity SR) resamples within each regime stratum with the stratum counts fixed.
"""

from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score  # noqa: F401  (verification path)

from phase3.analysis import draw_rows, threshold_free_metrics  # reused unchanged
from phase3.population import trajectory_blocks  # reused unchanged

from . import BONFERRONI_INTERVAL_PCT, BOOTSTRAP_B, BOOTSTRAP_INTERVAL_PCT, BOOTSTRAP_SEED

METRICS = ("pr_auc", "roc_auc")


def method_key(condition: str, seed: int) -> str:
    return f"{condition}|{int(seed)}"


def percentile_interval(values: np.ndarray, pct: Tuple[float, float] = BOOTSTRAP_INTERVAL_PCT):
    """(lo, hi, n_undefined). Non-finite replicates are counted and excluded, never hidden."""
    v = np.asarray(values, dtype=float)
    finite = v[np.isfinite(v)]
    n_undefined = int(v.size - finite.size)
    if finite.size == 0:
        return None, None, n_undefined
    lo, hi = np.percentile(finite, pct)
    return float(lo), float(hi), n_undefined


def _draw_plan(traj_ids, strata: Optional[Mapping[object, str]]):
    traj_ids = np.asarray(traj_ids)
    starts, ends, codes = trajectory_blocks(traj_ids)
    uniques = pd.unique(traj_ids)
    n_traj = len(starts)
    if n_traj != len(uniques):
        raise ValueError("rows of a trajectory are not contiguous")
    groups = None
    if strata is not None:
        labels = []
        for t in uniques:
            if t not in strata:
                raise ValueError(f"trajectory {t!r} has no stratum")
            labels.append(strata[t])
        labels = np.asarray(labels)
        groups = []
        for name in sorted(set(labels.tolist())):
            members = np.flatnonzero(labels == name)
            if members.size == 0:
                raise ValueError(f"empty stratum {name!r}")
            groups.append(members)
    return starts, ends, n_traj, groups


def _draw(rng: np.random.Generator, n_traj: int, groups) -> np.ndarray:
    if groups is None:
        return rng.integers(0, n_traj, size=n_traj)
    parts = [members[rng.integers(0, members.size, size=members.size)] for members in groups]
    return np.concatenate(parts)


class _FastCurves:
    """Pre-sorted weighted precision-recall / ROC curves for the trajectory bootstrap.

    A bootstrap replicate repeats whole trajectories, which is the same as giving every row of trajectory ``t`` the weight
    ``counts[t]`` (the number of times it was drawn). Sorting the scores once and taking weighted cumulative sums at the
    ends of the tied-score groups gives exactly the curve scikit-learn builds from the repeated rows (the cumulative
    counts are exact integers), without re-sorting 538,034 rows 100,000 times. ``verify_fast_replicates`` checks the
    equivalence against scikit-learn on the first replicates of every run.
    """

    def __init__(self, y: np.ndarray, score: np.ndarray, codes: np.ndarray):
        order = np.argsort(-np.asarray(score, dtype=float), kind="stable")
        s = np.asarray(score, dtype=float)[order]
        self.y = np.asarray(y, dtype=np.float64)[order]
        self.neg = 1.0 - self.y
        self.codes = np.asarray(codes)[order].astype(np.int32)
        change = np.flatnonzero(s[1:] != s[:-1])
        self.ends = np.concatenate([change, [len(s) - 1]]).astype(np.int64)

    def curves(self, counts: np.ndarray):
        w = counts[self.codes].astype(np.float64)
        tp = np.cumsum(w * self.y)[self.ends]
        fp = np.cumsum(w * self.neg)[self.ends]
        return tp, fp

    @staticmethod
    def ap(tp: np.ndarray, fp: np.ndarray) -> float:
        p_total = tp[-1]
        if p_total <= 0:
            return float("nan")
        den = tp + fp
        # a tied-score group made only of undrawn trajectories has zero weight: its recall step is 0, so its precision is irrelevant
        precision = np.divide(tp, den, out=np.zeros_like(tp), where=den > 0)
        recall = tp / p_total
        return float(np.sum(np.diff(np.concatenate([[0.0], recall])) * precision))

    @staticmethod
    def roc_auc(tp: np.ndarray, fp: np.ndarray) -> float:
        p_total, n_total = tp[-1], fp[-1]
        if p_total <= 0 or n_total <= 0:
            return float("nan")
        return float(np.trapezoid(np.concatenate([[0.0], tp / p_total]), np.concatenate([[0.0], fp / n_total])))


def _check_inputs(traj_ids, y, scores, metrics):
    y = np.asarray(y).astype(int)
    for nm, s in scores.items():
        if len(s) != len(y):
            raise ValueError(f"scores[{nm}] and labels differ in length")
    if len(np.asarray(traj_ids)) != len(y):
        raise ValueError("trajectory ids and labels differ in length")
    unknown = [m for m in metrics if m not in METRICS]
    if unknown:
        raise ValueError(f"unknown metric(s) {unknown}")
    return y


def bootstrap_replicates(traj_ids, y, scores: Mapping[str, np.ndarray], B: int, seed: int,
                         strata: Optional[Mapping[object, str]] = None, metrics: Sequence[str] = ("pr_auc",)) -> Dict[str, np.ndarray]:
    """Replicate arrays ``reps["<method>|<metric>"]`` of length B. One shared draw per replicate (same RNG stream as
    before: ``rng.integers`` per replicate, or per stratum when stratified)."""
    y = _check_inputs(traj_ids, y, scores, metrics)
    starts, ends, n_traj, groups = _draw_plan(traj_ids, strata)
    _, _, codes = trajectory_blocks(np.asarray(traj_ids))
    names = list(scores)
    reps = {f"{nm}|{mt}": np.full(B, np.nan) for nm in names for mt in metrics}
    fast = {nm: _FastCurves(y, scores[nm], codes) for nm in names}
    rng = np.random.default_rng(seed)
    for b in range(B):
        draw = _draw(rng, n_traj, groups)
        counts = np.bincount(draw, minlength=n_traj)
        for nm in names:
            tp, fp = fast[nm].curves(counts)
            if "pr_auc" in metrics:
                reps[f"{nm}|pr_auc"][b] = _FastCurves.ap(tp, fp)
            if "roc_auc" in metrics:
                reps[f"{nm}|roc_auc"][b] = _FastCurves.roc_auc(tp, fp)
    return reps


def verify_fast_replicates(traj_ids, y, scores: Mapping[str, np.ndarray], seed: int, n: int = 2, tol: float = 1e-10,
                           strata: Optional[Mapping[object, str]] = None) -> Dict[str, object]:
    """Recompute the first ``n`` replicates with scikit-learn on the explicitly repeated rows and compare with the
    pre-sorted weighted computation. Raises if any difference exceeds ``tol``."""
    y = _check_inputs(traj_ids, y, scores, ("pr_auc", "roc_auc"))
    starts, ends, n_traj, groups = _draw_plan(traj_ids, strata)
    fast = bootstrap_replicates(traj_ids, y, scores, B=n, seed=seed, strata=strata, metrics=("pr_auc", "roc_auc"))
    rng = np.random.default_rng(seed)
    worst = 0.0
    for b in range(n):
        draw = _draw(rng, n_traj, groups)
        rows = draw_rows(draw, starts, ends)
        yb = y[rows]
        for nm in scores:
            sb = np.asarray(scores[nm], dtype=float)[rows]
            ref_ap = average_precision_score(yb, sb) if yb.sum() > 0 else float("nan")
            ref_roc = roc_auc_score(yb, sb) if 0 < yb.sum() < len(yb) else float("nan")
            for key, ref in ((f"{nm}|pr_auc", ref_ap), (f"{nm}|roc_auc", ref_roc)):
                got = fast[key][b]
                if np.isnan(ref) != np.isnan(got):
                    raise AssertionError(f"fast path disagrees on definedness for {key}, replicate {b}")
                if not np.isnan(ref):
                    worst = max(worst, abs(got - ref))
    if worst > tol:
        raise AssertionError(f"fast bootstrap path differs from scikit-learn by {worst:.3e} (> {tol:.1e})")
    return {"replicates_checked": int(n), "n_methods": len(scores), "max_abs_difference": worst, "tolerance": tol}


def event_bootstrap(traj_ids, y, scores: Mapping[str, np.ndarray], events: Mapping[str, Mapping[object, list]], B: int, seed: int) -> Dict[str, object]:
    """Per-method bootstrap of PR-AUC, ROC-AUC, event recall and median lead time with the same trajectory draw
    (same RNG stream as ``phase3.analysis.trajectory_bootstrap``, whose event logic this reproduces)."""
    y = _check_inputs(traj_ids, y, scores, ("pr_auc", "roc_auc"))
    traj_ids = np.asarray(traj_ids)
    starts, ends, codes = trajectory_blocks(traj_ids)
    uniques = pd.unique(traj_ids)
    n_traj = len(starts)
    if n_traj != len(uniques):
        raise ValueError("rows of a trajectory are not contiguous")
    names = list(scores)
    prep = {}
    for nm in names:
        n_ev = np.zeros(n_traj, dtype=np.int64); n_w = np.zeros(n_traj, dtype=np.int64); leads = []
        for t, tid in enumerate(uniques):
            lst = events[nm].get(tid, [])
            n_ev[t] = len(lst)
            w = [lead for warned, lead in lst if warned]
            n_w[t] = len(w)
            leads.append(np.asarray(w, dtype=float))
        prep[nm] = (n_ev, n_w, leads)
    fast = {nm: _FastCurves(y, scores[nm], codes) for nm in names}
    keys = ("pr_auc", "roc_auc", "event_recall", "median_lead_s")
    reps = {f"{nm}|{k}": np.full(B, np.nan) for nm in names for k in keys}
    rng = np.random.default_rng(seed)
    for b in range(B):
        draw = rng.integers(0, n_traj, size=n_traj)
        counts = np.bincount(draw, minlength=n_traj)
        for nm in names:
            tp, fp = fast[nm].curves(counts)
            reps[f"{nm}|pr_auc"][b] = _FastCurves.ap(tp, fp)
            reps[f"{nm}|roc_auc"][b] = _FastCurves.roc_auc(tp, fp)
            n_ev, n_w, leads = prep[nm]
            tot, warned = int((n_ev * counts).sum()), int((n_w * counts).sum())
            if tot > 0:
                reps[f"{nm}|event_recall"][b] = warned / tot
            if warned > 0:
                reps[f"{nm}|median_lead_s"][b] = float(np.median(np.concatenate([leads[t] for t in draw])))
    per_method = {}
    for nm in names:
        pt = threshold_free_metrics(y, scores[nm])
        n_ev, n_w, leads = prep[nm]
        all_leads = np.concatenate(leads) if leads else np.zeros(0)
        point = {"pr_auc": pt["pr_auc"], "roc_auc": pt["roc_auc"],
                 "event_recall": float(n_w.sum() / n_ev.sum()) if n_ev.sum() > 0 else float("nan"),
                 "median_lead_s": float(np.median(all_leads)) if all_leads.size else float("nan")}
        for k in keys:
            lo, hi, nu = percentile_interval(reps[f"{nm}|{k}"])
            per_method[f"{nm}|{k}"] = {"point": point[k], "ci_lo": lo, "ci_hi": hi, "n_undefined_replicates": nu}
    return {"config": {"unit": "trajectory", "B": int(B), "seed": int(seed), "pairing": "one trajectory draw per replicate, shared by every method"},
            "per_method": per_method}


def point_estimates(y, scores: Mapping[str, np.ndarray], metrics: Sequence[str] = ("pr_auc",)) -> Dict[str, float]:
    out = {}
    for nm, s in scores.items():
        m = threshold_free_metrics(y, s)
        for mt in metrics:
            out[f"{nm}|{mt}"] = m[mt]
    return out


def contrast_summary(reference: str, comparison: str, seeds: Sequence[int], point: Mapping[str, float],
                     reps: Mapping[str, np.ndarray], metric: str = "pr_auc", bonferroni: bool = False) -> Dict[str, object]:
    """Per-seed paired deltas, their mean/median/spread (descriptive), and the trajectory-bootstrap interval for the
    seed-averaged delta. The across-seed spread and the bootstrap interval are returned in separate blocks and are
    never combined."""
    seeds = list(seeds)
    per_seed, d_reps = {}, []
    for s in seeds:
        a, b = method_key(reference, s), method_key(comparison, s)
        d = reps[f"{a}|{metric}"] - reps[f"{b}|{metric}"]
        d_reps.append(d)
        lo, hi, nu = percentile_interval(d)
        per_seed[int(s)] = {
            "point": float(point[f"{a}|{metric}"] - point[f"{b}|{metric}"]), "ci_lo": lo, "ci_hi": hi, "n_undefined_replicates": nu,
        }
    stack = np.vstack(d_reps)                      # (n_seeds, B)
    mean_rep = stack.mean(axis=0)                  # NaN if any seed's replicate is undefined
    deltas = np.array([per_seed[int(s)]["point"] for s in seeds], dtype=float)
    lo, hi, nu = percentile_interval(mean_rep)
    out = {
        "reference": reference, "comparison": comparison, "metric": metric, "seeds": [int(s) for s in seeds],
        "per_seed": per_seed,
        "seed_estimates": {
            "mean": float(deltas.mean()), "median": float(np.median(deltas)), "min": float(deltas.min()), "max": float(deltas.max()),
            "sd_ddof1": float(deltas.std(ddof=1)) if len(deltas) > 1 else None,
            "sign_consistent": bool(np.all(deltas > 0) or np.all(deltas < 0)),
            "note": "descriptive only; no interval across seeds is computed",
        },
        "bootstrap_seed_mean": {
            "point": float(deltas.mean()), "ci_lo": lo, "ci_hi": hi, "n_undefined_replicates": nu, "pct": list(BOOTSTRAP_INTERVAL_PCT),
            "includes_zero": (lo is not None and lo <= 0.0 <= hi),
            "note": "test-trajectory sampling uncertainty conditional on the fitted models; not combined with seed variability",
        },
    }
    if bonferroni:
        alo, ahi, anu = percentile_interval(mean_rep, BONFERRONI_INTERVAL_PCT)
        out["bootstrap_seed_mean_bonferroni"] = {
            "ci_lo": alo, "ci_hi": ahi, "n_undefined_replicates": anu, "pct": list(BONFERRONI_INTERVAL_PCT), "m": 2,
            "includes_zero": (alo is not None and alo <= 0.0 <= ahi),
        }
    return out


def run_protocol_bootstrap(traj_ids, y, scores, strata=None, metrics=("pr_auc",)):
    """The approved configuration only: B = 1000, seed 20261013. No B / seed arguments."""
    return bootstrap_replicates(traj_ids, y, scores, B=BOOTSTRAP_B, seed=BOOTSTRAP_SEED, strata=strata, metrics=metrics)
