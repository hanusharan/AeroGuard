"""Phase 4 — v0.3 CANDIDATE calibration (NOT a full dataset generation).

Generates a single small (~175-trajectory) batch split evenly across the 5
GRADUAL_APPROACH_CANDIDATES regimes (aeroguard_dataset/config.py), using the
existing, unmodified generation pipeline (dataset_builder.build_dataset) --
only the control-profile parameters differ from v0.1/v0.2; aeroguard/ physics
is untouched, and v0.2 (data/*_v2.*) is never read for writing, only for the
baseline-comparison numbers already computed by scripts/diagnose_precursor.py.

Writes nothing to data/. Plots and stats go to outputs/v03_calibration/.

Run with:
    python scripts/calibrate_v3.py
"""

import json
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
from aeroguard_dataset.config import (
    GRADUAL_APPROACH_CANDIDATES,
    compute_validity_envelope,
    make_v03_calibration_config,
)
from aeroguard_dataset.dataset_builder import build_dataset
from aeroguard_dataset.events import resolve_stall_boundary
from aeroguard_dataset.trajectory_sim import (
    TERMINATION_COMPLETED,
    TERMINATION_GAMMA_EXCEEDED,
    TERMINATION_GROUND_CONTACT,
    TERMINATION_LOW_AIRSPEED,
)

N_TOTAL = 175  # 35 per candidate; within the 150-200 total budget
OUT_DIR = os.path.join(paths.OUTPUTS_DIR, "v03_calibration")

# "Onset" threshold for the ramp-duration / precursor-fraction metric: alpha
# rising through 8deg (the same threshold used in Phase 1's ramp-timing
# analysis of the real v0.2 data, so v0.2 vs v0.3-candidate numbers are
# directly comparable). Precursor duration = time from alpha=8deg (rising)
# to the actual boundary crossing.
ONSET_ALPHA_DEG = 8.0


def compute_ramp_durations(raw_df, crossing_meta):
    durations_8_16 = []
    durations_12_cross = []
    for tid, tcross in zip(crossing_meta["trajectory_id"], crossing_meta["time_of_first_stall"]):
        g = raw_df[raw_df["trajectory_id"] == tid].sort_values("time")
        alpha_deg = np.degrees(g["alpha"].values)
        t = g["time"].values
        pre = t <= tcross + 1e-9
        alpha_pre = alpha_deg[pre]
        t_pre = t[pre]
        above8 = np.where(alpha_pre >= ONSET_ALPHA_DEG)[0]
        above16 = np.where(alpha_pre >= 16.0)[0]
        above12 = np.where(alpha_pre >= 12.0)[0]
        if len(above8) and len(above16):
            t8, t16 = t_pre[above8[0]], t_pre[above16[0]]
            if t16 >= t8:
                durations_8_16.append({"trajectory_id": tid, "duration_s": t16 - t8})
        if len(above12):
            t12 = t_pre[above12[0]]
            durations_12_cross.append({"trajectory_id": tid, "duration_s": tcross - t12})
    return pd.DataFrame(durations_8_16), pd.DataFrame(durations_12_cross)


