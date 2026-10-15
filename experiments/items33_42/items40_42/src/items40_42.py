"""Items 40-42: matched operating points, paired ratio bootstrap, conclusion checks.

Implements experiments/items33_42/items40_42/PROTOCOL.md. Pure functions over arrays of one population (rows sorted by
trajectory then time, each trajectory a contiguous block). Reads no data itself.
"""

import re
from typing import Dict, Iterable, List, Sequence

import numpy as np

B, SEED, PCT = 1000, 20261013, (2.5, 97.5)
TARGET_RATES = (10.0, 20.0, 40.0)                    # validation false episodes per simulated hour (grid, not acceptable rates)
QUANTILE_LEVELS = np.round(np.linspace(0.5, 1.0, 1001), 4)


def first_rows(traj) -> np.ndarray:
    """True on the first row of each trajectory block."""
    traj = np.asarray(traj)
    f = np.ones(len(traj), dtype=bool)
    f[1:] = traj[1:] != traj[:-1]
    return f


def false_episode_starts(first, label, unsafe, pred) -> np.ndarray:
    """Rows where a FALSE warning episode starts (Items 37-39 primary definition, no merging): an episode starts where
    pred is on and either the previous row of the same trajectory is off or this is the trajectory's first row; it is
    FALSE if its first row has label 0 and is not unsafe."""
    pred = np.asarray(pred, dtype=bool)
    prev = np.zeros_like(pred)
    prev[1:] = pred[:-1]
    prev[first] = False
    return pred & ~prev & (np.asarray(label) == 0) & ~np.asarray(unsafe, dtype=bool)


def matched_threshold(val_score, val_first, val_label, val_unsafe, val_hours: float, target_rate: float) -> Dict[str, float]:
    """Validation-only threshold rule: the first (lowest) candidate, among validation score quantiles at QUANTILE_LEVELS,
    whose validation FALSE-episode rate is <= target_rate. Receives validation arrays only."""
    s = np.asarray(val_score, dtype=float)
    cands = np.quantile(s, QUANTILE_LEVELS)
    for q, thr in zip(QUANTILE_LEVELS, cands):
        n = int(false_episode_starts(val_first, val_label, val_unsafe, s > thr).sum())
        if n / val_hours <= target_rate:
            return {"threshold": float(thr), "quantile_level": float(q), "val_false_episodes": n, "val_rate": n / val_hours}
    raise AssertionError("unreachable: the maximum score always gives zero warnings")


def draw_counts(T: int, B_: int = B, seed: int = SEED) -> np.ndarray:
    """B x T multiplicity matrix of whole-trajectory resampling; identical draws to items37_39.ratio_bootstrap."""
    rng = np.random.default_rng(seed)
    return np.stack([np.bincount(rng.integers(0, T, size=T), minlength=T) for _ in range(B_)])


def ratio_reps(num, den, C, scale: float = 1.0) -> np.ndarray:
    d = C @ np.asarray(den, dtype=float)
    n = C @ np.asarray(num, dtype=float)
    out = np.full(len(d), np.nan)
    ok = d > 0
    out[ok] = n[ok] / d[ok] * scale
    return out


def interval(point: float, reps: np.ndarray) -> Dict[str, object]:
    fin = reps[np.isfinite(reps)]
    lo, hi = (np.percentile(fin, PCT).tolist() if fin.size else (None, None))
    return {"point": float(point), "ci_lo": lo, "ci_hi": hi, "n_undefined_replicates": int(len(reps) - fin.size),
            "includes_zero": None if lo is None else bool(lo <= 0 <= hi)}


NEGATION = re.compile(r"\b(not|no|never|nothing|neither|nor|without|cannot|isn't|aren't|doesn't|don't|none|only|"
                      r"unlike|rather than|instead of|avoid|forbidden|excluded?|limitation)\b", re.I)
TERMS = ("blind", "independent", "confirm", "real aircraft", "real-aircraft", "operational", "equivalen", "negligible",
         "caus", "prove", "significan")


def wording_scan(lines: Iterable[str]) -> List[Dict[str, object]]:
    """Lines containing a watched term; flagged when the line has no negation or qualification word."""
    out = []
    for i, line in enumerate(lines, 1):
        low = line.lower()
        hit = [t for t in TERMS if t in low]
        if hit:
            out.append({"line_no": i, "terms": hit, "flag": not NEGATION.search(line), "text": line.strip()[:300]})
    return out


def trapezoid_pr_auc(y, s) -> float:
    from sklearn.metrics import auc, precision_recall_curve
    p, r, _ = precision_recall_curve(np.asarray(y).astype(int), np.asarray(s, dtype=float))
    return float(auc(r, p))
