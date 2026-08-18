"""Causal multi-window temporal summary features (Stage 4, Task 3).

TEMPORAL INDEXING CONVENTION (Task 2 -- documented precisely, once,
here):

  For a row at time t within a trajectory, a history window of length
  W seconds covers the CLOSED interval [t - W, t], i.e. the current
  sample plus every sample strictly before it back to and including
  t - W. With a fixed timestep dt, that interval contains exactly
  window_steps(W) + 1 samples, where window_steps(W) = round(W / dt).

  Every statistic computed over that window uses ONLY those
  window_steps(W)+1 samples -- never a sample at any time > t. A
  statistic is NaN for the first window_steps(W) rows of a trajectory
  (there is no legitimate way to fill a window that does not yet have
  enough history; see Task 3/13 "correct handling of insufficient-
  history rows").

  All window/derivative computations here are grouped by
  trajectory_id BEFORE any shift/rolling operation, so a window can
  never span two different trajectories (verified directly in
  tests/test_temporal_features.py, mirroring the existing
  tests/test_ml_dataset_prep.py::test_naive_ungrouped_shift_would_leak
  pattern).

  The future_stall_5s target is NEVER read by anything in this module
  -- it is computed independently in aeroguard_dataset/labeling.py from
  strictly future samples and is only ever consumed downstream as the
  training/evaluation label, never as an input feature here.

STATISTICS COMPUTED PER WINDOW (see ml/temporal_config.py for exactly
which variables get which statistic -- alpha gets the full panel below,
a few other physically-motivated variables get only a slope or a
recent-change):

  mean / min / max / range:
      simple aggregate statistics of the window's window_steps+1 samples.
  slope (compute_ols_slope):
      the causal ordinary-least-squares slope of the variable against
      time, fit over all window_steps+1 samples in the window -- more
      robust to single-sample noise than a 2-point difference. Computed
      via a closed-form O(1)-per-row rolling-sum formula (see function
      docstring), not a per-row polyfit, so it stays fast at dataset
      scale (~1M+ rows x 4 windows x several variables).
  trend (compute_endpoint_rate):
      (x[t] - x[t-W]) / W -- a 2-point endpoint RATE. For alpha and
      W in {1,2,3}s this reproduces, by construction, the same formula
      already used and validated for alpha_trend_1s/2s/3s in
      scripts/prepare_ml_dataset.py (verified in
      tests/test_temporal_features.py).
  endpoint difference (compute_endpoint_diff):
      x[t] - x[t-W] -- the raw (unscaled) 2-point difference, used for
      "elevator recent change" where the raw step size, not a rate, is
      the physically relevant quantity for a control input.
"""

from typing import List

import numpy as np
import pandas as pd

from . import temporal_config as tcfg


def window_steps(window_s: float, dt: float) -> int:
    return int(round(window_s / dt))


def _rolling_stat_grouped(series: pd.Series, group_keys: pd.Series, n: int, stat: str) -> pd.Series:
    rolled = series.groupby(group_keys, sort=False).rolling(window=n, min_periods=n)
    out = getattr(rolled, stat)()
    return out.reset_index(level=0, drop=True)


def compute_rolling_stat(df: pd.DataFrame, traj_col: str, col: str, window_s: float, dt: float, stat: str) -> pd.Series:
    """stat in {'mean', 'min', 'max'}. NaN for the first window_steps(W)
    rows of each trajectory (min_periods=n enforces this)."""
    n = window_steps(window_s, dt) + 1
    return _rolling_stat_grouped(df[col], df[traj_col], n, stat)


def compute_ols_slope(df: pd.DataFrame, traj_col: str, col: str, window_s: float, dt: float) -> pd.Series:
    """Causal OLS slope of df[col] vs. time over the trailing closed
    window [t-W, t], per trajectory.

    Closed-form derivation: for a window of n = window_steps+1 samples
    with time offsets x_i = 0..n-1 (relative to the window start), the
    OLS slope is
        slope = (n*Sxy - Sx*Sy) / (n*Sxx - Sx^2)
    where Sx, Sxx are fixed constants (x_i doesn't depend on WHERE the
    window is, only on n) and Sy = sum(y_i) is an ordinary rolling sum.
    Sxy = sum(x_i * y_i) is the only nontrivial part because x_i is a
    RELATIVE (window-local) offset that resets at every window
    position -- but writing x_i = g_i - (g_t - n + 1) (g_i = the
    variable's GLOBAL row-position-within-trajectory) turns Sxy into
    Sz - (g_t-n+1)*Sy, where Sz = sum(g_i * y_i) is ALSO an ordinary
    rolling sum (of the fixed series g*y). This lets the whole
    per-window regression be computed with two O(1)-per-row rolling
    sums instead of a per-row least-squares fit.
    """
    n = window_steps(window_s, dt) + 1
    if n < 2:
        raise ValueError("window must contain at least 2 samples")

    grp = df[traj_col]
    idx_global = df.groupby(traj_col, sort=False).cumcount().astype(float)
    y = df[col].astype(float)
    z = idx_global * y

    Sy = _rolling_stat_grouped(y, grp, n, "sum")
    Sz = _rolling_stat_grouped(z, grp, n, "sum")

    Sx = n * (n - 1) / 2.0
    Sxx = (n - 1) * n * (2 * n - 1) / 6.0
    denom = n * Sxx - Sx * Sx  # constant, > 0 for n >= 2

    window_start_idx = idx_global - (n - 1)
    Sxy = Sz - window_start_idx * Sy
    slope_per_step = (n * Sxy - Sx * Sy) / denom
    return slope_per_step / dt  # convert from rad/step to rad/s (x_i above are step counts, not seconds)


