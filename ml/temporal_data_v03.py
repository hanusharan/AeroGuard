"""Builds the v0.3 temporal feature panel.

Additive companion to ml/temporal_data.py -- identical procedure, reused
building blocks (build_temporal_panel, causal_backward_difference,
compute_time_to_stall), pointed at the v0.3 full-scale dataset instead
of v0.2's. See ml/temporal_data.py's module docstring for why the FULL
processed table (not the Stage-3 "usable" table) is read, and why the
window-boundary NaN convention this produces is the correct one.

Reads ONLY data/processed/processed_dataset_v3.parquet and
data/splits/split_manifest_v3.csv (both frozen v0.3-generation-gate
outputs -- never modified here). Caches its own output under
data/ml_temporal_v03/ -- a new, additive location. Never touches
data/ml_temporal/, data/ml/, data/processed/, or data/splits/.
"""

import os
import sys

import pandas as pd

from . import temporal_config_v03 as v3cfg
from .temporal_features import build_temporal_panel
from aeroguard_dataset.features import causal_backward_difference

_SCRIPTS_DIR = os.path.join(v3cfg.PROJECT_ROOT, "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
from prepare_ml_dataset import compute_time_to_stall  # noqa: E402  (dataset-agnostic; validated in tests/test_ml_dataset_prep.py)

_SPLIT_NAMES = ("train", "val", "test")


def _cache_paths():
    return {s: os.path.join(v3cfg.TEMPORAL_DATA_DIR, f"temporal_{s}.parquet") for s in _SPLIT_NAMES}


def _load_full_processed_with_split() -> pd.DataFrame:
    df = pd.read_parquet(v3cfg.PROCESSED_DATASET_PATH)
    manifest = pd.read_csv(v3cfg.SPLIT_MANIFEST_PATH)
    df = df.sort_values(["trajectory_id", "time"]).reset_index(drop=True)

    n_before = len(df)
    df = df.merge(manifest, on="trajectory_id", how="left", validate="many_to_one")
    assert len(df) == n_before, "merge with v0.3 split manifest changed row count"
    assert df["split"].notna().all(), "some v0.3 trajectory_id(s) missing from split manifest"

    df["dgamma_dt"] = df.groupby("trajectory_id")["gamma"].transform(lambda s: causal_backward_difference(s.to_numpy(), v3cfg.DT))
    df["dq_dt"] = df.groupby("trajectory_id")["pitch_rate"].transform(lambda s: causal_backward_difference(s.to_numpy(), v3cfg.DT))
    df["time_to_stall"] = compute_time_to_stall(df)
    return df


def build_and_cache_temporal_splits(force: bool = False, verbose: bool = True) -> dict:
    v3cfg.ensure_dirs()
    paths = _cache_paths()
    if not force and all(os.path.exists(p) for p in paths.values()):
        if verbose:
            print(f"Reusing cached v0.3 temporal panels in {v3cfg.TEMPORAL_DATA_DIR} (pass force=True to rebuild)")
        return {s: pd.read_parquet(p) for s, p in paths.items()}

    if verbose:
        print(f"Loading full v0.3 processed dataset ({v3cfg.PROCESSED_DATASET_PATH})...")
    full = _load_full_processed_with_split()
    if verbose:
        print(f"  {len(full):,} rows, {full['trajectory_id'].nunique()} trajectories")
        print(f"Building v0.3 temporal panel (windows={v3cfg.HISTORY_WINDOWS_S})...")
    panel_full = build_temporal_panel(full, windows_s=v3cfg.HISTORY_WINDOWS_S, dt=v3cfg.DT)

    out = {}
    for name in _SPLIT_NAMES:
        split_df = panel_full.loc[panel_full["split"] == name].drop(columns=["split"]).reset_index(drop=True)
        split_df.to_parquet(paths[name], index=False)
        out[name] = split_df
        if verbose:
            print(f"  -> {paths[name]} ({len(split_df):,} rows, {len(split_df.columns)} columns)")
    return out


def load_temporal_splits(force: bool = False, verbose: bool = True) -> dict:
    """Returns {'train': df, 'val': df, 'test': df} for v0.3, each with
    every base physics column, every temporal summary column (windows
    from ml/temporal_config_v03.py), dgamma_dt/dq_dt, and time_to_stall."""
    return build_and_cache_temporal_splits(force=force, verbose=verbose)
