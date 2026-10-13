"""Synthetic fixtures for the Item 33 tests. Nothing here is a research result.

``make_panel`` builds trajectories with the real panel's columns (all 23 frozen features, the label, the
availability flag, ``is_unsafe`` and ``time_to_stall``). The first 100 rows of a trajectory have NaN window columns and
the last 500 rows have no label, exactly like the real panels, so the project's own ``usable_mask_for_window`` applies.
``StubForest`` is NOT a learning algorithm: ``fit`` only records the training columns and ``predict_proba`` is a fixed
function of the features, so the plumbing can be tested without training anything.
"""

import numpy as np
import pandas as pd

from aeroguard_dataset.labeling import compute_future_stall_label
from item33.conditions import C0_FEATURES

DT = 0.01
A_PEAK = 0.28044009791924895
WINDOW_COLS = [
    "alpha_mean_1s", "alpha_min_1s", "alpha_max_1s", "alpha_range_1s", "alpha_slope_1s", "alpha_trend_1s",
    "V_slope_1s", "gamma_slope_1s", "pitch_rate_slope_1s", "elevator_change_1s",
]
PULSES = {"normal": [], "pos": [(650, 1)], "neg": [(650, -1)], "double": [(300, 1), (650, 1)]}


def _time_to_stall(time, is_unsafe):
    out = np.full(len(time), np.nan)
    unsafe = np.flatnonzero(is_unsafe)
    for i in range(len(time)):
        later = unsafe[unsafe > i]
        if later.size:
            out[i] = time[later[0]] - time[i]
    return out


def make_panel(prefix, kinds, seed=0, length=800):
    rng = np.random.default_rng(seed)
    idx = np.arange(length)
    frames = []
    for n, kind in enumerate(kinds):
        alpha = 0.01 * np.sin(idx / 80.0 + n) + 0.0005 * rng.standard_normal(length)
        for centre, sign in PULSES[kind]:
            alpha = alpha + sign * 0.33 * np.exp(-0.5 * ((idx - centre) / 60.0) ** 2)
        time = idx * DT
        is_unsafe = np.abs(alpha) > A_PEAK
        label, avail = compute_future_stall_label(is_unsafe, DT, 5.0)
        data = {name: rng.standard_normal(length) * 0.01 for name in C0_FEATURES}
        data.update({"V": 40.0 + 0.3 * rng.standard_normal(length), "alpha": alpha, "stall_margin": A_PEAK - alpha,
                     "elevator": -0.02 + 0.005 * rng.standard_normal(length), "throttle": np.full(length, 0.3 + 0.01 * n)})
        df = pd.DataFrame(data)
        df.insert(0, "time", time)
        df.insert(0, "trajectory_id", f"{prefix}_{n:03d}")
        df["is_unsafe"] = is_unsafe
        df["future_stall_5s"] = label
        df["future_stall_5s_available"] = avail
        df["time_to_stall"] = _time_to_stall(time, is_unsafe)
        df.loc[: 99, WINDOW_COLS] = np.nan     # no full 1 s window yet
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


KINDS_TRAIN = ["pos", "neg", "normal", "double", "pos", "normal", "pos", "double", "normal", "pos"]
KINDS_VAL = ["pos", "normal", "double", "neg", "normal", "pos"]
KINDS_TEST = ["pos", "normal", "double", "pos", "normal", "neg", "normal", "pos"]


def make_splits(seed=0):
    return {
        "train": make_panel("tr", KINDS_TRAIN, seed=seed + 1),
        "val": make_panel("va", KINDS_VAL, seed=seed + 2),
        "test": make_panel("te", KINDS_TEST, seed=seed + 3),
    }


def make_manifest(splits):
    rows = [(t, s) for s, df in splits.items() for t in df["trajectory_id"].unique()]
    return pd.DataFrame(rows, columns=["trajectory_id", "split"])


def make_metadata(splits):
    regimes = ["normal", "stall", "gradual_approach_v3"]
    ids = [t for df in splits.values() for t in df["trajectory_id"].unique()]
    return pd.DataFrame({"trajectory_id": ids, "generation_mode": [regimes[i % 3] for i in range(len(ids))]})


class StubForest:
    """Deterministic stand-in for a fitted forest (records columns; no learning)."""

    def __init__(self, seed):
        self.seed = int(seed)
        self.columns = None
        self.fit_calls = 0

    def fit(self, X, y):
        self.fit_calls += 1
        self.columns = list(X.columns)
        self.feature_names_in_ = np.array(self.columns, dtype=object)
        self.n_features_in_ = len(self.columns)
        return self

    def predict_proba(self, X):
        cols = list(X.columns)
        z = 40.0 * (X["alpha"].to_numpy() - 0.15)
        if "elevator" in cols:
            z = z + 25.0 * X["elevator"].to_numpy()
        if "elevator_change_1s" in cols:
            z = z + 5.0 * X["elevator_change_1s"].to_numpy()
        jitter = np.random.default_rng(self.seed).normal(0.0, 0.02, len(X))
        p = 1.0 / (1.0 + np.exp(-(z + jitter)))
        return np.column_stack([1.0 - p, p])


class StubFrozen(StubForest):
    """Stand-in for the frozen model in the dry run: never the real artifact."""

    def __init__(self):
        super().__init__(0)
        self.feature_names_in_ = np.array(list(C0_FEATURES), dtype=object)
        self.n_features_in_ = len(C0_FEATURES)

    def fit(self, X, y):  # pragma: no cover - a frozen model is never fitted
        raise AssertionError("the frozen stand-in must never be fitted")

    def predict_proba(self, X):
        z = 40.0 * (X["alpha"].to_numpy() - 0.15) + 25.0 * X["elevator"].to_numpy() + 2.0 * X["throttle"].to_numpy()
        p = 1.0 / (1.0 + np.exp(-z))
        return np.column_stack([1.0 - p, p])
