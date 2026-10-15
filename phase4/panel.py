"""Feature panel for Phase 4 (reuses ml/ unchanged).

The same derivative columns as ``ml.temporal_data_v03`` (dgamma_dt, dq_dt by the
causal backward difference) and the 1 s window of ``ml.temporal_features.build_temporal_panel``.
Only usable rows are kept (target available and full 1 s window), as in every
earlier temporal evaluation. Feature columns are stored as float32: scikit-learn
trees cast inputs to float32 before splitting, so this does not change any
tree decision.
"""

from typing import List

import numpy as np
import pandas as pd

from aeroguard_dataset.features import causal_backward_difference
from ml.temporal_config import INSTANTANEOUS_STATE_FEATURES, model_d_features
from ml.temporal_features import build_temporal_panel, usable_mask_for_window

from . import DT

WINDOW_S = 1.0
FEATURES_D: List[str] = list(model_d_features(WINDOW_S))                      # 23
FEATURES_D_NOSM: List[str] = [c for c in FEATURES_D if c != "stall_margin"]   # 22
FEATURES_A: List[str] = list(INSTANTANEOUS_STATE_FEATURES)                    # 8
ACTUATOR_FEATURES = ("elevator", "throttle", "elevator_change_1s")
FEATURES_XD: List[str] = [c for c in FEATURES_D if c not in ACTUATOR_FEATURES]            # 20
FEATURES_XD_NOSM: List[str] = [c for c in FEATURES_XD if c != "stall_margin"]            # 19
KEEP = ["trajectory_id", "time", "is_unsafe", "future_stall_5s", "dalpha_dt"]


def build_usable_panel(frames: List[pd.DataFrame]) -> pd.DataFrame:
    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values(["trajectory_id", "time"]).reset_index(drop=True)
    g = df.groupby("trajectory_id", sort=False)
    df["dgamma_dt"] = g["gamma"].transform(lambda s: causal_backward_difference(s.to_numpy(), DT))
    df["dq_dt"] = g["pitch_rate"].transform(lambda s: causal_backward_difference(s.to_numpy(), DT))
    panel = build_temporal_panel(df, windows_s=[WINDOW_S], dt=DT)
    mask = usable_mask_for_window(panel, WINDOW_S).to_numpy()
    out = panel.loc[mask, list(dict.fromkeys(KEEP + FEATURES_D))].reset_index(drop=True)
    bad = ~np.isfinite(out[FEATURES_D].to_numpy(dtype=float)).all(axis=1)
    if bad.any():
        raise ValueError(f"{int(bad.sum())} usable rows have a non-finite feature")
    out[FEATURES_D] = out[FEATURES_D].astype(np.float32)
    out["future_stall_5s"] = out["future_stall_5s"].astype(np.int8)
    out["is_unsafe"] = out["is_unsafe"].astype(bool)
    return out


def stride_rows(df: pd.DataFrame, stride: int) -> pd.DataFrame:
    """Every ``stride``-th usable row of each trajectory, starting from its first usable row."""
    if stride == 1:
        return df
    pos = df.groupby("trajectory_id", sort=False).cumcount().to_numpy()
    return df.loc[pos % stride == 0].reset_index(drop=True)
