"""Generalization experiment, Phase 3 — SMALL calibration (150
trajectories) of the alternative single-pulse, duration-capped precursor
mechanism (aeroguard_dataset/control_profiles_alt_single.py).

Mirrors scripts/calibrate_candidate_d_v3.py's structure and metric
definitions exactly (reuses its corrected_precursor_duration,
transition_time, and classify_trajectory functions unchanged, by direct
import -- the same dip-aware / direction-aligned precursor metric and
4-way dive-then-zoom/runaway classification already established for
v0.3, per the task's explicit instruction to reuse it rather than
re-derive a new one).

Does NOT modify aeroguard/, aeroguard_dataset/config.py,
aeroguard_dataset/control_profiles.py, control_profiles_candidate_d_v2.py,
control_profiles_candidate_d_v3.py, dataset_builder.py, or any existing
data/ or outputs/ml_v03 / outputs/v03_calibration file. Writes only to
outputs/ml_v03_generalization/calibration/ (new, isolated).

Run with:
    python scripts/calibrate_alt_single.py
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
from aeroguard_dataset.control_profiles_alt_single import build_alt_single_pulse_profile
from aeroguard_dataset.events import first_unsafe_index, resolve_stall_boundary
from aeroguard_dataset.features import compute_features_for_trajectory
from aeroguard_dataset.paths import trim_level_flight
from aeroguard_dataset.trajectory_sim import (
    TERMINATION_COMPLETED,
    TERMINATION_GAMMA_EXCEEDED,
    TERMINATION_GROUND_CONTACT,
    TERMINATION_LOW_AIRSPEED,
    simulate_trajectory,
)

# Reuse the exact dip-aware precursor metric and 4-way classification
# already validated for v0.3's own Candidate D calibration -- not
# re-derived here.
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
from calibrate_candidate_d_v3 import classify_trajectory, corrected_precursor_duration, transition_time  # noqa: E402

OUT_DIR = os.path.join(paths.OUTPUTS_DIR, "ml_v03_generalization", "calibration")
os.makedirs(os.path.join(OUT_DIR, "plots"), exist_ok=True)
N_TRAJECTORIES = 150  # within the 100-200 task-specified budget
SEED = 20260817  # same seed convention as every other calibration run
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
        tid = f"altF_cal_{i:04d}"
        V0 = float(rng.uniform(cfg.v0_min, cfg.v0_max))
        h0 = float(rng.uniform(cfg.altitude_min, cfg.altitude_max))
        alpha_trim, throttle_trim, elevator_trim = trim_level_flight(aircraft, V0)
        profile = build_alt_single_pulse_profile(rng, alpha_trim, throttle_trim, elevator_trim, DURATION_S)

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
            "trajectory_id": tid, "generation_mode": "gradual_alt_single_capped",
            "initial_airspeed": V0, "initial_altitude": h0,
            "maximum_alpha": float(np.max(result.alpha)) if len(result.alpha) else np.nan,
            "minimum_alpha": float(np.min(result.alpha)) if len(result.alpha) else np.nan,
            "maximum_abs_gamma": float(np.max(np.abs(result.gamma))) if len(result.gamma) else np.nan,
            "whether_stall_occurred": stall_occurred, "time_of_first_stall": time_of_first_stall,
            "termination_reason": result.termination_reason, "duration_actual_s": float(result.t[-1]) if len(result.t) else 0.0,
        })

    return pd.concat(raw_frames, ignore_index=True), pd.DataFrame(metadata_rows), boundary, gamma_max_rad


def main():
    print(f"Calibrating alt-single-pulse mechanism: n={N_TRAJECTORIES}, seed={SEED}, dt={DT}, duration={DURATION_S}s")
    raw_df, meta_df, boundary, gamma_max_rad = generate_batch(N_TRAJECTORIES, SEED)
    boundary_deg = np.degrees(boundary.alpha_at_cl_peak)

    raw_df.to_parquet(os.path.join(OUT_DIR, "alt_single_calibration_raw.parquet"), index=False)
    meta_df.to_csv(os.path.join(OUT_DIR, "alt_single_calibration_metadata.csv"), index=False)

    n = len(meta_df)
    term_counts = meta_df["termination_reason"].value_counts()
    pct_crossed = 100.0 * meta_df["whether_stall_occurred"].mean()
    pct_gamma = 100.0 * term_counts.get(TERMINATION_GAMMA_EXCEEDED, 0) / n
    pct_ground = 100.0 * term_counts.get(TERMINATION_GROUND_CONTACT, 0) / n
    pct_low_v = 100.0 * term_counts.get(TERMINATION_LOW_AIRSPEED, 0) / n
    pct_completed = 100.0 * term_counts.get(TERMINATION_COMPLETED, 0) / n
    print(f"\ncrossed={pct_crossed:.1f}%  gamma_term={pct_gamma:.1f}%  ground_contact={pct_ground:.1f}%  "
          f"low_v={pct_low_v:.1f}%  completed={pct_completed:.1f}%  (n={n})")
    print("(reference -- Candidate D v3 gate run: crossed=22.9% gamma_term=31.4% completed=68.6%)")
    print("(reference -- original uncapped single-pulse family A/B/C: gamma_term=63-91%)")

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
    cross_df.to_csv(os.path.join(OUT_DIR, "alt_single_crossing_classification.csv"), index=False)

    print(f"\n=== crossing-level detail (n_crossings={len(cross_df)}) ===")
    if len(cross_df):
        print(cross_df[["trajectory_id", "termination_reason", "corrected_precursor_s", "t_8_to_16_s",
                         "classification", "gamma_at_cross_deg"]].to_string(index=False))

    valid = cross_df["corrected_precursor_s"].dropna() if len(cross_df) else pd.Series(dtype=float)
    print(f"\ncorrected precursor metric: n_used={len(valid)}, median="
          f"{valid.median() if len(valid) else float('nan'):.2f}s" if len(valid) else "\ncorrected precursor metric: n_used=0")
    for sec in [2, 3, 4, 5]:
        frac = (valid >= sec).mean() if len(valid) else float("nan")
        print(f"  >= {sec}s: {frac:.1%}" if len(valid) else f"  >= {sec}s: n/a")

    max_alpha_all = np.degrees(meta_df["maximum_alpha"].abs())
    small_margin = ((max_alpha_all >= boundary_deg) & (max_alpha_all <= boundary_deg + 5.0)).mean()
    print(f"\nsmall-margin crossing rate: {100 * small_margin:.1f}%")
    if len(cross_df):
        print(f"median 8->16deg transition: {cross_df['t_8_to_16_s'].median():.2f}s")
        print(f"median 12->16deg transition: {cross_df['t_12_to_16_s'].median():.2f}s")

    class_counts = cross_df["classification"].value_counts() if len(cross_df) else pd.Series(dtype=int)
    print("\n=== classification counts ===")
    print(class_counts)
    n_clean = int(class_counts.get("gradual_monotonic_low_gamma", 0) + class_counts.get("dip_then_rise", 0))
    n_bad = int(class_counts.get("dive_then_zoom_climb", 0) + class_counts.get("runaway_extreme", 0))
    pct_clean = 100.0 * n_clean / len(cross_df) if len(cross_df) else float("nan")
    pct_dive_then_zoom = 100.0 * class_counts.get("dive_then_zoom_climb", 0) / len(cross_df) if len(cross_df) else float("nan")
    print(f"\nclean (gradual_monotonic_low_gamma + dip_then_rise): {n_clean}/{len(cross_df)} = {pct_clean:.1f}%")
    print(f"dive_then_zoom_climb: {class_counts.get('dive_then_zoom_climb', 0)} = {pct_dive_then_zoom:.1f}%")

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
        "median_8_to_16_s": float(cross_df["t_8_to_16_s"].median()) if len(cross_df) and cross_df["t_8_to_16_s"].notna().any() else None,
        "median_12_to_16_s": float(cross_df["t_12_to_16_s"].median()) if len(cross_df) and cross_df["t_12_to_16_s"].notna().any() else None,
        "small_margin_crossing_rate_pct": float(100 * small_margin),
        "classification_counts": class_counts.to_dict(),
        "pct_clean_crossings": pct_clean,
        "pct_dive_then_zoom_climb": pct_dive_then_zoom,
    }
    pd.DataFrame([summary]).to_json(os.path.join(OUT_DIR, "alt_single_calibration_summary.json"), orient="records", indent=2)
    print(f"\nWrote summary to {os.path.join(OUT_DIR, 'alt_single_calibration_summary.json')}")

    # plots: sample traces of a few crossings, colored/marked by classification
    if len(cross_df):
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
        fig.suptitle("Alt single-pulse mechanism: representative crossings")
        fig.tight_layout()
        fig.savefig(os.path.join(OUT_DIR, "plots", "01_alt_single_traces.png"), dpi=110)
        plt.close(fig)

    print("\nDone.")


if __name__ == "__main__":
    main()
