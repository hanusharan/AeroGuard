"""Reconciliation Task 3/4 — independent reproducibility check of RUN A's
Candidate D (gradual_D_two_stage), using the EXACT implementation that
produced RUN A: aeroguard_dataset.config.GRADUAL_APPROACH_CANDIDATES /
make_v03_calibration_config (seed 20260817, n=175, 5 candidates @ 20%
each), the same call scripts/calibrate_v3.py makes.

This does NOT modify scripts/calibrate_v3.py, aeroguard_dataset/config.py,
or any RUN A/RUN B output. It regenerates the identical 175-trajectory
batch (deterministic RNG) so we have the raw per-step telemetry to
inspect -- calibrate_v3.py itself never saved raw trajectories to disk,
only aggregate stats -- and applies two precursor-duration definitions
side by side to isolate whether RUN A's very different numbers are a
real effect or a metric-definition artifact:

  (a) RUN A's own definition (scripts/calibrate_v3.py:
      compute_ramp_durations / onset_to_cross): first index where RAW
      (signed) alpha >= 8deg, restricted to t <= t_cross, then
      t_cross - t8. Silently drops any trajectory whose crossing is
      negative-alpha (alpha never >= +8deg): "above8" stays empty.
  (b) RUN B's definition (scripts/precursor_diagnosis.py /
      scripts/calibrate_v03.py): direction-aligned -- flip alpha's sign
      by the sign of alpha AT the crossing sample first, then take the
      LAST index where direction-aligned alpha < 8deg before crossing
      (robust to early transient touches of 8deg that don't lead
      immediately into the final approach; handles negative-alpha
      crossings).

Also computes the full Task-3 metric list and classifies each Candidate-D
crossing as "clean approach" vs "runaway excursion" by inspecting gamma's
behavior through the approach window, for Task 4.

Outputs -> outputs/v03_calibration/ (new files only, doesn't touch RUN A
or RUN B's existing files):
  candidate_d_reproduction_raw.parquet
  candidate_d_reproduction_metadata.csv
  candidate_d_metric_comparison.csv
  candidate_d_trajectory_classification.csv
  plots/03_candidate_d_reproduction_traces.png (Task 4)
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
from aeroguard_dataset.config import GRADUAL_APPROACH_CANDIDATES, compute_validity_envelope, make_v03_calibration_config
from aeroguard_dataset.dataset_builder import build_dataset
from aeroguard_dataset.events import resolve_stall_boundary
from aeroguard_dataset.trajectory_sim import (
    TERMINATION_COMPLETED,
    TERMINATION_GAMMA_EXCEEDED,
    TERMINATION_GROUND_CONTACT,
    TERMINATION_LOW_AIRSPEED,
)

OUT_DIR = os.path.join(paths.OUTPUTS_DIR, "v03_calibration")
os.makedirs(os.path.join(OUT_DIR, "plots"), exist_ok=True)
CANDIDATE = "gradual_D_two_stage"


def run_a_definition(alpha_deg_signed: np.ndarray, t: np.ndarray, t_cross: float):
    """Exact replica of scripts/calibrate_v3.py's onset_to_cross logic."""
    pre = t <= t_cross + 1e-9
    above8 = np.where(alpha_deg_signed[pre] >= 8.0)[0]
    if len(above8) == 0:
        return np.nan
    t8 = t[pre][above8[0]]
    return t_cross - t8


def run_b_definition(alpha_rad_signed: np.ndarray, t: np.ndarray, t_cross: float, cross_sign: float):
    """Direction-aligned, last-below-threshold-before-crossing (RUN B /
    scripts/precursor_diagnosis.py's crossing_ramp_mechanism method)."""
    a_dir = alpha_rad_signed * cross_sign
    i_cross = int(np.argmin(np.abs(t - t_cross)))
    below8 = np.where(a_dir[:i_cross] < np.radians(8.0))[0]
    if len(below8) == 0:
        return np.nan
    t8 = t[below8[-1]]
    return t_cross - t8


