"""Item 29: the common evaluation population, row identity and integrity checks.

Why this module exists instead of reusing ``ml.temporal_data_v03.load_temporal_splits``:
that function loads all three splits at once and rebuilds the cached panels if they
are missing. Phase 3 needs (a) train-only access at G4 / G6, (b) read-only data use,
(c) explicit column lists and (d) row keys that make silent reordering impossible.

The population mask itself is the EXISTING
``ml.temporal_features.usable_mask_for_window`` (label available AND a full 1.0 s
history window), reused unchanged.

Importing this module reads no data.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from ml import temporal_config as tcfg
from ml.events import group_boolean_into_episodes  # reused unchanged
from ml.temporal_features import usable_mask_for_window  # reused unchanged

from . import (
    BASELINE_MANIFEST_RELPATH,
    DT,
    FROZEN_MODEL_RELPATH,
    PROTOCOL_SHA256,
    WINDOW_S,
)

SPLITS = ("train", "val", "test")
TARGET_COL = tcfg.TARGET_COL                      # "future_stall_5s"
AVAILABLE_COL = tcfg.TARGET_AVAILABLE_COL         # "future_stall_5s_available"
WINDOW_COLUMNS = list(tcfg.temporal_feature_columns(WINDOW_S))  # the ten 1.0 s columns
KEY_COLUMNS = ["trajectory_id", "time"]

# Counts reported by earlier records (PROTOCOL.md 8.1). They are re-derived at G5; a
# mismatch stops the work. They are NOT results of this protocol.
REPORTED_COUNTS = {
    "dataset_rows": 5_340_865,
    "dataset_trajectories": 3_150,
    "trajectories_train": 2_205,
    "trajectories_val": 472,
    "trajectories_test": 473,
    "panel_rows_train": 3_749_572,
    "panel_rows_val": 771_995,
    "panel_rows_test": 819_298,
    "usable_rows_train": 2_443_881,
    "usable_rows_val": 491_322,
    "usable_rows_test": 538_034,
    "test_trajectories_with_usable_rows": 456,
    "test_positive_rows": 46_169,
    "test_negative_rows": 491_865,
    "test_events": 76,
    "test_first_events": 57,
    "test_later_events": 19,
    "test_trajectories_with_events": 57,
    "test_trajectories_with_any_unsafe_run": 67,
}


class GateViolation(RuntimeError):
    """A step tried to touch data or a split that the current gate does not allow."""


class DataIntegrityError(RuntimeError):
    """A required file is missing or its SHA-256 differs from the locked value."""


class KeyMismatchError(ValueError):
    """Row keys differ, are duplicated, are reordered, or are not consecutive."""


class MissingPredictionError(ValueError):
    """A method has no (or a non-finite) score for some eligible row."""


# --- hashes ---------------------------------------------------------------------------

def sha256_file(path, chunk_bytes: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(chunk_bytes)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def verify_file_hashes(base_dir, expected: Mapping[str, str]) -> List[Dict[str, object]]:
    """Hash every ``base_dir/<relpath>`` and compare with ``expected``. Raises
    DataIntegrityError listing every missing or changed file; returns the records otherwise."""
    records, problems = [], []
    for rel, want in expected.items():
        path = Path(base_dir) / rel
        if not path.is_file():
            records.append({"path": rel, "expected": want, "observed": None, "ok": False})
            problems.append(f"missing: {rel}")
            continue
        got = sha256_file(path)
        ok = got == want
        records.append({"path": rel, "expected": want, "observed": got, "size_bytes": path.stat().st_size, "ok": ok})
        if not ok:
            problems.append(f"hash differs: {rel} (expected {want[:12]}..., observed {got[:12]}...)")
    if problems:
        raise DataIntegrityError("; ".join(problems))
    return records


def verify_protocol(path, expected: str = PROTOCOL_SHA256) -> str:
    got = sha256_file(path)
    if got != expected:
        raise DataIntegrityError(f"protocol hash differs: expected {expected}, observed {got}")
    return got


def verify_baseline_manifest(root) -> Dict[str, object]:
    """Python equivalent of ``sha256sum -c baselines/v0.3.sha256`` run from ``root``."""
    manifest = Path(root) / BASELINE_MANIFEST_RELPATH
    n_ok, failures = 0, []
    for line in manifest.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, _, rel = line.partition("  ")
        rel = rel.strip().lstrip("*")
        target = Path(root) / rel
        if target.is_file() and sha256_file(target) == digest:
            n_ok += 1
        else:
            failures.append(rel)
    return {"n_ok": n_ok, "n_failed": len(failures), "failures": failures}


def assert_phase3_output_path(path, root) -> Path:
    """Phase 3 may write only below ``<root>/outputs/phase3/run_<UTC>/`` and never to a protected location."""
    root_p = Path(root).resolve()
    target = Path(path).resolve()
    allowed = root_p / "outputs" / "phase3"
    protected = [root_p / "outputs" / "ml_v03", root_p / "outputs" / "analysis_v11", root_p / FROZEN_MODEL_RELPATH]
    for bad in protected:
        if target == bad or bad in target.parents:
            raise GateViolation(f"refusing to write to protected location {bad}")
    if allowed not in target.parents:
        raise GateViolation(f"outputs must be below {allowed}, got {target}")
    run_part = target.relative_to(allowed).parts[0]
    if not run_part.startswith("run_"):
        raise GateViolation(f"outputs must be inside a per-run directory outputs/phase3/run_<UTC>/, got {target}")
    return target


# --- split-restricted loading -----------------------------------------------------------

@dataclass(frozen=True)
class SplitTable:
    """Rows of ONE split, tagged so that fit functions can refuse the wrong split."""
    split: str
    df: pd.DataFrame


def panel_path(data_dir, split: str) -> Path:
    if split not in SPLITS:
        raise ValueError(f"unknown split {split!r}")
    return Path(data_dir) / "ml_temporal_v03" / f"temporal_{split}.parquet"


def load_split(data_dir, split: str, columns: Sequence[str], allowed_splits: Iterable[str]) -> SplitTable:
    """Read ONLY ``columns`` of ONE split panel. ``allowed_splits`` is the gate's whitelist:
    asking for a split outside it raises before any file is opened."""
    if split not in SPLITS:
        raise ValueError(f"unknown split {split!r}")
    if split not in tuple(allowed_splits):
        raise GateViolation(f"split {split!r} is not allowed at this gate (allowed: {tuple(allowed_splits)})")
    path = panel_path(data_dir, split)
    if not path.is_file():
        raise DataIntegrityError(f"missing panel file {path}")
    cols = list(dict.fromkeys(columns))
    df = pd.read_parquet(path, columns=cols)
    return SplitTable(split=split, df=df)


def require_split(table: SplitTable, expected: str) -> None:
    if not isinstance(table, SplitTable) or table.split != expected:
        got = getattr(table, "split", type(table).__name__)
        raise GateViolation(f"expected the {expected!r} split, got {got!r}")


def schema_missing_columns(path, required: Iterable[str]) -> List[str]:
    """Read only the Parquet footer and report which required columns are absent."""
    import pyarrow.parquet as pq

    names = set(pq.read_schema(path).names)
    return [c for c in required if c not in names]


# --- row identity --------------------------------------------------------------------------

@dataclass(frozen=True)
class RowKeys:
    """``(trajectory_id, step)`` per row, in the order of the source table."""
    traj: np.ndarray
    step: np.ndarray

    def __len__(self) -> int:
        return int(self.step.shape[0])


def step_index(time) -> np.ndarray:
    t = np.asarray(time, dtype=float)
    steps = np.rint(t / DT)
    if t.size and float(np.max(np.abs(t - steps * DT))) > 1e-6:
        raise KeyMismatchError("time values are not on the 0.01 s grid")
    return steps.astype(np.int64)


def _blocks(codes: np.ndarray):
    n = codes.shape[0]
    if n == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)
    change = np.flatnonzero(codes[1:] != codes[:-1]) + 1
    starts = np.concatenate([[0], change]).astype(np.int64)
    ends = np.concatenate([change, [n]]).astype(np.int64)
    return starts, ends


def trajectory_blocks(traj):
    """(starts, ends, codes) of the contiguous per-trajectory blocks of a trajectory-id array."""
    codes, _ = pd.factorize(np.asarray(traj))
    starts, ends = _blocks(codes)
    return starts, ends, codes


def row_keys(df: pd.DataFrame) -> RowKeys:
    """Keys of ``df``'s rows. Raises unless every trajectory occupies one contiguous block with
    strictly increasing steps (which also makes the keys unique)."""
    traj = df["trajectory_id"].to_numpy()
    step = step_index(df["time"].to_numpy(dtype=float))
    codes, uniques = pd.factorize(traj)
    starts, ends = _blocks(codes)
    if len(starts) != len(uniques):
        raise KeyMismatchError("rows of a trajectory are not contiguous (trajectories are interleaved)")
    if step.size > 1:
        same = codes[1:] == codes[:-1]
        if (np.diff(step)[same] <= 0).any():
            raise KeyMismatchError("steps are not strictly increasing within a trajectory (duplicate or reordered rows)")
    return RowKeys(traj=traj, step=step)


def assert_consecutive_steps(keys: RowKeys) -> int:
    """Within each trajectory the steps must advance by exactly 1 (PROTOCOL.md 8.1): episodes
    are formed by array adjacency, not by time gaps. Returns the number of trajectories."""
    codes, uniques = pd.factorize(keys.traj)
    if keys.step.size > 1:
        same = codes[1:] == codes[:-1]
        if (np.diff(keys.step)[same] != 1).any():
            raise KeyMismatchError("eligible rows of a trajectory are not consecutive time steps")
    return int(len(uniques))


def assert_same_keys(a: RowKeys, b: RowKeys, label: str = "keys") -> None:
    if len(a) != len(b):
        raise KeyMismatchError(f"{label}: different number of rows ({len(a)} vs {len(b)})")
    if not np.array_equal(a.step, b.step) or not np.array_equal(a.traj, b.traj):
        raise KeyMismatchError(f"{label}: row keys differ (rows missing, reordered or relabelled)")


@dataclass(frozen=True)
class PredictionSet:
    name: str
    keys: RowKeys
    score: np.ndarray


def make_prediction_set(name: str, keys: RowKeys, score) -> PredictionSet:
    s = np.asarray(score, dtype=float)
    if s.ndim != 1 or s.shape[0] != len(keys):
        raise MissingPredictionError(f"{name}: expected {len(keys)} scores, got shape {s.shape}")
    bad = ~np.isfinite(s)
    if bad.any():
        raise MissingPredictionError(f"{name}: {int(bad.sum())} eligible row(s) have no finite score")
    return PredictionSet(name=name, keys=keys, score=s)


def assert_common_population(reference: RowKeys, labels, sets: Sequence[PredictionSet]) -> None:
    """Every method must carry exactly the reference keys, in the same order, and one label per row."""
    labels = np.asarray(labels)
    if labels.shape[0] != len(reference):
        raise KeyMismatchError("labels and reference keys have different lengths")
    for s in sets:
        assert_same_keys(reference, s.keys, label=f"method {s.name}")
        if s.score.shape[0] != labels.shape[0]:
            raise MissingPredictionError(f"{s.name}: score and label counts differ")


def eligible_time(keys: RowKeys) -> Dict[str, float]:
    """The two candidate denominators of PROTOCOL.md 8.4."""
    codes, uniques = pd.factorize(keys.traj)
    starts, ends = _blocks(codes)
    span_steps = int((keys.step[ends - 1] - keys.step[starts]).sum()) if len(starts) else 0
    return {
        "n_rows": len(keys),
        "n_trajectories": int(len(uniques)),
        "span_seconds": span_steps * DT,          # existing definition: sum of (max time - min time)
        "rows_times_dt_seconds": len(keys) * DT,  # reported alongside, not used as the denominator
    }


# --- population ----------------------------------------------------------------------------

def usable_mask(df: pd.DataFrame) -> np.ndarray:
    """Label available AND a full 1.0 s history window (existing function, reused unchanged)."""
    return usable_mask_for_window(df, WINDOW_S).to_numpy(dtype=bool)


def summarize_population(df: pd.DataFrame) -> Dict[str, int]:
    mask = usable_mask(df)
    sub = df.loc[mask]
    y = sub[TARGET_COL].to_numpy()
    out = {
        "rows_total": int(len(df)),
        "trajectories_total": int(df["trajectory_id"].nunique()),
        "rows_usable": int(mask.sum()),
        "trajectories_with_usable_rows": int(sub["trajectory_id"].nunique()),
        "positives": int((y == 1).sum()),
        "negatives": int((y == 0).sum()),
    }
    if "is_unsafe" in df.columns:
        out["trajectories_with_any_unsafe_run"] = int(df.loc[df["is_unsafe"].astype(bool), "trajectory_id"].nunique())
    return out


def count_events(df: pd.DataFrame, mask: Optional[np.ndarray] = None) -> Dict[str, int]:
    """Events as defined by ml/events.py: maximal runs of is_unsafe among the rows passed in
    (here the eligible rows). First vs later is the order within a trajectory."""
    sub = df if mask is None else df.loc[mask]
    first = later = 0
    traj_with_events = 0
    for _, g in sub.groupby("trajectory_id", sort=False):
        runs = group_boolean_into_episodes(g["time"].to_numpy(), g["is_unsafe"].to_numpy().astype(bool))
        if runs:
            traj_with_events += 1
            first += 1
            later += len(runs) - 1
    return {"events": first + later, "first_events": first, "later_events": later, "trajectories_with_events": traj_with_events}


def compare_counts(observed: Mapping[str, int], expected: Mapping[str, int] = REPORTED_COUNTS) -> List[str]:
    """Human-readable mismatches; an empty list means every expected count was reproduced."""
    problems = []
    for key, want in expected.items():
        if key not in observed:
            problems.append(f"{key}: not observed")
        elif int(observed[key]) != int(want):
            problems.append(f"{key}: expected {want}, observed {observed[key]}")
    return problems


def assert_no_trajectory_overlap(ids_by_split: Mapping[str, Iterable]) -> None:
    names = list(ids_by_split)
    sets = {n: set(ids_by_split[n]) for n in names}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            both = sets[a] & sets[b]
            if both:
                raise KeyMismatchError(f"{len(both)} trajectory id(s) appear in both {a} and {b}, e.g. {sorted(both)[:3]}")


def compare_with_item26(keys: RowKeys, labels, item26_keys: pd.DataFrame, item26_labels) -> Dict[str, object]:
    """Cross-check against the Item 26 artifacts (a prior E1 record, not a validation).
    Fails closed on an unexpected schema instead of guessing."""
    if "trajectory_id" not in item26_keys.columns:
        raise ValueError("Item 26 row_keys has no 'trajectory_id' column")
    if "step" in item26_keys.columns:
        other_step = item26_keys["step"].to_numpy(dtype=np.int64)
    elif "time" in item26_keys.columns:
        other_step = step_index(item26_keys["time"].to_numpy(dtype=float))
    else:
        raise ValueError("Item 26 row_keys has neither a 'step' nor a 'time' column")
    other = RowKeys(traj=item26_keys["trajectory_id"].to_numpy(), step=other_step)
    keys_equal = len(other) == len(keys) and np.array_equal(other.step, keys.step) and np.array_equal(other.traj, keys.traj)
    lab = np.asarray(item26_labels)
    labels_equal = lab.shape == np.asarray(labels).shape and bool(np.array_equal(lab.astype(int), np.asarray(labels).astype(int)))
    return {"keys_equal": bool(keys_equal), "labels_equal": bool(labels_equal), "n_item26": len(other), "n_phase3": len(keys)}