def compute_candidate_stats(label, raw_df, processed_df, metadata_df, boundary_deg, v_floor, gamma_max_rad):
    n = len(metadata_df)
    term_counts = metadata_df["termination_reason"].value_counts()

    crossing_meta = metadata_df[metadata_df["whether_stall_occurred"] & metadata_df["time_of_first_stall"].notna()]
    n_crossed = len(crossing_meta)

    pct_crossed = 100.0 * n_crossed / n
    pct_gamma_term = 100.0 * term_counts.get(TERMINATION_GAMMA_EXCEEDED, 0) / n
    pct_ground_contact = 100.0 * term_counts.get(TERMINATION_GROUND_CONTACT, 0) / n
    pct_low_v = 100.0 * term_counts.get(TERMINATION_LOW_AIRSPEED, 0) / n
    pct_completed = 100.0 * term_counts.get(TERMINATION_COMPLETED, 0) / n

    max_alpha_deg = np.degrees(metadata_df["maximum_alpha"].abs())

    spent_meaningful_time = []
    for tid, g in raw_df.groupby("trajectory_id"):
        alpha_deg = np.degrees(g["alpha"])
        dt = g["time"].iloc[1] - g["time"].iloc[0] if len(g) > 1 else 0.01
        seconds_in_zone = np.sum((alpha_deg >= 8) & (alpha_deg <= 16)) * dt
        spent_meaningful_time.append(seconds_in_zone > 0.5)
    frac_8_16 = 100.0 * np.mean(spent_meaningful_time)

    small_margin_mask = (max_alpha_deg >= boundary_deg) & (max_alpha_deg <= boundary_deg + 5.0)
    frac_small_margin = 100.0 * small_margin_mask.mean()

    dur_8_16, dur_12_cross = compute_ramp_durations(raw_df, crossing_meta)

    def frac_ge(df, seconds):
        if len(df) == 0:
            return None
        return 100.0 * float((df["duration_s"] >= seconds).mean())

    n_pos = int((processed_df["future_stall_5s"] == 1.0).sum())
    n_neg = int((processed_df["future_stall_5s"] == 0.0).sum())
    positive_rate = 100.0 * n_pos / (n_pos + n_neg) if (n_pos + n_neg) > 0 else float("nan")

    stats = {
        "label": label,
        "n_trajectories": n,
        "n_crossed": n_crossed,
        "pct_crossed_boundary": pct_crossed,
        "pct_terminated_gamma": pct_gamma_term,
        "pct_terminated_ground_contact": pct_ground_contact,
        "pct_terminated_low_airspeed": pct_low_v,
        "pct_completed_full_duration": pct_completed,
        "max_alpha_deg_mean": float(max_alpha_deg.mean()),
        "max_alpha_deg_median": float(max_alpha_deg.median()),
        "frac_spent_meaningful_time_8_16deg_pct": frac_8_16,
        "frac_small_margin_crossing_0_5deg_over_pct": frac_small_margin,
        "n_with_8_16_ramp": len(dur_8_16),
        "median_alpha_8_to_16_deg_s": float(dur_8_16["duration_s"].median()) if len(dur_8_16) else None,
        "mean_alpha_8_to_16_deg_s": float(dur_8_16["duration_s"].mean()) if len(dur_8_16) else None,
        "n_with_12_to_cross": len(dur_12_cross),
        "median_alpha_12_to_crossing_s": float(dur_12_cross["duration_s"].median()) if len(dur_12_cross) else None,
        # precursor-duration fractions use the alpha=8deg -> crossing window,
        # i.e. dur_8_16 EXTENDED to the crossing, not just to 16deg -- see below
        "future_stall_5s_positive_rate_pct_of_available": positive_rate,
        "future_stall_5s_n_positive": n_pos,
        "future_stall_5s_n_negative": n_neg,
    }

    # precursor fraction: time from alpha=8deg onset to the ACTUAL crossing
    # (not just to 16deg) -- this is the metric the decision gate cares about.
    onset_to_cross = []
    for tid, tcross in zip(crossing_meta["trajectory_id"], crossing_meta["time_of_first_stall"]):
        g = raw_df[raw_df["trajectory_id"] == tid].sort_values("time")
        alpha_deg = np.degrees(g["alpha"].values)
        t = g["time"].values
        pre = t <= tcross + 1e-9
        above8 = np.where(alpha_deg[pre] >= ONSET_ALPHA_DEG)[0]
        if len(above8):
            t8 = t[pre][above8[0]]
            onset_to_cross.append(tcross - t8)
    onset_to_cross = pd.Series(onset_to_cross, dtype=float)
    stats["n_with_onset_to_crossing"] = int(len(onset_to_cross))
    stats["median_onset_8deg_to_crossing_s"] = float(onset_to_cross.median()) if len(onset_to_cross) else None
    for sec in [1, 2, 3, 4, 5]:
        stats[f"frac_crossings_with_ge_{sec}s_precursor_pct"] = (
            100.0 * float((onset_to_cross >= sec).mean()) if len(onset_to_cross) else None
        )

    return stats, onset_to_cross


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    aircraft = Aircraft()
    boundary = resolve_stall_boundary(aircraft)
    boundary_deg = np.degrees(boundary.alpha_at_cl_peak)
    cfg = make_v03_calibration_config(n_trajectories=N_TOTAL)
    v_stall, v_floor, gamma_max_rad = compute_validity_envelope(aircraft, cfg)

    print(f"v0.3 CANDIDATE calibration: n_total={N_TOTAL}, seed={cfg.seed}")
    print(f"regimes: {list(cfg.regime_proportions.keys())}")
    print(f"stall boundary = {boundary_deg:.2f} deg, V_stall={v_stall:.2f}, v_floor={v_floor:.2f}\n")

    raw_df, processed_df, metadata_df, v0_check = build_dataset(
        cfg, verbose=True, regime_control_configs=GRADUAL_APPROACH_CANDIDATES
    )

    all_stats = []
    onset_by_candidate = {}
    for name in GRADUAL_APPROACH_CANDIDATES:
        meta_c = metadata_df[metadata_df["generation_mode"] == name]
        ids = set(meta_c["trajectory_id"])
        raw_c = raw_df[raw_df["trajectory_id"].isin(ids)]
        proc_c = processed_df[processed_df["trajectory_id"].isin(ids)]
        stats, onset = compute_candidate_stats(name, raw_c, proc_c, meta_c, boundary_deg, v_floor, gamma_max_rad)
        all_stats.append(stats)
        onset_by_candidate[name] = onset

        print(f"--- {name} (n={stats['n_trajectories']}) ---")
        print(f"  % crossed boundary          : {stats['pct_crossed_boundary']:.1f}%")
        print(f"  % gamma-envelope terminated  : {stats['pct_terminated_gamma']:.1f}%")
        print(f"  % ground-contact terminated  : {stats['pct_terminated_ground_contact']:.1f}%")
        print(f"  median alpha 8->16deg (s)    : {stats['median_alpha_8_to_16_deg_s']}")
        print(f"  median alpha8->crossing (s)  : {stats['median_onset_8deg_to_crossing_s']}")
        for sec in [1, 2, 3, 4, 5]:
            print(f"  frac crossings >= {sec}s precursor : {stats[f'frac_crossings_with_ge_{sec}s_precursor_pct']}")
        print()

    stats_df = pd.DataFrame(all_stats)
    stats_df.to_csv(os.path.join(OUT_DIR, "v03_calibration_stats.csv"), index=False)
    print(f"Wrote {os.path.join(OUT_DIR, 'v03_calibration_stats.csv')}")

    with open(os.path.join(OUT_DIR, "v03_calibration_stats.json"), "w") as f:
        json.dump(all_stats, f, indent=2)

    # ---- plot: precursor-duration distributions per candidate ----
    fig, ax = plt.subplots(figsize=(9, 5))
    data_to_plot, labels = [], []
    for name, onset in onset_by_candidate.items():
        if len(onset) > 0:
            data_to_plot.append(onset.values)
            labels.append(f"{name}\n(n={len(onset)})")
    if data_to_plot:
        ax.boxplot(data_to_plot, tick_labels=labels, showmeans=True)
    ax.set_ylabel("precursor duration: alpha=8deg onset -> crossing [s]")
    ax.set_title("v0.3 candidates: precursor duration distribution")
    ax.tick_params(axis="x", labelsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "01_precursor_duration_by_candidate.png"), dpi=120)
    plt.close(fig)

    # ---- plot: sample alpha(t) traces per candidate, aligned to crossing ----
    fig, axes = plt.subplots(1, len(GRADUAL_APPROACH_CANDIDATES), figsize=(22, 4.5), sharey=True)
    rng = np.random.default_rng(cfg.seed)
    for ax, name in zip(axes, GRADUAL_APPROACH_CANDIDATES):
        meta_c = metadata_df[
            (metadata_df["generation_mode"] == name)
            & metadata_df["whether_stall_occurred"]
            & metadata_df["time_of_first_stall"].notna()
        ]
        sample_ids = meta_c["trajectory_id"].sample(n=min(10, len(meta_c)), random_state=cfg.seed) if len(meta_c) else []
        for tid in sample_ids:
            tcross = meta_c.loc[meta_c["trajectory_id"] == tid, "time_of_first_stall"].iloc[0]
            g = raw_df[raw_df["trajectory_id"] == tid].sort_values("time")
            t_rel = g["time"].values - tcross
            mask = (t_rel >= -6) & (t_rel <= 1)
            ax.plot(t_rel[mask], np.degrees(g["alpha"].values[mask]), alpha=0.6, lw=1)
        ax.axhline(boundary_deg, color="red", ls="--", lw=0.8)
        ax.axvline(0, color="black", ls=":", lw=0.8)
        ax.set_title(name.replace("gradual_", ""), fontsize=8)
        ax.set_xlabel("t rel. crossing [s]")
    axes[0].set_ylabel("alpha [deg]")
    fig.suptitle("v0.3 candidates: alpha(t) aligned to crossing (up to 10 samples each)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "02_alpha_traces_by_candidate.png"), dpi=120)
    plt.close(fig)

    print(f"\nDone. Outputs in {OUT_DIR}")


if __name__ == "__main__":
    main()
