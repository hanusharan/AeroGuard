"""Paired trajectory bootstrap (PROTOCOL.md section 9.1-9.3).

Unit: the trajectory. One draw per replicate is shared by every (condition, seed) method, so every
difference is paired. Rows are never resampled independently. Seed-averaged contrasts are the mean over
seeds, within a replicate, of the paired difference. Undefined replicates are counted, never dropped silently.
Stratified resampling (sensitivity SR) resamples within each regime stratum with the stratum counts fixed.
"""

from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

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


def bootstrap_replicates(traj_ids, y, scores: Mapping[str, np.ndarray], B: int, seed: int,
                         strata: Optional[Mapping[object, str]] = None, metrics: Sequence[str] = ("pr_auc",)) -> Dict[str, np.ndarray]:
    """Replicate arrays ``reps["<method>|<metric>"]`` of length B. One shared draw per replicate."""
    y = np.asarray(y).astype(int)
    for nm, s in scores.items():
        if len(s) != len(y):
            raise ValueError(f"scores[{nm}] and labels differ in length")
    if len(np.asarray(traj_ids)) != len(y):
        raise ValueError("trajectory ids and labels differ in length")
    unknown = [m for m in metrics if m not in METRICS]
    if unknown:
        raise ValueError(f"unknown metric(s) {unknown}")
    starts, ends, n_traj, groups = _draw_plan(traj_ids, strata)
    names = list(scores)
    reps = {f"{nm}|{mt}": np.full(B, np.nan) for nm in names for mt in metrics}
    rng = np.random.default_rng(seed)
    arrays = {nm: np.asarray(scores[nm], dtype=float) for nm in names}
    for b in range(B):
        draw = _draw(rng, n_traj, groups)
        rows = draw_rows(draw, starts, ends)
        yb = y[rows]
        n_pos = int(yb.sum())
        for nm in names:
            sb = arrays[nm][rows]
            if "pr_auc" in metrics and n_pos > 0:
                reps[f"{nm}|pr_auc"][b] = average_precision_score(yb, sb)
            if "roc_auc" in metrics and 0 < n_pos < len(yb):
                reps[f"{nm}|roc_auc"][b] = roc_auc_score(yb, sb)
    return reps


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
