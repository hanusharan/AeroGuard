"""Builds the Stage-4 temporal feature panel.

Reads ONLY data/processed/processed_dataset_v2.parquet and
data/splits/split_manifest_v2.csv (both frozen Stage 2 outputs) --
i.e. each trajectory's COMPLETE row sequence, including row 0. This is
deliberate, not incidental: building temporal (rolling/shift) features
on top of the ALREADY "usable"-row-filtered ml_{split}_v2.parquet
tables (which exclude each trajectory's row 0, since dV_dt/dalpha_dt
are undefined there) would silently shift every window's boundary-NaN
convention by one row relative to Stage 3's own convention -- caught
during development by
tests/test_temporal_features.py::test_recomputed_alpha_trend_matches_original_ml_v2_columns,
which failed until this module switched from reading ml_{split}_v2 to
reading the full processed table directly.

Reuses two already-validated Stage-3 building blocks rather than
reimplementing them:
  - aeroguard_dataset.features.causal_backward_difference for
    dgamma_dt/dq_dt (same function already used for dV_dt/dalpha_dt in
    Stage 2 and for dgamma_dt/dq_dt in Stage 3's
    scripts/prepare_ml_dataset.py).
  - scripts/prepare_ml_dataset.py's compute_time_to_stall (identical
    formula/behavior as the one already shipped in
    ml_{split}_v2.parquet's time_to_stall column; tested in
    tests/test_ml_dataset_prep.py).

Never modifies aeroguard_dataset/, data/processed/, data/splits/, or
data/ml/. Caches its own output under data/ml_temporal/ -- a new,
additive location.
"""

import os
import sys

import pandas as pd

from . import config as base_config
from . import temporal_config as tcfg
from .temporal_features import build_temporal_panel
from aeroguard_dataset.features import causal_backward_difference

_SCRIPTS_DIR = os.path.join(tcfg.PROJECT_ROOT, "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
from prepare_ml_dataset import compute_time_to_stall  # noqa: E402  (validated in tests/test_ml_dataset_prep.py)

_SPLIT_NAMES = ("train", "val", "test")


def _cache_paths():
    return {s: os.path.join(tcfg.TEMPORAL_DATA_DIR, f"temporal_{s}.parquet") for s in _SPLIT_NAMES}


def _load_full_processed_with_split() -> pd.DataFrame:
    df = pd.read_parquet(base_config.PROCESSED_DATASET_PATH)
    manifest = pd.read_csv(base_config.SPLIT_MANIFEST_PATH)
    df = df.sort_values(["trajectory_id", "time"]).reset_index(drop=True)

    n_before = len(df)
    df = df.merge(manifest, on="trajectory_id", how="left", validate="many_to_one")
    assert len(df) == n_before, "merge with split manifest changed row count"
    assert df["split"].notna().all(), "some trajectory_id(s) missing from split manifest"

    df["dgamma_dt"] = df.groupby("trajectory_id")["gamma"].transform(lambda s: causal_backward_difference(s.to_numpy(), tcfg.DT))
    df["dq_dt"] = df.groupby("trajectory_id")["pitch_rate"].transform(lambda s: causal_backward_difference(s.to_numpy(), tcfg.DT))
    df["time_to_stall"] = compute_time_to_stall(df)
    return df


def build_and_cache_temporal_splits(force: bool = False, verbose: bool = True) -> dict:
    tcfg.ensure_dirs()
    paths = _cache_paths()
    if not force and all(os.path.exists(p) for p in paths.values()):
        if verbose:
            print(f"Reusing cached temporal panels in {tcfg.TEMPORAL_DATA_DIR} (pass force=True to rebuild)")
        return {s: pd.read_parquet(p) for s, p in paths.items()}

    if verbose:
        print(f"Loading full processed dataset ({base_config.PROCESSED_DATASET_PATH})...")
    full = _load_full_processed_with_split()
    if verbose:
        print(f"  {len(full):,} rows, {full['trajectory_id'].nunique()} trajectories")
        print(f"Building temporal panel (windows={tcfg.HISTORY_WINDOWS_S})...")
    panel_full = build_temporal_panel(full, windows_s=tcfg.HISTORY_WINDOWS_S, dt=tcfg.DT)

    out = {}
    for name in _SPLIT_NAMES:
        split_df = panel_full.loc[panel_full["split"] == name].drop(columns=["split"]).reset_index(drop=True)
        split_df.to_parquet(paths[name], index=False)
        out[name] = split_df
        if verbose:
            print(f"  -> {paths[name]} ({len(split_df):,} rows, {len(split_df.columns)} columns)")
    return out


def load_temporal_splits(force: bool = False, verbose: bool = True) -> dict:
    """Returns {'train': df, 'val': df, 'test': df}, each with every
    base physics column, every Stage-3 CORE_FEATURES/target column, and
    every Stage-4 temporal summary column
    (ml/temporal_config.py:temporal_feature_columns)."""
    return build_and_cache_temporal_splits(force=force, verbose=verbose)
