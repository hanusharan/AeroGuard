"""AeroGuard Stage 3: build the ML-ready dataset from the frozen v0.2 telemetry.

Reads ONLY data/processed/processed_dataset_v2.parquet and
data/splits/split_manifest_v2.csv (both already validated in Stage 2).
Does not modify, regenerate, or re-derive the underlying physics or the
existing future_stall_5s label -- that label was independently
re-derived from raw telemetry and matched exactly (0 mismatches across
all 1000 trajectories); this script reuses it as-is.

What this script ADDS (documented in full in ml_feature_schema_v2.json):
  1. Two new causal derivatives, computed with the SAME validated
     backward-difference function already used for dV_dt/dalpha_dt
     (aeroguard_dataset.features.causal_backward_difference), applied
     per-trajectory so no cross-trajectory contamination is possible:
        dgamma_dt, dq_dt
  2. Three causal ALPHA TREND features (1s/2s/3s look-back). These are
     evidence-based, not guessed: a direct correlation check against
     future_stall_5s showed alpha's trend strengthens substantially
     with a longer look-back (0.127 at 0.01s -> 0.422 at 3s), while the
     same check for gamma/V/pitch_rate showed no such benefit (all
     stayed below 0.08, flat vs. window length) -- so only alpha gets
     window features, per the "don't blindly create hundreds of
     features" instruction.
  3. A secondary target, time_to_stall: time until the FIRST future
     is_unsafe row in the same trajectory (NaN if none remains). Unlike
     future_stall_5s, this has no "insufficient future data" ambiguity
     -- every trajectory is fully simulated to its own actual end, so
     "does a crossing exist anywhere in the remaining recorded
     telemetry" is always answerable.

Row filtering -- IMPORTANT DESIGN CORRECTION found while building this
script: my first pass required ALL designed features (including the
3-second alpha trend) to be non-NaN before a row counted as "usable".
That combines with the existing 5-second future-label requirement to
impose an implicit ~8-second MINIMUM TRAJECTORY DURATION (3s of past
history + 5s of future label runway) before a trajectory can contribute
even one training row. Checking who that excluded: 152/1000
trajectories, ALL terminated via the gamma envelope, and 138 of those
152 are from the "stall" regime (55% of all 250 stall trajectories!) --
i.e. it disproportionately erases exactly the fastest, most violent
stall departures, which is a real selection-bias risk, not a neutral
row-count loss. Fix: "usable" now requires only the CORE features
(current-state + the existing 1-step derivatives, which need just 1
prior row); the 3-second-window alpha_trend_* columns remain in the
table but are allowed to be NaN where a full window isn't available.
Anyone using the window features must apply that additional filter
themselves -- documented explicitly in ml_feature_schema_v2.json and in
the printed row-count report below, rather than silently baked into a
single "usable" number.

Outputs:
    data/ml/ml_dataset_v2.parquet          (all usable rows, all splits, with a 'split' column)
    data/ml/ml_train_v2.parquet            (usable rows whose trajectory_id is in the train split)
    data/ml/ml_val_v2.parquet
    data/ml/ml_test_v2.parquet
    data/metadata/ml_feature_schema_v2.json

Run with:
    python scripts/prepare_ml_dataset.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from aeroguard.aircraft import Aircraft
from aeroguard_dataset.events import resolve_stall_boundary
from aeroguard_dataset.features import causal_backward_difference

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "processed_dataset_v2.parquet")
MANIFEST_PATH = os.path.join(PROJECT_ROOT, "data", "splits", "split_manifest_v2.csv")
ML_DIR = os.path.join(PROJECT_ROOT, "data", "ml")
SCHEMA_PATH = os.path.join(PROJECT_ROOT, "data", "metadata", "ml_feature_schema_v2.json")

DT = 0.01  # matches generation_config_v2.json; fixed timestep, so all windows below are exact integer step counts
ALPHA_TREND_WINDOWS_S = [1.0, 2.0, 3.0]  # evidence-based (see module docstring), alpha only

# Forbidden columns: must never appear as an INPUT feature (leakage or
# not physically observable to a real onboard system). Checked
# programmatically by tests/test_ml_dataset_prep.py, not just documented.
FORBIDDEN_INPUT_COLUMNS = frozenset({
    "future_stall_5s", "future_stall_5s_available", "time_to_stall", "is_unsafe",
    "generation_mode", "termination_reason", "whether_stall_occurred",
    "whether_validity_envelope_was_exceeded", "time_of_first_stall",
    "maximum_alpha", "minimum_alpha", "minimum_airspeed", "maximum_airspeed",
    "maximum_abs_gamma", "n_steps", "duration_actual_s", "random_seed",
    "trajectory_id", "split",
})

CURRENT_STATE_FEATURES = ["V", "alpha", "gamma", "pitch_rate", "altitude", "elevator", "throttle", "stall_margin"]
CAUSAL_DYNAMIC_FEATURES = ["dV_dt", "dalpha_dt", "dgamma_dt", "dq_dt"]
HISTORY_FEATURES = [f"alpha_trend_{int(w)}s" for w in ALPHA_TREND_WINDOWS_S]
ALL_INPUT_FEATURES = CURRENT_STATE_FEATURES + CAUSAL_DYNAMIC_FEATURES + HISTORY_FEATURES

# CORE features define "usable" (see module docstring for why the
# window features do NOT): every one needs at most 1 prior row of the
# same trajectory, so they cost almost no rows/trajectories.
CORE_FEATURES = CURRENT_STATE_FEATURES + CAUSAL_DYNAMIC_FEATURES


def compute_causal_trend(df: pd.DataFrame, col: str, window_s: float, dt: float) -> pd.Series:
    """trend(t) = (x(t) - x(t - window_s)) / window_s, computed per
    trajectory (groupby BEFORE shift -- this is what prevents a window
    from ever reaching into a different trajectory's rows; see
    tests/test_ml_dataset_prep.py::test_naive_ungrouped_shift_would_leak
    for a deliberate demonstration of the bug this avoids)."""
    window_steps = round(window_s / dt)
    lagged = df.groupby("trajectory_id")[col].shift(window_steps)
    return (df[col] - lagged) / window_s


def compute_time_to_stall(df: pd.DataFrame) -> pd.Series:
    """time_to_stall(t) = time of the first is_unsafe==True row strictly
    after t, minus t, within the SAME trajectory; NaN if no such row
    exists in the trajectory's remaining recorded telemetry. Every
    trajectory is fully simulated to its actual end, so this is always
    well-defined (no "insufficient future data" case, unlike
    future_stall_5s's fixed 5s window)."""
    out = np.full(len(df), np.nan)
    for tid, g in df.groupby("trajectory_id", sort=False):
        idx = g.index.to_numpy()
        times = g["time"].to_numpy()
        is_unsafe = g["is_unsafe"].to_numpy()
        unsafe_positions = np.where(is_unsafe)[0]
        if len(unsafe_positions) == 0:
            continue
        n = len(g)
        # for each row position i, find the first unsafe position strictly > i
        insertion = np.searchsorted(unsafe_positions, np.arange(n), side="right")
        has_future = insertion < len(unsafe_positions)
        future_positions = np.where(has_future, unsafe_positions[np.clip(insertion, 0, len(unsafe_positions) - 1)], -1)
        local_result = np.full(n, np.nan)
        local_result[has_future] = times[future_positions[has_future]] - times[np.arange(n)[has_future]]
        out[idx] = local_result
    return pd.Series(out, index=df.index)


def build_ml_table(verbose: bool = True) -> pd.DataFrame:
    df = pd.read_parquet(PROCESSED_PATH)
    manifest = pd.read_csv(MANIFEST_PATH)

    df = df.sort_values(["trajectory_id", "time"]).reset_index(drop=True)

    if verbose:
        print(f"Loaded {len(df):,} rows from {PROCESSED_PATH}")

    # --- 1. new causal derivatives (reusing the validated backward-difference fn) ---
    df["dgamma_dt"] = df.groupby("trajectory_id")["gamma"].transform(lambda s: causal_backward_difference(s.to_numpy(), DT))
    df["dq_dt"] = df.groupby("trajectory_id")["pitch_rate"].transform(lambda s: causal_backward_difference(s.to_numpy(), DT))

    # --- 2. alpha-only causal trend/history features (evidence-based) ---
    for w in ALPHA_TREND_WINDOWS_S:
        df[f"alpha_trend_{int(w)}s"] = compute_causal_trend(df, "alpha", w, DT)

    # --- 3. secondary target ---
    df["time_to_stall"] = compute_time_to_stall(df)

    # --- 4. merge split assignment ---
    n_before = len(df)
    df = df.merge(manifest, on="trajectory_id", how="left", validate="many_to_one")
    assert len(df) == n_before, "merge with split manifest changed row count"
    assert df["split"].notna().all(), "some trajectory_id(s) missing from split manifest"

    # --- 5. usable-row filter (CORE features only -- see module docstring) ---
    usable = df["future_stall_5s_available"].astype(bool)
    for feat in CORE_FEATURES:
        usable = usable & df[feat].notna()

    if verbose:
        n_traj_total = df["trajectory_id"].nunique()
        n_traj_usable = df.loc[usable, "trajectory_id"].nunique()
        print(f"Usable rows (target available AND all {len(CORE_FEATURES)} core features present): {usable.sum():,} / {len(df):,}")
        print(f"  trajectories contributing >=1 usable row: {n_traj_usable} / {n_traj_total}")

        full_window = usable & df["alpha_trend_3s"].notna()
        n_traj_full_window = df.loc[full_window, "trajectory_id"].nunique()
        print(f"  of those, rows that ALSO have the full 3s alpha-trend history: {full_window.sum():,} "
              f"({n_traj_full_window} trajectories) -- window features are optional/nullable, apply this filter yourself if you use them")

    ml_df = df.loc[usable].reset_index(drop=True)

    keep_cols = (
        ["trajectory_id", "time", "split"]
        + ALL_INPUT_FEATURES
        + ["future_stall_5s", "future_stall_5s_available", "time_to_stall", "is_unsafe"]
    )
    return ml_df[keep_cols]


def build_schema(aircraft: Aircraft) -> dict:
    boundary = resolve_stall_boundary(aircraft)

    def feat(physical_meaning, units, source, causal, derived, formula=None, window=None):
        return {
            "physical_meaning": physical_meaning, "units": units, "source_columns": source,
            "causal": causal, "derived": derived, "derivation_formula": formula,
            "history_window": window, "allowed_as_ml_input": True,
        }

    schema = {
        "dataset_version": "stage2-v0.2-calibration",
        "ml_dataset_version": "ml_v2.0",
        "stall_boundary_alpha_rad": boundary.alpha_at_cl_peak,
        "stall_boundary_alpha_deg": float(np.degrees(boundary.alpha_at_cl_peak)),
        "identifiers": {
            "trajectory_id": {"description": "unique flight identifier; join key only", "allowed_as_ml_input": False},
            "time": {"description": "seconds since trajectory start", "allowed_as_ml_input": False,
                      "reason_excluded": "causal (no leakage) but excluded from the baseline input set: risks the model learning WHEN control pulses tend to start in the synthetic generator, not real physics -- a dataset-generation-process artifact, not a physical precursor."},
            "split": {"description": "train/val/test assignment", "allowed_as_ml_input": False},
        },
        "input_features": {
            "V": feat("airspeed", "m/s", ["V"], True, False),
            "alpha": feat("angle of attack = theta - gamma", "rad", ["alpha"], True, False),
            "gamma": feat("flight-path angle", "rad", ["gamma"], True, False),
            "pitch_rate": feat("pitch rate q", "rad/s", ["pitch_rate"], True, False),
            "altitude": feat("altitude h", "m", ["altitude"], True, False,
                              formula=None) | {"caveat": "This simplified physics model uses a CONSTANT air density (rho) everywhere -- altitude never feeds back into lift/drag/thrust (verified by inspecting aerodynamics.py). Measured correlation with future_stall_5s: 0.023 (~0). Included for completeness / as a feature-importance sanity check (a correctly-behaving model should assign it near-zero importance), NOT because it is expected to help."},
            "elevator": feat("commanded elevator deflection", "rad", ["elevator"], True, False),
            "throttle": feat("commanded throttle", "dimensionless [0-1]", ["throttle"], True, False),
            "stall_margin": feat("alpha_at_cl_peak - alpha", "rad", ["stall_margin"], True, False,
                                  formula="stall_margin = alpha_at_cl_peak - alpha") | {
                "caveat": "EXACT algebraic duplicate of alpha (verified: stall_margin = 0.28044 - alpha, residual 0.0, correlation with alpha = -1.0000 exactly). Included for interpretability (directly reads as 'degrees of margin left'), but do not feed both alpha and stall_margin to a linear model -- pick one. Tree models are insensitive to this redundancy."},
            "dV_dt": feat("causal backward-difference dV/dt", "m/s^2", ["V"], True, True,
                           formula="(V[t]-V[t-1])/dt", window="1 step (0.01s), same-trajectory"),
            "dalpha_dt": feat("causal backward-difference dalpha/dt", "rad/s", ["alpha"], True, True,
                               formula="(alpha[t]-alpha[t-1])/dt", window="1 step (0.01s), same-trajectory"),
            "dgamma_dt": feat("causal backward-difference dgamma/dt", "rad/s", ["gamma"], True, True,
                               formula="(gamma[t]-gamma[t-1])/dt", window="1 step (0.01s), same-trajectory") | {
                "note": "NEW in this stage; computed with the same validated causal_backward_difference() function already used for dV_dt/dalpha_dt in Stage 2."},
            "dq_dt": feat("causal backward-difference d(pitch_rate)/dt", "rad/s^2", ["pitch_rate"], True, True,
                           formula="(q[t]-q[t-1])/dt", window="1 step (0.01s), same-trajectory") | {
                "note": "NEW in this stage; same function as dV_dt/dalpha_dt."},
            "alpha_trend_1s": feat("causal alpha trend over the last 1 second", "rad/s", ["alpha"], True, True,
                                    formula="(alpha[t]-alpha[t-1.0s])/1.0", window="100 steps (1.0s), same-trajectory") | {
                "note": "Evidence-based addition: correlation with future_stall_5s = 0.242 (vs. 0.127 for the 1-step dalpha_dt).",
                "nullable": True, "nullable_reason": "NaN for the first 1.0s of every trajectory (insufficient history)."},
            "alpha_trend_2s": feat("causal alpha trend over the last 2 seconds", "rad/s", ["alpha"], True, True,
                                    formula="(alpha[t]-alpha[t-2.0s])/2.0", window="200 steps (2.0s), same-trajectory") | {
                "note": "correlation with future_stall_5s = 0.338.",
                "nullable": True, "nullable_reason": "NaN for the first 2.0s of every trajectory (insufficient history)."},
            "alpha_trend_3s": feat("causal alpha trend over the last 3 seconds", "rad/s", ["alpha"], True, True,
                                    formula="(alpha[t]-alpha[t-3.0s])/3.0", window="300 steps (3.0s), same-trajectory") | {
                "note": "correlation with future_stall_5s = 0.422, the strongest of any tested window/variable combination.",
                "nullable": True,
                "nullable_reason": (
                    "NaN for the first 3.0s of every trajectory. IMPORTANT: this is NOT included in the "
                    "'usable row' filter, unlike every other input feature -- requiring it would combine with "
                    "the 5s future-label requirement to impose an implicit ~8s minimum trajectory duration, "
                    "which was found to disproportionately erase the fastest 'stall'-regime departures "
                    "(138/250 stall trajectories entirely excluded, vs 14/250 near_boundary, 0/500 normal). "
                    "Rows/trajectories in ml_dataset_v2.parquet may have this column as NaN; filter on "
                    "alpha_trend_3s.notna() yourself if your model needs it."
                )},
        },
        "targets": {
            "future_stall_5s": {
                "description": "1.0 if is_unsafe is True for any sample strictly after t and up to t+5s within the SAME trajectory; 0.0 if not; NaN if fewer than 5s of future telemetry remain in that (possibly early-terminated) trajectory.",
                "type": "binary classification target (primary)",
                "window": "(t, t+5s], same trajectory only",
                "unavailable_representation": "NaN in future_stall_5s; future_stall_5s_available=False",
                "independently_re_derived": "Yes -- rebuilt from raw telemetry with a fresh implementation (no shared code with the original), 0 mismatches across all 1000 trajectories / 1,753,615 rows.",
                "allowed_as_ml_input": False,
            },
            "future_stall_5s_available": {
                "description": "boolean mask: whether future_stall_5s is defined for this row. Used only to select trainable rows, never as a model input.",
                "allowed_as_ml_input": False,
            },
            "time_to_stall": {
                "description": "time (s) until the first future is_unsafe==True row in the SAME trajectory; NaN if no such row exists in the trajectory's remaining recorded telemetry.",
                "type": "continuous secondary target (auxiliary)",
                "note": "Unlike future_stall_5s, always fully determined (every trajectory is simulated to its actual end) -- no 'insufficient future data' case. Useful for lead-time-style analysis (e.g. bucketing into >5s/3-5s/1-3s/<1s/after-crossing), but is NOT capped at 5s, so it is not a drop-in replacement for future_stall_5s.",
                "allowed_as_ml_input": False,
            },
        },
        "excluded_columns_and_reasons": {
            "theta": "EXACT duplicate: theta = alpha + gamma (verified, residual 2e-16). Redundant once alpha and gamma are both present.",
            "vertical_speed": "EXACT duplicate: vertical_speed = V*sin(gamma) (verified, residual 0.0).",
            "thrust": "EXACT duplicate: thrust = clip(throttle,0,1)*thrust_max (verified, residual 0.0, correlation 1.0 with throttle).",
            "is_unsafe": "Redundant with alpha (deterministic function of alpha) AND conceptually circular for a 'predict before it happens' framing (it IS the current-instant version of the event being predicted).",
            "generation_mode (regime)": "Not physically observable to a real aircraft -- it is a label of HOW this synthetic trajectory was generated (normal/near_boundary/stall), not a measurable physical quantity. Using it would let a model key on the synthetic-data-generation process rather than physics.",
            "termination_reason, whether_validity_envelope_was_exceeded, whether_stall_occurred, time_of_first_stall": "Computed from (or reveal) the trajectory's FUTURE/eventual outcome. Severe leakage if used as inputs.",
            "maximum_alpha, minimum_alpha, minimum_airspeed, maximum_airspeed, maximum_abs_gamma": "Aggregated over the ENTIRE trajectory including rows after t. Severe leakage.",
            "n_steps, duration_actual_s": "Reveal the eventual total trajectory length / whether-and-when it terminates early. Leakage.",
            "random_seed": "Constant across the whole dataset; zero information.",
            "initial_airspeed, initial_altitude, initial_alpha, trim_throttle, trim_elevator": "Causal (t=0 facts) but static per-trajectory; current state already captures what matters physically, and including them in a row-level model risks the model keying on trajectory identity rather than current physics.",
        },
    }
    return schema


def main():
    os.makedirs(ML_DIR, exist_ok=True)

    aircraft = Aircraft()
    ml_df = build_ml_table(verbose=True)

    print("\nSplit sizes (usable rows):")
    for split_name in ["train", "val", "test"]:
        sub = ml_df[ml_df["split"] == split_name]
        n_pos = int((sub["future_stall_5s"] == 1.0).sum())
        n_neg = int((sub["future_stall_5s"] == 0.0).sum())
        n_traj = sub["trajectory_id"].nunique()
        print(f"  {split_name:5s}: {len(sub):>9,} rows, {n_traj:4d} trajectories, "
              f"{n_pos:>7,} positive ({100*n_pos/(n_pos+n_neg):.2f}%), {n_neg:>9,} negative")

    dataset_path = os.path.join(ML_DIR, "ml_dataset_v2.parquet")
    ml_df.to_parquet(dataset_path, index=False)
    print(f"\nSaved -> {dataset_path} ({len(ml_df):,} rows)")

    for split_name in ["train", "val", "test"]:
        sub = ml_df[ml_df["split"] == split_name].drop(columns=["split"])
        path = os.path.join(ML_DIR, f"ml_{split_name}_v2.parquet")
        sub.to_parquet(path, index=False)
        print(f"Saved -> {path} ({len(sub):,} rows)")

    schema = build_schema(aircraft)
    with open(SCHEMA_PATH, "w") as f:
        json.dump(schema, f, indent=2)
    print(f"Saved -> {SCHEMA_PATH}")

    return ml_df


if __name__ == "__main__":
    main()