def compute_endpoint_diff(df: pd.DataFrame, traj_col: str, col: str, window_s: float, dt: float) -> pd.Series:
    n = window_steps(window_s, dt)
    lagged = df.groupby(traj_col, sort=False)[col].shift(n)
    return df[col] - lagged


def compute_endpoint_rate(df: pd.DataFrame, traj_col: str, col: str, window_s: float, dt: float) -> pd.Series:
    return compute_endpoint_diff(df, traj_col, col, window_s, dt) / window_s


def compute_second_derivative(df: pd.DataFrame, traj_col: str, first_derivative_col: str, dt: float) -> pd.Series:
    """Causal second derivative via a second backward difference applied
    to an already-causal first-derivative column (e.g. dalpha_dt).
    NaN for the first TWO rows of each trajectory (row 0's first
    derivative is already NaN, so row 1's second derivative -- which
    needs row 0's first derivative -- is NaN too)."""
    prev = df.groupby(traj_col, sort=False)[first_derivative_col].shift(1)
    return (df[first_derivative_col] - prev) / dt


def build_temporal_panel(
    df: pd.DataFrame,
    windows_s: List[float] = None,
    dt: float = None,
    traj_col: str = "trajectory_id",
    time_col: str = "time",
) -> pd.DataFrame:
    """Add every Stage-4 temporal-summary column (Task 3) to a copy of
    `df`. `df` must already contain the base per-trajectory telemetry
    columns (V, alpha, gamma, pitch_rate, elevator) and, for the second
    derivative, dalpha_dt -- exactly what ml_{train,val,test}_v2.parquet
    already provide (see ml/temporal_data.py).

    Sorts by (trajectory_id, time) first and returns a fresh
    0..n-1 RangeIndex, so every rolling/shift operation inside is
    guaranteed to see each trajectory's own rows in time order and
    never a mix of trajectories.
    """
    windows_s = list(windows_s) if windows_s is not None else tcfg.HISTORY_WINDOWS_S
    dt = dt if dt is not None else tcfg.DT

    df = df.sort_values([traj_col, time_col]).reset_index(drop=True)
    out = df.copy()

    for w in windows_s:
        wtag = tcfg._fmt(w)
        out[f"alpha_mean_{wtag}s"] = compute_rolling_stat(df, traj_col, "alpha", w, dt, "mean")
        out[f"alpha_min_{wtag}s"] = compute_rolling_stat(df, traj_col, "alpha", w, dt, "min")
        out[f"alpha_max_{wtag}s"] = compute_rolling_stat(df, traj_col, "alpha", w, dt, "max")
        out[f"alpha_range_{wtag}s"] = out[f"alpha_max_{wtag}s"] - out[f"alpha_min_{wtag}s"]
        out[f"alpha_slope_{wtag}s"] = compute_ols_slope(df, traj_col, "alpha", w, dt)
        out[f"alpha_trend_{wtag}s"] = compute_endpoint_rate(df, traj_col, "alpha", w, dt)

        for v in tcfg.SLOPE_ONLY_VARS:
            out[f"{v}_slope_{wtag}s"] = compute_ols_slope(df, traj_col, v, w, dt)
        for v in tcfg.ENDPOINT_DIFF_ONLY_VARS:
            out[f"{v}_change_{wtag}s"] = compute_endpoint_diff(df, traj_col, v, w, dt)

    if "dalpha_dt" in df.columns:
        out["d2alpha_dt2"] = compute_second_derivative(df, traj_col, "dalpha_dt", dt)

    return out


def usable_mask_for_window(df: pd.DataFrame, window_s: float) -> pd.Series:
    """Rows where the target is available AND every temporal-summary
    column for this specific window is available (Task 2/5: 'each row
    has sufficient history for every temporal window being compared')."""
    mask = df[tcfg.TARGET_AVAILABLE_COL].astype(bool)
    for c in tcfg.temporal_feature_columns(window_s):
        mask = mask & df[c].notna()
    return mask


def common_subset_mask(df: pd.DataFrame, windows_s: List[float] = None) -> pd.Series:
    """Task 5's FAIR-comparison population: rows usable for every window
    under comparison simultaneously. Because windows are nested closed
    intervals [t-W, t] over the SAME uniformly-sampled trajectory, a row
    with a full window at the LARGEST W automatically has a full window
    at every smaller W too -- so the common subset is exactly the
    largest window's own usable mask (checked directly in
    tests/test_temporal_features.py::test_common_subset_equals_largest_window_mask)."""
    windows_s = list(windows_s) if windows_s is not None else tcfg.HISTORY_WINDOWS_S
    return usable_mask_for_window(df, max(windows_s))
