"""Inference-time input replacement for the FROZEN model (PROTOCOL.md section 10).

This is a perturbation of the frozen model's inputs. It is a separate analysis family
(``frozen_model_masking``) and does not measure the same quantity as retrained feature ablation: replaced
values can be out-of-distribution and inconsistent with the unchanged derived columns.

Columns are replaced, never dropped: the returned frame has exactly the requested feature columns in the
requested order. Derived columns are NOT recomputed after a replacement. The input frame is never modified.
"""

from typing import Dict, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from phase3.population import trajectory_blocks  # reused unchanged

from . import MASK_SEEDS

ANALYSIS_FAMILY = "frozen_model_masking"
MASK_SETS: Dict[str, tuple] = {
    "M-A": ("elevator", "throttle"),
    "M-B": ("elevator_change_1s",),
    "M-C": ("elevator", "throttle", "elevator_change_1s"),
}
METHODS = ("MS1", "MS2", "MS3")


class MaskingError(ValueError):
    """The requested masking is not allowed or not well defined."""


def apply_mask(df: pd.DataFrame, features: Sequence[str], mask_set: str, method: str, *,
               medians: Optional[Mapping[str, float]] = None, seed: Optional[int] = None) -> pd.DataFrame:
    """Return a copy of ``df[features]`` with the set's columns replaced.

    MS1 constant (training medians given in ``medians``); MS2 one global row permutation; MS3 a within-trajectory
    permutation (trajectories must be contiguous blocks, processed in order from one RNG stream). The same
    permutation is applied to every column of the set, so their joint is preserved."""
    if mask_set not in MASK_SETS:
        raise MaskingError(f"unknown mask set {mask_set!r}")
    if method not in METHODS:
        raise MaskingError(f"unknown masking method {method!r}")
    feats = list(features)
    cols = list(MASK_SETS[mask_set])
    absent = [c for c in feats if c not in df.columns]
    if absent:
        raise MaskingError(f"missing feature column(s): {absent}")
    notin = [c for c in cols if c not in feats]
    if notin:
        raise MaskingError(f"masked column(s) not among the model's features: {notin}")
    out = df[feats].copy()
    n = len(out)
    if method == "MS1":
        if medians is None or any(c not in medians or not np.isfinite(medians[c]) for c in cols):
            raise MaskingError("MS1 needs a finite training median for every masked column")
        for c in cols:
            out[c] = float(medians[c])
        return out
    if seed is None or seed not in MASK_SEEDS:
        raise MaskingError(f"permutation seed must be one of the pre-specified {MASK_SEEDS}")
    values = {c: df[c].to_numpy().copy() for c in cols}
    if method == "MS2":
        perm = np.random.default_rng(int(seed)).permutation(n)
        for c in cols:
            out[c] = values[c][perm]
        return out
    starts, ends, codes = trajectory_blocks(df["trajectory_id"].to_numpy())
    if len(starts) != len(pd.unique(df["trajectory_id"])):
        raise MaskingError("rows of a trajectory are not contiguous")
    rng = np.random.default_rng(int(seed))
    index = np.arange(n)
    for s, e in zip(starts, ends):
        index[s:e] = s + rng.permutation(e - s)
    for c in cols:
        out[c] = values[c][index]
    return out