def main():
    aircraft = Aircraft()
    boundary = resolve_stall_boundary(aircraft)
    boundary_rad = boundary.alpha_at_cl_peak
    boundary_deg = np.degrees(boundary_rad)
    cfg = make_v03_calibration_config(n_trajectories=175)  # seed=20260817 default, matches RUN A exactly
    v_stall, v_floor, gamma_max_rad = compute_validity_envelope(aircraft, cfg)

    print(f"Reproducing RUN A's exact calibration call: seed={cfg.seed}, n={cfg.n_trajectories}, "
          f"candidates={list(cfg.regime_proportions.keys())}")
    raw_df, processed_df, metadata_df, v0_check = build_dataset(
        cfg, verbose=True, regime_control_configs=GRADUAL_APPROACH_CANDIDATES
    )

    # Save raw data this time (RUN A's calibrate_v3.py never did) so results are inspectable.
    raw_df.to_parquet(os.path.join(OUT_DIR, "candidate_d_reproduction_raw.parquet"), index=False)
    metadata_df.to_csv(os.path.join(OUT_DIR, "candidate_d_reproduction_metadata.csv"), index=False)

    meta_d = metadata_df[metadata_df["generation_mode"] == CANDIDATE].copy()
    raw_d = raw_df[raw_df["trajectory_id"].isin(meta_d["trajectory_id"])]
    n = len(meta_d)
    print(f"\n=== {CANDIDATE}: n={n} (RUN A reported n=35 for this candidate at n_total=175) ===")

    # ---- reproduce RUN A's own top-line numbers first (sanity check) ----
    term_counts = meta_d["termination_reason"].value_counts()
    pct_crossed = 100.0 * meta_d["whether_stall_occurred"].mean()
    pct_gamma = 100.0 * term_counts.get(TERMINATION_GAMMA_EXCEEDED, 0) / n
    pct_ground = 100.0 * term_counts.get(TERMINATION_GROUND_CONTACT, 0) / n
    pct_low_v = 100.0 * term_counts.get(TERMINATION_LOW_AIRSPEED, 0) / n
    pct_completed = 100.0 * term_counts.get(TERMINATION_COMPLETED, 0) / n
    print(f"crossed={pct_crossed:.1f}%  gamma_term={pct_gamma:.1f}%  ground_contact={pct_ground:.1f}%  "
          f"low_v={pct_low_v:.1f}%  completed={pct_completed:.1f}%")
    print(f"(RUN A reported: crossed=22.9%  gamma_term=31.4%  ground_contact=0%  completed=68.6%)")

    # ---- crossing-level analysis with BOTH definitions ----
    crossers = meta_d[meta_d["whether_stall_occurred"] & meta_d["time_of_first_stall"].notna()]
    raw_idx = raw_d.set_index("trajectory_id")

    rows = []
    for _, m in crossers.iterrows():
        tid = m["trajectory_id"]
        t_cross = m["time_of_first_stall"]
        g = raw_idx.loc[[tid]].sort_values("time")
        t = g["time"].to_numpy()
        a = g["alpha"].to_numpy()
        gamma = g["gamma"].to_numpy()
        elev = g["elevator"].to_numpy()
        alpha_deg = np.degrees(a)

        i_cross = int(np.argmin(np.abs(t - t_cross)))
        cross_sign = 1.0 if a[i_cross] >= 0 else -1.0
        gamma_at_cross_deg = np.degrees(gamma[i_cross])
        max_alpha_deg = float(np.degrees(np.max(np.abs(a))))

        run_a_dur = run_a_definition(alpha_deg, t, t_cross)
        run_b_dur = run_b_definition(a, t, t_cross, cross_sign)

        # Task 4: clean-approach vs runaway classification. "Clean": alpha
        # approach is monotonic-ish (direction-aligned alpha mostly
        # non-decreasing in the 5s pre-crossing window) AND gamma at
        # crossing stays well inside the envelope (|gamma| < 35deg, a
        # 10deg margin under the 45deg cap) AND termination is not a
        # gamma/ground-contact excursion. "Runaway": gamma blows past this
        # margin, or the trajectory terminates via the validity envelope
        # shortly after crossing (a zoom climb/dive that happens to pass
        # through the boundary rather than a controlled approach to it).
        window_mask = (t <= t_cross) & (t >= t_cross - 5.0)
        a_dir_window = a[window_mask] * cross_sign
        monotonic_frac = float(np.mean(np.diff(a_dir_window) >= -np.radians(0.5))) if window_mask.sum() > 1 else np.nan
        is_clean = (abs(gamma_at_cross_deg) < 35.0) and (m["termination_reason"] == TERMINATION_COMPLETED or
                                                            (m["termination_reason"] == TERMINATION_GAMMA_EXCEEDED and
                                                             (m["duration_actual_s"] - t_cross) > 0.3))

        rows.append({
            "trajectory_id": tid, "cross_sign": cross_sign, "t_cross": t_cross,
            "termination_reason": m["termination_reason"], "duration_actual_s": m["duration_actual_s"],
            "run_a_onset8_to_cross_s": run_a_dur, "run_b_onset8_to_cross_s": run_b_dur,
            "gamma_at_cross_deg": gamma_at_cross_deg, "max_alpha_deg": max_alpha_deg,
            "monotonic_frac_5s_window": monotonic_frac, "time_from_cross_to_end_s": m["duration_actual_s"] - t_cross,
            "is_clean_approach": is_clean,
        })
    cmp_df = pd.DataFrame(rows)
    cmp_df.to_csv(os.path.join(OUT_DIR, "candidate_d_trajectory_classification.csv"), index=False)

    print(f"\n=== crossing-level detail (n_crossings={len(cmp_df)}) ===")
    print(cmp_df[["trajectory_id", "cross_sign", "termination_reason", "run_a_onset8_to_cross_s",
                   "run_b_onset8_to_cross_s", "gamma_at_cross_deg", "max_alpha_deg", "is_clean_approach"]]
          .to_string(index=False))

    n_negative_sign = int((cmp_df["cross_sign"] < 0).sum())
    n_runA_nan = int(cmp_df["run_a_onset8_to_cross_s"].isna().sum())
    n_runB_nan = int(cmp_df["run_b_onset8_to_cross_s"].isna().sum())
    print(f"\nnegative-alpha (nose-down) crossings: {n_negative_sign}/{len(cmp_df)}")
    print(f"RUN A definition: {n_runA_nan} crossings silently dropped (no positive alpha>=8deg found pre-crossing)")
    print(f"RUN B definition: {n_runB_nan} crossings dropped (direction-aligned, should be ~0 unless alpha started >=8deg)")

    valid_a = cmp_df["run_a_onset8_to_cross_s"].dropna()
    valid_b = cmp_df["run_b_onset8_to_cross_s"].dropna()
    print(f"\nRUN A def: n_used={len(valid_a)}, median={valid_a.median() if len(valid_a) else float('nan'):.2f}s, "
          f">=2s: {(valid_a>=2).mean():.1%}  >=3s: {(valid_a>=3).mean():.1%}  "
          f">=4s: {(valid_a>=4).mean():.1%}  >=5s: {(valid_a>=5).mean():.1%}" if len(valid_a) else "RUN A def: no valid rows")
    print(f"RUN B def: n_used={len(valid_b)}, median={valid_b.median() if len(valid_b) else float('nan'):.2f}s, "
          f">=2s: {(valid_b>=2).mean():.1%}  >=3s: {(valid_b>=3).mean():.1%}  "
          f">=4s: {(valid_b>=4).mean():.1%}  >=5s: {(valid_b>=5).mean():.1%}" if len(valid_b) else "RUN B def: no valid rows")

    n_clean = int(cmp_df["is_clean_approach"].sum())
    print(f"\nclean-approach classification: {n_clean}/{len(cmp_df)} clean, {len(cmp_df)-n_clean}/{len(cmp_df)} runaway/ambiguous")

    # ---- other Task-3 metrics ----
    max_alpha_all_deg = np.degrees(meta_d["maximum_alpha"].abs())
    small_margin_mask = (max_alpha_all_deg >= boundary_deg) & (max_alpha_all_deg <= boundary_deg + 5.0)
    print(f"\nmax-alpha distribution (deg, whole candidate n={n}): "
          f"mean={max_alpha_all_deg.mean():.2f} median={max_alpha_all_deg.median():.2f} "
          f"p25={np.percentile(max_alpha_all_deg,25):.2f} p75={np.percentile(max_alpha_all_deg,75):.2f} "
          f"p90={np.percentile(max_alpha_all_deg,90):.2f}")
    print(f"small-margin crossing rate (max|alpha| within 5deg over boundary): {100*small_margin_mask.mean():.1f}%")

    summary = {
        "n_trajectories": n, "n_crossings": len(cmp_df),
        "pct_crossed": pct_crossed, "pct_gamma_term": pct_gamma, "pct_ground_contact": pct_ground,
        "pct_low_v": pct_low_v, "pct_completed": pct_completed,
        "n_negative_alpha_crossings": n_negative_sign,
        "run_a_def_n_used": len(valid_a), "run_a_def_median_s": float(valid_a.median()) if len(valid_a) else None,
        "run_a_def_frac_ge2s": float((valid_a >= 2).mean()) if len(valid_a) else None,
        "run_a_def_frac_ge3s": float((valid_a >= 3).mean()) if len(valid_a) else None,
        "run_a_def_frac_ge4s": float((valid_a >= 4).mean()) if len(valid_a) else None,
        "run_a_def_frac_ge5s": float((valid_a >= 5).mean()) if len(valid_a) else None,
        "run_b_def_n_used": len(valid_b), "run_b_def_median_s": float(valid_b.median()) if len(valid_b) else None,
        "run_b_def_frac_ge2s": float((valid_b >= 2).mean()) if len(valid_b) else None,
        "run_b_def_frac_ge3s": float((valid_b >= 3).mean()) if len(valid_b) else None,
        "run_b_def_frac_ge4s": float((valid_b >= 4).mean()) if len(valid_b) else None,
        "run_b_def_frac_ge5s": float((valid_b >= 5).mean()) if len(valid_b) else None,
        "n_clean_approach": n_clean, "n_runaway_or_ambiguous": len(cmp_df) - n_clean,
        "max_alpha_deg_mean": float(max_alpha_all_deg.mean()), "max_alpha_deg_median": float(max_alpha_all_deg.median()),
        "small_margin_crossing_rate_pct": float(100 * small_margin_mask.mean()),
    }
    pd.DataFrame([summary]).to_csv(os.path.join(OUT_DIR, "candidate_d_metric_comparison.csv"), index=False)

    # ---- Task 4 plots: full state traces for several representative trajectories ----
    sample_ids = cmp_df["trajectory_id"].tolist()[:6]
    fig, axes = plt.subplots(len(sample_ids), 5, figsize=(22, 3.2 * len(sample_ids)))
    if len(sample_ids) == 1:
        axes = axes[None, :]
    for row_i, tid in enumerate(sample_ids):
        g = raw_idx.loc[[tid]].sort_values("time")
        t_cross = cmp_df.loc[cmp_df.trajectory_id == tid, "t_cross"].iloc[0]
        term = cmp_df.loc[cmp_df.trajectory_id == tid, "termination_reason"].iloc[0]
        t = g["time"].to_numpy()
        alpha_deg = np.degrees(g["alpha"].to_numpy())
        gamma_deg = np.degrees(g["gamma"].to_numpy())
        elev = g["elevator"].to_numpy()
        alt = g["altitude"].to_numpy()
        V = g["V"].to_numpy()

        for col, (arr, name) in enumerate(zip([alpha_deg, elev, gamma_deg, alt, V],
                                                 ["alpha [deg]", "elevator [rad]", "gamma [deg]", "altitude [m]", "V [m/s]"])):
            ax = axes[row_i, col]
            ax.plot(t, arr, lw=1)
            ax.axvline(t_cross, color="red", ls="--", lw=0.8, label="crossing")
            if name == "alpha [deg]":
                for lvl, c in [(8, "orange"), (12, "goldenrod"), (boundary_deg, "red"), (-8, "orange"), (-12, "goldenrod"), (-boundary_deg, "red")]:
                    ax.axhline(lvl, color=c, ls=":", lw=0.6)
            ax.set_title(f"{tid} ({term})\n{name}" if col == 0 else name, fontsize=7)
            ax.tick_params(labelsize=6)
    fig.suptitle(f"Candidate D ({CANDIDATE}) reproduction: representative crossing trajectories (Task 4)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "plots", "03_candidate_d_reproduction_traces.png"), dpi=110)
    plt.close(fig)

    print(f"\nDone. Outputs in {OUT_DIR} (+ plots/03_candidate_d_reproduction_traces.png)")


if __name__ == "__main__":
    main()
