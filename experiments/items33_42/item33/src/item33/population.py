"""Common evaluation population, row identity, split roles and data-structure summaries
(PROTOCOL.md sections 6, 7 and 9.3).

Reuses ``phase3.population`` unchanged for hashing, row keys, the usable mask, count reconciliation and
the trajectory-overlap check. Importing this module reads no data.
"""

import hashlib
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from phase3.population import (  # noqa: F401  (re-exported; reused unchanged)
    AVAILABLE_COL, DataIntegrityError, GateViolation, KeyMismatchError, MissingPredictionError, PredictionSet, REPORTED_COUNTS, RowKeys,
    SplitTable, TARGET_COL,
    assert_common_population, assert_consecutive_steps, assert_no_trajectory_overlap, assert_same_keys, compare_counts,
    count_events, eligible_time, make_prediction_set, require_split, row_keys, sha256_file, summarize_population,
    trajectory_blocks, usable_mask, verify_file_hashes,
)

SPLITS = ("train", "val", "test")
PANEL_SUBDIR = "ml_temporal_v03"


def panel_relpath(split: str) -> str:
    if split not in SPLITS:
        raise ValueError(f"unknown split {split!r}")
    return f"{PANEL_SUBDIR}/temporal_{split}.parquet"


def load_split(data_dir, split: str, columns: Sequence[str], allowed_splits: Iterable[str],
               reader: Optional[Callable[..., pd.DataFrame]] = None) -> SplitTable:
    """Read ONLY ``columns`` of ONE split. ``allowed_splits`` is the gate's whitelist: a split outside it
    raises before any file is opened or any reader is called. ``reader`` is injectable for synthetic tests."""
    if split not in SPLITS:
        raise ValueError(f"unknown split {split!r}")
    if split not in tuple(allowed_splits):
        raise GateViolation(f"split {split!r} is not allowed at this gate (allowed: {tuple(allowed_splits)})")
    from pathlib import Path

    path = Path(data_dir) / panel_relpath(split)
    cols = list(dict.fromkeys(columns))
    if reader is None:
        if not path.is_file():
            raise DataIntegrityError(f"missing panel file {path}")
        reader = pd.read_parquet
    df = reader(path, columns=cols)
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise DataIntegrityError(f"{split}: missing column(s) {missing}")
    return SplitTable(split=split, df=df)


def key_hash(keys: RowKeys) -> str:
    """Canonical SHA-256 of an ordered key set: for each trajectory block, the id, then its steps as
    little-endian int64. Order-sensitive, so reordering changes the hash."""
    h = hashlib.sha256()
    traj, step = keys.traj, keys.step
    n = len(step)
    if n == 0:
        return h.hexdigest()
    codes, _ = pd.factorize(traj)
    change = np.flatnonzero(codes[1:] != codes[:-1]) + 1
    starts = np.concatenate([[0], change])
    ends = np.concatenate([change, [n]])
    for s, e in zip(starts, ends):
        h.update(f"{traj[s]}\x00".encode())
        h.update(np.ascontiguousarray(step[s:e], dtype="<i8").tobytes())
    return h.hexdigest()


def assert_identical_populations(keys_by_condition: Mapping[str, RowKeys]) -> str:
    """Every condition must carry exactly the same keys in the same order. Returns the common key hash."""
    items = list(keys_by_condition.items())
    if not items:
        raise ValueError("no populations given")
    ref_name, ref = items[0]
    for name, k in items[1:]:
        assert_same_keys(ref, k, label=f"{name} vs {ref_name}")
    return key_hash(ref)


def assert_labels_alignment(keys: RowKeys, y) -> None:
    if len(np.asarray(y)) != len(keys):
        raise KeyMismatchError("labels and keys differ in length")


def regime_of_trajectories(traj_ids: Sequence, metadata: pd.DataFrame) -> Dict[object, str]:
    """Regime (``generation_mode``) per trajectory from the tracked metadata table. Every trajectory must
    appear exactly once; an unknown or duplicated id stops the analysis."""
    if metadata["trajectory_id"].duplicated().any():
        raise DataIntegrityError("metadata has duplicated trajectory ids")
    mapping = dict(zip(metadata["trajectory_id"], metadata["generation_mode"]))
    uniq = list(dict.fromkeys(np.asarray(traj_ids).tolist()))
    missing = [t for t in uniq if t not in mapping]
    if missing:
        raise DataIntegrityError(f"{len(missing)} trajectory id(s) absent from the metadata, e.g. {missing[:3]}")
    return {t: mapping[t] for t in uniq}


def stratum_sizes(regime_by_traj: Mapping[object, str]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for r in regime_by_traj.values():
        out[r] = out.get(r, 0) + 1
    if not out or any(v <= 0 for v in out.values()):
        raise DataIntegrityError("empty regime stratum")
    return dict(sorted(out.items()))


def column_constancy(df: pd.DataFrame, column: str, tol: float = 1e-12) -> Dict[str, object]:
    """Descriptive structure of a column within trajectories (used at G33-1 for throttle and trim
    questions): how many trajectories hold it constant, and how many distinct per-trajectory constants exist."""
    g = df.groupby("trajectory_id", sort=False)[column]
    spread = (g.max() - g.min()).to_numpy(dtype=float)
    first = g.first().to_numpy(dtype=float)
    constant = spread <= tol
    return {
        "column": column, "n_trajectories": int(len(spread)), "n_constant_within_trajectory": int(constant.sum()),
        "fraction_constant": float(constant.mean()) if len(spread) else float("nan"),
        "n_distinct_constant_values": int(len(np.unique(np.round(first[constant], 9)))) if constant.any() else 0,
    }


def training_medians(df: pd.DataFrame, columns: Sequence[str], mask) -> Dict[str, float]:
    """Median of each column over the TRAINING usable rows (used by masking method MS1)."""
    sub = df.loc[np.asarray(mask, dtype=bool), list(columns)]
    if sub.empty or sub.isna().any().any():
        raise DataIntegrityError("training medians need non-empty, NaN-free training usable rows")
    return {c: float(sub[c].median()) for c in columns}
