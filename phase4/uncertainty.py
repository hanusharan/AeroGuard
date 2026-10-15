"""Items 46-47: uncertainty scores, abstention and split conformal prediction (PROTOCOL.md sections 6-7)."""

from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.neighbors import NearestNeighbors

from . import BOOT_SEED

ABSTAIN_FRACTION = 0.05
CONFORMAL_ALPHA = 0.10
NOVELTY_REFERENCE_ROWS = 20_000
NOVELTY_K = 10


def u_amb(p: np.ndarray) -> np.ndarray:
    return p * (1.0 - p)


def u_ens(prob_by_seed: List[np.ndarray]) -> np.ndarray:
    return np.std(np.vstack(prob_by_seed), axis=0)


class Novelty:
    """Mean distance to the k nearest of a fixed sample of training rows, in standardised feature space."""

    def __init__(self, train_X: np.ndarray, seed: int = BOOT_SEED, n_ref: int = NOVELTY_REFERENCE_ROWS, k: int = NOVELTY_K):
        self.mu = train_X.mean(axis=0); self.sd = train_X.std(axis=0); self.sd[self.sd == 0] = 1.0
        idx = np.random.default_rng(seed).choice(len(train_X), size=min(n_ref, len(train_X)), replace=False)
        self.k = k
        self.nn = NearestNeighbors(n_neighbors=k, n_jobs=-1).fit(((train_X[idx] - self.mu) / self.sd).astype(np.float32))

    def __call__(self, X: np.ndarray, batch: int = 200_000) -> np.ndarray:
        out = np.empty(len(X))
        for a in range(0, len(X), batch):
            d, _ = self.nn.kneighbors(((X[a:a + batch] - self.mu) / self.sd).astype(np.float32))
            out[a:a + batch] = d.mean(axis=1)
        return out


def abstain_threshold(u_val: np.ndarray, frac: float = ABSTAIN_FRACTION) -> float:
    """tau such that a fraction ``frac`` of validation rows have U > tau."""
    return float(np.quantile(u_val, 1.0 - frac))


def risk_coverage(err: np.ndarray, u: np.ndarray, n_points: int = 101) -> Dict[str, object]:
    """Error rate among the most-certain rows as coverage grows; AURC is the mean selective risk."""
    o = np.argsort(u, kind="mergesort")
    cum = np.cumsum(err[o]) / np.arange(1, len(err) + 1)
    cov = np.linspace(0.01, 1.0, n_points)
    pts = cum[np.clip((cov * len(err)).astype(int) - 1, 0, len(err) - 1)]
    return {"coverage": cov.tolist(), "selective_risk": pts.tolist(), "aurc": float(np.mean(cum))}


def abstention_report(df: pd.DataFrame, pred: np.ndarray, u: np.ndarray, tau: float, events: pd.DataFrame) -> Dict[str, object]:
    y = df["future_stall_5s"].to_numpy().astype(int)
    err = (pred.astype(int) != y).astype(float)
    ab = u > tau
    out = {"abstention_rate": float(ab.mean()), "error_all": float(err.mean()),
           "error_retained": float(err[~ab].mean()) if (~ab).any() else float("nan"),
           "error_abstained": float(err[ab].mean()) if ab.any() else float("nan"),
           "error_auroc": float(roc_auc_score(err, u)) if 0 < err.sum() < len(err) else float("nan")}
    rc = risk_coverage(err, u); out["aurc"] = rc["aurc"]; out["risk_coverage"] = rc
    # event level: missed events with any abstention in the 5 s before the crossing; warned events whose onset row abstained
    traj = df["trajectory_id"].to_numpy(); times = df["time"].to_numpy()
    starts = {}
    codes, uniq = pd.factorize(traj)
    bounds = np.r_[0, np.flatnonzero(codes[1:] != codes[:-1]) + 1, len(traj)]
    for i, t in enumerate(uniq):
        starts[t] = (bounds[i], bounds[i + 1])
    miss_flag, warn_onset_flag = [], []
    for r in events.itertuples():
        a, b = starts[r.trajectory_id]
        tt = times[a:b]
        win = (tt >= r.crossing_time - 5.0) & (tt < r.crossing_time)
        if not r.warned:
            miss_flag.append(bool(ab[a:b][win].any()))
        else:
            onset = r.crossing_time - r.lead_s
            j = a + int(np.argmin(np.abs(tt - onset)))
            warn_onset_flag.append(bool(ab[j]))
    out["missed_events"] = len(miss_flag)
    out["missed_with_abstention_before_crossing"] = float(np.mean(miss_flag)) if miss_flag else float("nan")
    out["warned_events"] = len(warn_onset_flag)
    out["warned_onset_abstained"] = float(np.mean(warn_onset_flag)) if warn_onset_flag else float("nan")
    return out


def conformal_qhat(p_val: np.ndarray, y_val: np.ndarray, alpha: float = CONFORMAL_ALPHA) -> float:
    s = 1.0 - np.where(y_val == 1, p_val, 1.0 - p_val)
    n = len(s)
    return float(np.quantile(s, min(1.0, np.ceil((n + 1) * (1 - alpha)) / n), method="higher"))


def conformal_report(p: np.ndarray, y: np.ndarray, qhat: float) -> Dict[str, float]:
    inc1 = (1.0 - p) <= qhat          # label 1 in the set
    inc0 = p <= qhat                  # label 0 in the set  (1 - (1 - p))
    covered = np.where(y == 1, inc1, inc0)
    return {"coverage": float(covered.mean()), "coverage_pos": float(covered[y == 1].mean()) if (y == 1).any() else float("nan"),
            "coverage_neg": float(covered[y == 0].mean()) if (y == 0).any() else float("nan"),
            "avg_set_size": float((inc1.astype(int) + inc0.astype(int)).mean()),
            "empty_set_rate": float((~inc1 & ~inc0).mean())}
