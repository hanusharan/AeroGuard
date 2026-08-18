"""Reconciliation follow-up calibration (ONE narrowly-scoped test): does
the same-sign / zero-gap pulse fix (aeroguard_dataset/
control_profiles_candidate_d_v2.py) reduce the dive-then-zoom-climb
mechanism found in the original GRADUAL_D_TWO_STAGE candidate?

Generates ~175 trajectories (matching the reconciliation baseline's n and
seed for comparability) using ONLY Candidate D v2 -- no new candidate
family, no dataset write to data/. Reuses the unmodified physics/
generation primitives directly (trim_level_flight, simulate_trajectory,
compute_features_for_trajectory, compute_future_stall_label,
resolve_stall_boundary, compute_validity_envelope) rather than
dataset_builder.build_dataset, since this is a single-candidate run, not
a multi-regime sweep -- dataset_builder.py, config.py, and
control_profiles.py are all untouched.

Evaluates with the corrected (direction-aligned, dip-aware) precursor
metric from the reconciliation report -- NOT the original first-touch
metric -- and classifies every crossing trajectory into one of 4
categories: gradual/monotonic, dip-then-rise, dive-then-zoom-climb,
runaway/extreme.

Outputs -> outputs/v03_calibration/ (new files only).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from aeroguard.aircraft import Aircraft
from aeroguard_dataset import paths
from aeroguard_dataset.config import GenerationConfig, compute_validity_envelope
from aeroguard_dataset.control_profiles_candidate_d_v2 import build_candidate_d_v2_profile
from aeroguard_dataset.events import first_unsafe_index, resolve_stall_boundary
from aeroguard_dataset.features import compute_features_for_trajectory
from aeroguard_dataset.labeling import compute_future_stall_label
from aeroguard_dataset.paths import trim_level_flight
from aeroguard_dataset.trajectory_sim import (
    TERMINATION_COMPLETED,
    TERMINATION_GAMMA_EXCEEDED,
    TERMINATION_GROUND_CONTACT,
    TERMINATION_LOW_AIRSPEED,
    simulate_trajectory,
)

OUT_DIR = os.path.join(paths.OUTPUTS_DIR, "v03_calibration")
os.makedirs(os.path.join(OUT_DIR, "plots"), exist_ok=True)
N_TRAJECTORIES = 175  # same n as the reconciliation baseline (35/candidate x 5)
SEED = 20260817  # same seed as the reconciliation baseline (make_v03_calibration_config default)
DT = 0.01
DURATION_S = 20.0


def generate_batch(n: int, seed: int):
    aircraft = Aircraft()
    boundary = resolve_stall_boundary(aircraft)
    cfg = GenerationConfig()  # defaults: same V0/altitude ranges, dt, duration, gamma envelope as every other run
    v_stall, v_floor, gamma_max_rad = compute_validity_envelope(aircraft, cfg)
    rng = np.random.default_rng(seed)

    raw_frames, metadata_rows = [], []
    for i in range(n):
        tid = f"candD_v2_{i:04d}"
        V0 = float(rng.uniform(cfg.v0_min, cfg.v0_max))
        h0 = float(rng.uniform(cfg.altitude_min, cfg.altitude_max))
        alpha_trim, throttle_trim, elevator_trim = trim_level_flight(aircraft, V0)
        profile = build_candidate_d_v2_profile(rng, alpha_trim, throttle_trim, elevator_trim, DURATION_S)

        result = simulate_trajectory(
            trajectory_id=tid, aircraft=aircraft, control_profile=profile,
            V0=V0, gamma0=0.0, alpha0=alpha_trim, h0=h0, q0=0.0,
            duration_s=DURATION_S, dt=DT, v_floor=v_floor, gamma_max_rad=gamma_max_rad,
        )
        features = compute_features_for_trajectory(result, boundary, DT)
        stall_occurred = bool(np.any(features["is_unsafe"]))
        first_idx = first_unsafe_index(result.alpha, boundary)
        time_of_first_stall = float(result.t[first_idx]) if first_idx is not None else None

        raw_frames.append(pd.DataFrame({
            "trajectory_id": tid, "time": result.t, "V": result.V, "alpha": result.alpha,
            "gamma": result.gamma, "altitude": result.altitude, "pitch_rate": result.pitch_rate,
            "elevator": result.elevator, "throttle": result.throttle,
            "dalpha_dt": features["dalpha_dt"],
        }))
        metadata_rows.append({
            "trajectory_id": tid, "generation_mode": "gradual_D_two_stage_v2",
            "initial_airspeed": V0, "initial_altitude": h0,
            "maximum_alpha": float(np.max(result.alpha)) if len(result.alpha) else np.nan,
            "minimum_alpha": float(np.min(result.alpha)) if len(result.alpha) else np.nan,
            "maximum_abs_gamma": float(np.max(np.abs(result.gamma))) if len(result.gamma) else np.nan,
            "whether_stall_occurred": stall_occurred, "time_of_first_stall": time_of_first_stall,
            "termination_reason": result.termination_reason, "duration_actual_s": float(result.t[-1]) if len(result.t) else 0.0,
        })

    return pd.concat(raw_frames, ignore_index=True), pd.DataFrame(metadata_rows), boundary, gamma_max_rad


def corrected_precursor_duration(a_rad: np.ndarray, t: np.ndarray, t_cross: float, cross_sign: float):
    """Direction-aligned, dip-aware: last below-8deg sample strictly before
    the final approach to crossing (reconciliation report's RUN B metric)."""
    a_dir = a_rad * cross_sign
    i_cross = int(np.argmin(np.abs(t - t_cross)))
    below8 = np.where(a_dir[:i_cross] < np.radians(8.0))[0]
    if len(below8) == 0:
        return np.nan
    return t_cross - t[below8[-1]]


def _dip_aware_onset_time(a_rad: np.ndarray, t: np.ndarray, t_cross: float, cross_sign: float, threshold_deg: float):
    """Last time direction-aligned alpha was below threshold_deg, strictly
    before crossing (dip-aware: robust to early transient touches)."""
    a_dir = a_rad * cross_sign
    i_cross = int(np.argmin(np.abs(t - t_cross)))
    below = np.where(a_dir[:i_cross] < np.radians(threshold_deg))[0]
    if len(below) == 0:
        return np.nan
    return t[below[-1]]


def transition_time(a_rad: np.ndarray, t: np.ndarray, t_cross: float, cross_sign: float, lo_deg: float, hi_deg: float):
    """Duration between the dip-aware onset of lo_deg and of hi_deg (both
    measured the same way, so e.g. 8->16 = onset(16) - onset(8))."""
    t_lo = _dip_aware_onset_time(a_rad, t, t_cross, cross_sign, lo_deg)
    t_hi = _dip_aware_onset_time(a_rad, t, t_cross, cross_sign, hi_deg)
    if np.isnan(t_lo) or np.isnan(t_hi):
        return np.nan
    return t_hi - t_lo


def classify_trajectory(a_rad: np.ndarray, gamma_rad: np.ndarray, t: np.ndarray, t_cross: float, cross_sign: float,
                         termination_reason: str):
    """4-way classification per Phase 3C: gradual/monotonic-low-gamma,
    dip-then-rise, dive-then-zoom-climb, runaway/extreme."""
    i_cross = int(np.argmin(np.abs(t - t_cross)))
    window = (t >= max(0, t_cross - 8.0)) & (t <= t_cross)
    a_dir_deg = np.degrees(a_rad[window] * cross_sign)
    gamma_deg = np.degrees(gamma_rad[window])
    max_abs_gamma = float(np.max(np.abs(gamma_deg))) if window.any() else np.nan
    gamma_sign_flip = bool(np.any(gamma_deg > 15) and np.any(gamma_deg < -15))  # swings through both signs strongly
    diffs = np.diff(a_dir_deg)
    frac_retreating = float(np.mean(diffs < -0.3)) if len(diffs) else 0.0  # fraction of steps alpha visibly retreats

    if max_abs_gamma >= 40.0 or gamma_sign_flip:
        return "dive_then_zoom_climb" if gamma_sign_flip else "runaway_extreme"
    if frac_retreating > 0.05:  # more than 5% of pre-crossing steps show a real retreat
        return "dip_then_rise"
    return "gradual_monotonic_low_gamma"


def main():
    print(f"Generating Candidate D v2: n={N_TRAJECTORIES}, seed={SEED}, dt={DT}, duration={DURATION_S}s")
    raw_df, meta_df, boundary, gamma_max_rad = generate_batch(N_TRAJECTORIES, SEED)
    boundary_deg = np.degrees(boundary.alpha_at_cl_peak)

    raw_df.to_parquet(os.path.join(OUT_DIR, "candidate_d_v2_raw.parquet"), index=False)
    meta_df.to_csv(os.path.join(OUT_DIR, "candidate_d_v2_metadata.csv"), index=False)

    n = len(meta_df)
    term_counts = meta_df["termination_reason"].value_counts()
    pct_crossed = 100.0 * meta_df["whether_stall_occurred"].mean()
    pct_gamma = 100.0 * term_counts.get(TERMINATION_GAMMA_EXCEEDED, 0) / n
    pct_ground = 100.0 * term_counts.get(TERMINATION_GROUND_CONTACT, 0) / n
    pct_low_v = 100.0 * term_counts.get(TERMINATION_LOW_AIRSPEED, 0) / n
    pct_completed = 100.0 * term_counts.get(TERMINATION_COMPLETED, 0) / n
    print(f"\ncrossed={pct_crossed:.1f}%  gamma_term={pct_gamma:.1f}%  ground_contact={pct_ground:.1f}%  "
          f"low_v={pct_low_v:.1f}%  completed={pct_completed:.1f}%  (n={n})")
    print(f"(baseline Candidate D v1: crossed=22.9% gamma_term=31.4% ground_contact=0% completed=68.6%)")

    crossers = meta_df[meta_df["whether_stall_occurred"] & meta_df["time_of_first_stall"].notna()]
    raw_idx = raw_df.set_index("trajectory_id")

    rows = []
    for _, m in crossers.iterrows():
        tid = m["trajectory_id"]
        t_cross = m["time_of_first_stall"]
        g = raw_idx.loc[[tid]].sort_values("time")
        t = g["time"].to_numpy()
        a = g["alpha"].to_numpy()
        gamma = g["gamma"].to_numpy()
        i_cross = int(np.argmin(np.abs(t - t_cross)))
        cross_sign = 1.0 if a[i_cross] >= 0 else -1.0

        dur = corrected_precursor_duration(a, t, t_cross, cross_sign)
        t_8_16 = transition_time(a, t, t_cross, cross_sign, 8.0, 16.0)
        t_12_16 = transition_time(a, t, t_cross, cross_sign, 12.0, 16.0)
        cls = classify_trajectory(a, gamma, t, t_cross, cross_sign, m["termination_reason"])
        max_alpha_deg = float(np.degrees(np.max(np.abs(a))))
        gamma_at_cross_deg = float(np.degrees(gamma[i_cross]))

        rows.append({
            "trajectory_id": tid, "cross_sign": cross_sign, "t_cross": t_cross,
            "termination_reason": m["termination_reason"], "corrected_precursor_s": dur,
            "t_8_to_16_s": t_8_16, "t_12_to_16_s": t_12_16, "classification": cls,
            "max_alpha_deg": max_alpha_deg, "gamma_at_cross_deg": gamma_at_cross_deg,
        })
    cross_df = pd.DataFrame(rows)
    cross_df.to_csv(os.path.join(OUT_DIR, "candidate_d_v2_crossing_classification.csv"), index=False)

    print(f"\n=== crossing-level detail (n_crossings={len(cross_df)}) ===")
    print(cross_df[["trajectory_id", "termination_reason", "corrected_precursor_s", "t_8_to_16_s",
                     "classification", "gamma_at_cross_deg"]].to_string(index=False))

    valid = cross_df["corrected_precursor_s"].dropna()
    print(f"\ncorrected precursor metric: n_used={len(valid)}, median={valid.median() if len(valid) else float('nan'):.2f}s")
    for sec in [2, 3, 4, 5]:
        frac = (valid >= sec).mean() if len(valid) else float("nan")
        print(f"  >= {sec}s: {frac:.1%}")

    max_alpha_all = np.degrees(meta_df["maximum_alpha"].abs())
    small_margin = ((max_alpha_all >= boundary_deg) & (max_alpha_all <= boundary_deg + 5.0)).mean()
    print(f"\nsmall-margin crossing rate: {100*small_margin:.1f}%")
    print(f"median 8->16deg transition: {cross_df['t_8_to_16_s'].median():.2f}s")
    print(f"median 12->16deg transition: {cross_df['t_12_to_16_s'].median():.2f}s")

    print("\n=== classification counts ===")
    print(cross_df["classification"].value_counts())

    summary = {
        "n_trajectories": n, "n_crossings": len(cross_df),
        "pct_crossed": pct_crossed, "pct_gamma_term": pct_gamma, "pct_ground_contact": pct_ground,
        "pct_low_v": pct_low_v, "pct_completed": pct_completed,
        "corrected_precursor_n_used": int(len(valid)),
        "corrected_precursor_median_s": float(valid.median()) if len(valid) else None,
        "corrected_precursor_frac_ge2s": float((valid >= 2).mean()) if len(valid) else None,
        "corrected_precursor_frac_ge3s": float((valid >= 3).mean()) if len(valid) else None,
        "corrected_precursor_frac_ge4s": float((valid >= 4).mean()) if len(valid) else None,
        "corrected_precursor_frac_ge5s": float((valid >= 5).mean()) if len(valid) else None,
        "median_8_to_16_s": float(cross_df["t_8_to_16_s"].median()) if cross_df["t_8_to_16_s"].notna().any() else None,
        "median_12_to_16_s": float(cross_df["t_12_to_16_s"].median()) if cross_df["t_12_to_16_s"].notna().any() else None,
        "small_margin_crossing_rate_pct": float(100 * small_margin),
        "classification_counts": cross_df["classification"].value_counts().to_dict(),
        "n_gradual_monotonic_low_gamma": int((cross_df["classification"] == "gradual_monotonic_low_gamma").sum()),
    }
    pd.DataFrame([summary]).to_json(os.path.join(OUT_DIR, "candidate_d_v2_summary.json"), orient="records", indent=2)
    print(f"\nWrote summary to {os.path.join(OUT_DIR, 'candidate_d_v2_summary.json')}")

    # plots: sample traces of a few crossings, colored/marked by classification
    sample_ids = cross_df["trajectory_id"].tolist()[:6]
    fig, axes = plt.subplots(len(sample_ids), 3, figsize=(14, 3.0 * len(sample_ids)))
    if len(sample_ids) == 1:
        axes = axes[None, :]
    for row_i, tid in enumerate(sample_ids):
        g = raw_idx.loc[[tid]].sort_values("time")
        row = cross_df[cross_df.trajectory_id == tid].iloc[0]
        t = g["time"].to_numpy()
        alpha_deg = np.degrees(g["alpha"].to_numpy())
        gamma_deg = np.degrees(g["gamma"].to_numpy())
        elev = g["elevator"].to_numpy()
        for col, (arr, name) in enumerate(zip([alpha_deg, elev, gamma_deg], ["alpha [deg]", "elevator [rad]", "gamma [deg]"])):
            ax = axes[row_i, col]
            ax.plot(t, arr, lw=1)
            ax.axvline(row["t_cross"], color="red", ls="--", lw=0.8)
            if col == 0:
                for lvl in [8, 12, boundary_deg, -8, -12, -boundary_deg]:
                    ax.axhline(lvl, color="orange", ls=":", lw=0.5)
            ax.set_title(f"{tid} [{row['classification']}]" if col == 0 else name, fontsize=7)
            ax.tick_params(labelsize=6)
    fig.suptitle("Candidate D v2: representative crossings (same-sign, zero-gap fix)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "plots", "04_candidate_d_v2_traces.png"), dpi=110)
    plt.close(fig)

    print(f"\nDone.")


if __name__ == "__main__":
    main()
