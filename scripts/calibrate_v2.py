"""Stage 2 v0.2 CALIBRATION experiment (NOT a full dataset generation).

Generates a small (100-200) trajectory batch using the recalibrated
near_boundary control-profile regime (see aeroguard_dataset/config.py:
NEAR_BOUNDARY_CONTROL_CONFIG, REGIME_CONTROL_CONFIGS_V2) and reports the
statistics needed to decide KEEP v0.1 vs ADOPT v0.2.

Writes nothing to data/ (this is explicitly not the full dataset).
Plots and a report go to outputs/dataset_audit_v2_calibration/.

Run with:
    python scripts/calibrate_v2.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from aeroguard.aircraft import Aircraft
from aeroguard_dataset import paths
from aeroguard_dataset.config import (
    GenerationConfig,
    REGIME_CONTROL_CONFIGS,
    REGIME_CONTROL_CONFIGS_V2,
    compute_validity_envelope,
    make_generation_config_v2,
)
from aeroguard_dataset.dataset_builder import build_dataset
from aeroguard_dataset.events import resolve_stall_boundary
from aeroguard_dataset.trajectory_sim import (
    TERMINATION_COMPLETED,
    TERMINATION_GAMMA_EXCEEDED,
    TERMINATION_LOW_AIRSPEED,
)
from aeroguard_dataset.visualize import (
    plot_alpha_distribution,
    plot_alpha_vs_airspeed,
    plot_stall_margin_distribution,
    plot_validity_envelope_violations,
    _plot_sample_trajectories,
    _pick_sample_ids,
)

N_CALIBRATION = 150
OUT_DIR = os.path.join(paths.OUTPUTS_DIR, "dataset_audit_v2_calibration")


def compute_stats(raw_df, processed_df, metadata_df, boundary, v_floor, gamma_max_rad, label):
    n = len(metadata_df)
    boundary_deg = np.degrees(boundary.alpha_at_cl_peak)

    term_counts = metadata_df["termination_reason"].value_counts()
    pct_crossed = 100.0 * metadata_df["whether_stall_occurred"].mean()
    pct_gamma = 100.0 * term_counts.get(TERMINATION_GAMMA_EXCEEDED, 0) / n
    pct_low_v = 100.0 * term_counts.get(TERMINATION_LOW_AIRSPEED, 0) / n
    pct_completed = 100.0 * term_counts.get(TERMINATION_COMPLETED, 0) / n

    max_alpha_deg = np.degrees(metadata_df["maximum_alpha"].abs())
    max_gamma_deg = np.degrees(metadata_df["maximum_abs_gamma"])

    # fraction of trajectories spending >0.5s with alpha in [8,16] deg
    spent_meaningful_time = []
    for tid, g in raw_df.groupby("trajectory_id"):
        alpha_deg = np.degrees(g["alpha"])
        seconds_in_zone = np.sum((alpha_deg >= 8) & (alpha_deg <= 16)) * (g["time"].iloc[1] - g["time"].iloc[0] if len(g) > 1 else 0.01)
        spent_meaningful_time.append(seconds_in_zone > 0.5)
    frac_8_16 = 100.0 * np.mean(spent_meaningful_time)

    small_margin_mask = (max_alpha_deg >= boundary_deg) & (max_alpha_deg <= boundary_deg + 5.0)
    frac_small_margin = 100.0 * small_margin_mask.mean()

    n_pos = int((processed_df["future_stall_5s"] == 1.0).sum())
    n_neg = int((processed_df["future_stall_5s"] == 0.0).sum())
    positive_rate = 100.0 * n_pos / (n_pos + n_neg) if (n_pos + n_neg) > 0 else float("nan")

    stats = {
        "label": label,
        "n_trajectories": n,
        "pct_crossed_boundary": pct_crossed,
        "pct_terminated_gamma": pct_gamma,
        "pct_terminated_low_airspeed": pct_low_v,
        "pct_completed_full_duration": pct_completed,
        "max_alpha_deg_mean": float(max_alpha_deg.mean()),
        "max_alpha_deg_median": float(max_alpha_deg.median()),
        "max_alpha_deg_p25": float(np.percentile(max_alpha_deg, 25)),
        "max_alpha_deg_p75": float(np.percentile(max_alpha_deg, 75)),
        "max_alpha_deg_p90": float(np.percentile(max_alpha_deg, 90)),
        "max_gamma_deg_mean": float(max_gamma_deg.mean()),
        "max_gamma_deg_median": float(max_gamma_deg.median()),
        "max_gamma_deg_p90": float(np.percentile(max_gamma_deg, 90)),
        "frac_spent_meaningful_time_8_16deg_pct": frac_8_16,
        "frac_small_margin_crossing_0_5deg_over_pct": frac_small_margin,
        "future_stall_5s_positive_rate_pct_of_available": positive_rate,
        "future_stall_5s_n_positive": n_pos,
        "future_stall_5s_n_negative": n_neg,
    }
    return stats


def print_stats(stats):
    print(f"\n--- {stats['label']} (n={stats['n_trajectories']}) ---")
    print(f"  % crossed stall boundary          : {stats['pct_crossed_boundary']:.1f}%")
    print(f"  % terminated (gamma envelope)      : {stats['pct_terminated_gamma']:.1f}%")
    print(f"  % terminated (low-airspeed floor)  : {stats['pct_terminated_low_airspeed']:.1f}%")
    print(f"  % completed full duration          : {stats['pct_completed_full_duration']:.1f}%")
    print(f"  max|alpha| deg: mean={stats['max_alpha_deg_mean']:.1f} median={stats['max_alpha_deg_median']:.1f} "
          f"p25={stats['max_alpha_deg_p25']:.1f} p75={stats['max_alpha_deg_p75']:.1f} p90={stats['max_alpha_deg_p90']:.1f}")
    print(f"  max|gamma| deg: mean={stats['max_gamma_deg_mean']:.1f} median={stats['max_gamma_deg_median']:.1f} p90={stats['max_gamma_deg_p90']:.1f}")
    print(f"  fraction spending >0.5s in alpha 8-16 deg : {stats['frac_spent_meaningful_time_8_16deg_pct']:.1f}%")
    print(f"  fraction crossing by small margin (0-5deg): {stats['frac_small_margin_crossing_0_5deg_over_pct']:.1f}%")
    print(f"  future_stall_5s positive rate (of available): {stats['future_stall_5s_positive_rate_pct_of_available']:.1f}%  "
          f"(pos={stats['future_stall_5s_n_positive']}, neg={stats['future_stall_5s_n_negative']})")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    aircraft = Aircraft()
    boundary = resolve_stall_boundary(aircraft)
    cfg_v2 = make_generation_config_v2(n_trajectories=N_CALIBRATION)
    v_stall, v_floor, gamma_max_rad = compute_validity_envelope(aircraft, cfg_v2)

    print(f"v0.2 CALIBRATION run: n={N_CALIBRATION}, seed={cfg_v2.seed}, regimes={cfg_v2.regime_proportions}")
    print(f"stall boundary = {np.degrees(boundary.alpha_at_cl_peak):.2f} deg, V_stall={v_stall:.2f}, v_floor={v_floor:.2f}, gamma_max={np.degrees(gamma_max_rad):.0f} deg")

    raw_df, processed_df, metadata_df, v0_check = build_dataset(
        cfg_v2, verbose=True, regime_control_configs=REGIME_CONTROL_CONFIGS_V2
    )

    stats_v2 = compute_stats(raw_df, processed_df, metadata_df, boundary, v_floor, gamma_max_rad, "v0.2 calibration (near_boundary regime)")
    print_stats(stats_v2)

    print("\nPer-regime breakdown (v0.2):")
    for mode, g in metadata_df.groupby("generation_mode"):
        pct_crossed = 100.0 * g["whether_stall_occurred"].mean()
        pct_gamma = 100.0 * (g["termination_reason"] == TERMINATION_GAMMA_EXCEEDED).mean()
        print(f"  {mode:15s} n={len(g):3d}  crossed={pct_crossed:5.1f}%  gamma_term={pct_gamma:5.1f}%")

    print("\nGenerating calibration plots...")
    plot_alpha_distribution(raw_df, boundary, OUT_DIR)
    os.rename(os.path.join(OUT_DIR, "04_alpha_distribution.png"), os.path.join(OUT_DIR, "02_alpha_distribution.png"))

    plot_alpha_vs_airspeed(processed_df, boundary, OUT_DIR, cfg_v2.seed)
    os.rename(os.path.join(OUT_DIR, "07_alpha_vs_airspeed_scatter.png"), os.path.join(OUT_DIR, "03_alpha_vs_airspeed.png"))

    plot_stall_margin_distribution(processed_df, OUT_DIR)
    os.rename(os.path.join(OUT_DIR, "09_stall_margin_distribution.png"), os.path.join(OUT_DIR, "05_stall_margin_distribution.png"))

    plot_validity_envelope_violations(metadata_df, v_floor, gamma_max_rad, OUT_DIR)
    os.rename(os.path.join(OUT_DIR, "10_validity_envelope_violations.png"), os.path.join(OUT_DIR, "04_termination_reasons.png"))

    # alpha vs time: mix of near_boundary + a few stall samples, since that's
    # the regime this calibration is actually about
    ids = _pick_sample_ids(metadata_df, metadata_df["generation_mode"] == "near_boundary", 8, cfg_v2.seed)
    _plot_sample_trajectories(raw_df, ids, boundary, "v0.2 near_boundary sample trajectories", os.path.join(OUT_DIR, "01_alpha_vs_time_near_boundary_samples.png"))

    print(f"Plots saved to {OUT_DIR}")

    with open(os.path.join(OUT_DIR, "calibration_stats_v2.json"), "w") as f:
        json.dump(stats_v2, f, indent=2)
    print(f"Stats saved to {os.path.join(OUT_DIR, 'calibration_stats_v2.json')}")


if __name__ == "__main__":
    main()
