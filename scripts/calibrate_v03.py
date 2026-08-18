"""Phase 4 -- v0.3 candidate control-profile CALIBRATION (small batches only).

Generates ~30 trajectories per candidate (5 candidates x 30 = 150 total,
within the 150-200 budget) using the candidates defined in
aeroguard_dataset/control_profiles_v03_candidates.py, all under the
"near_boundary" regime slot (100% of each candidate batch, since each
candidate IS a near_boundary variant being screened).

Writes nothing to data/ and does not touch v0.1/v0.2 data, aeroguard/
physics, aeroguard_dataset/config.py, or any existing output. All
generated data/plots/stats are new files under outputs/v03_calibration/.

Run with:
    python scripts/calibrate_v03.py
"""
import dataclasses
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from aeroguard.aircraft import Aircraft
from aeroguard_dataset import paths
from aeroguard_dataset.config import GenerationConfig, compute_validity_envelope
from aeroguard_dataset.control_profiles_v03_candidates import V03_CANDIDATES
from aeroguard_dataset.dataset_builder import build_dataset
from aeroguard_dataset.events import resolve_stall_boundary
from aeroguard_dataset.trajectory_sim import (
    TERMINATION_COMPLETED,
    TERMINATION_GAMMA_EXCEEDED,
    TERMINATION_GROUND_CONTACT,
    TERMINATION_LOW_AIRSPEED,
)

N_PER_CANDIDATE = 30
BASE_SEED = 20260818  # distinct from the v0.1/v0.2 generation seed (20260817)
OUT_DIR = os.path.join(paths.OUTPUTS_DIR, "v03_calibration")

ALPHA_8DEG_RAD = np.radians(8.0)
ALPHA_12DEG_RAD = np.radians(12.0)


def make_candidate_config(name: str, seed_offset: int) -> GenerationConfig:
    return dataclasses.replace(
        GenerationConfig(),
        seed=BASE_SEED + seed_offset,
        n_trajectories=N_PER_CANDIDATE,
        dataset_version=f"v0.3-calibration-{name}",
        regime_proportions={"near_boundary": 1.0},
    )


def ramp_metrics(raw_df: pd.DataFrame, metadata_df: pd.DataFrame, alpha_stall_rad: float):
    """Per-crossing-trajectory alpha8->cross / alpha12->cross timing, and
    fraction of crossings with a genuine >=1s/2s/3s precursor window --
    THE key Phase-4 metric. Direction-aligned (nose-up vs nose-down
    crossings), same method as outputs/precursor_diagnosis/
    crossing_ramp_mechanism.csv."""
    crossers = metadata_df[metadata_df["whether_stall_occurred"]]
    raw_idx = raw_df.set_index("trajectory_id")
    rows = []
    for _, m in crossers.iterrows():
        tid = m["trajectory_id"]
        g = raw_idx.loc[[tid]]
        t = g["time"].to_numpy()
        a = g["alpha"].to_numpy()
        unsafe = np.abs(a) > alpha_stall_rad
        if not unsafe.any():
            continue
        i_cross = int(np.argmax(unsafe))
        t_cross = t[i_cross]
        sign = 1.0 if a[i_cross] >= 0 else -1.0
        a_dir = a * sign
        below8 = np.where(a_dir[:i_cross] < ALPHA_8DEG_RAD)[0]
        below12 = np.where(a_dir[:i_cross] < ALPHA_12DEG_RAD)[0]
        t_alpha8 = t[below8[-1]] if len(below8) else np.nan
        t_alpha12 = t[below12[-1]] if len(below12) else np.nan
        rows.append({
            "trajectory_id": tid,
            "time_alpha8_to_cross_s": (t_cross - t_alpha8) if not np.isnan(t_alpha8) else np.nan,
            "time_alpha12_to_cross_s": (t_cross - t_alpha12) if not np.isnan(t_alpha12) else np.nan,
        })
    return pd.DataFrame(rows)


def compute_stats(raw_df, processed_df, metadata_df, boundary, label):
    n = len(metadata_df)
    boundary_deg = np.degrees(boundary.alpha_at_cl_peak)
    term_counts = metadata_df["termination_reason"].value_counts()
    pct_crossed = 100.0 * metadata_df["whether_stall_occurred"].mean()
    pct_gamma = 100.0 * term_counts.get(TERMINATION_GAMMA_EXCEEDED, 0) / n
    pct_ground = 100.0 * term_counts.get(TERMINATION_GROUND_CONTACT, 0) / n
    pct_low_v = 100.0 * term_counts.get(TERMINATION_LOW_AIRSPEED, 0) / n
    pct_completed = 100.0 * term_counts.get(TERMINATION_COMPLETED, 0) / n

    max_alpha_deg = np.degrees(metadata_df["maximum_alpha"].abs())
    max_gamma_deg = np.degrees(metadata_df["maximum_abs_gamma"])

    spent_meaningful_time = []
    for tid, g in raw_df.groupby("trajectory_id"):
        alpha_deg = np.degrees(g["alpha"]).abs()
        dt_local = g["time"].iloc[1] - g["time"].iloc[0] if len(g) > 1 else 0.01
        seconds_in_zone = np.sum((alpha_deg >= 8) & (alpha_deg <= 16)) * dt_local
        spent_meaningful_time.append(seconds_in_zone > 0.5)
    frac_8_16 = 100.0 * np.mean(spent_meaningful_time)

    small_margin_mask = (max_alpha_deg >= boundary_deg) & (max_alpha_deg <= boundary_deg + 5.0)
    frac_small_margin = 100.0 * small_margin_mask.mean()

    n_pos = int((processed_df["future_stall_5s"] == 1.0).sum())
    n_neg = int((processed_df["future_stall_5s"] == 0.0).sum())
    positive_rate = 100.0 * n_pos / (n_pos + n_neg) if (n_pos + n_neg) > 0 else float("nan")

    ramp_df = ramp_metrics(raw_df, metadata_df, boundary.alpha_at_cl_peak)
    n_crossings_with_ramp_data = len(ramp_df)
    if n_crossings_with_ramp_data > 0:
        v8 = ramp_df["time_alpha8_to_cross_s"].dropna()
        median_alpha8_to_cross = float(v8.median()) if len(v8) else float("nan")
        v12 = ramp_df["time_alpha12_to_cross_s"].dropna()
        median_alpha12_to_cross = float(v12.median()) if len(v12) else float("nan")
        frac_ge1s = float((v8 >= 1.0).mean()) if len(v8) else float("nan")
        frac_ge2s = float((v8 >= 2.0).mean()) if len(v8) else float("nan")
        frac_ge3s = float((v8 >= 3.0).mean()) if len(v8) else float("nan")
    else:
        median_alpha8_to_cross = median_alpha12_to_cross = float("nan")
        frac_ge1s = frac_ge2s = frac_ge3s = float("nan")

    V_mean = float(raw_df["V"].mean())
    gamma_deg_mean_abs = float(np.degrees(raw_df["gamma"]).abs().mean())

    return {
        "label": label,
        "n_trajectories": n,
        "pct_crossed_boundary": pct_crossed,
        "pct_terminated_gamma": pct_gamma,
        "pct_terminated_ground_contact": pct_ground,
        "pct_terminated_low_airspeed": pct_low_v,
        "pct_completed_full_duration": pct_completed,
        "max_alpha_deg_mean": float(max_alpha_deg.mean()),
        "max_alpha_deg_median": float(max_alpha_deg.median()),
        "max_gamma_deg_mean": float(max_gamma_deg.mean()),
        "max_gamma_deg_median": float(max_gamma_deg.median()),
        "frac_spent_meaningful_time_8_16deg_pct": frac_8_16,
        "frac_small_margin_crossing_0_5deg_over_pct": frac_small_margin,
        "future_stall_5s_positive_rate_pct_of_available": positive_rate,
        "future_stall_5s_n_positive": n_pos,
        "future_stall_5s_n_negative": n_neg,
        "n_crossing_trajectories": int(metadata_df["whether_stall_occurred"].sum()),
        "n_crossings_with_ramp_data": n_crossings_with_ramp_data,
        "median_time_alpha8_to_cross_s": median_alpha8_to_cross,
        "median_time_alpha12_to_cross_s": median_alpha12_to_cross,
        "frac_crossings_with_ge1s_precursor": frac_ge1s,
        "frac_crossings_with_ge2s_precursor": frac_ge2s,
        "frac_crossings_with_ge3s_precursor": frac_ge3s,
        "V_mean_m_s": V_mean,
        "abs_gamma_deg_mean": gamma_deg_mean_abs,
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    aircraft = Aircraft()
    boundary = resolve_stall_boundary(aircraft)

    all_stats = []
    all_raw = []
    all_meta = []

    for i, (name, cand_cfg) in enumerate(V03_CANDIDATES.items()):
        cfg = make_candidate_config(name, seed_offset=i)
        v_stall, v_floor, gamma_max_rad = compute_validity_envelope(aircraft, cfg)
        print(f"\n=== {name}: n={N_PER_CANDIDATE}, seed={cfg.seed} ===")
        print(f"  elevator: mag=[{cand_cfg.elevator.magnitude_min:.2f},{cand_cfg.elevator.magnitude_max:.2f}] rad, "
              f"rise=[{cand_cfg.elevator.rise_s_min:.1f},{cand_cfg.elevator.rise_s_max:.1f}]s, "
              f"hold=[{cand_cfg.elevator.hold_s_min:.1f},{cand_cfg.elevator.hold_s_max:.1f}]s, "
              f"fall=[{cand_cfg.elevator.fall_s_min:.1f},{cand_cfg.elevator.fall_s_max:.1f}]s")

        raw_df, processed_df, metadata_df, _ = build_dataset(
            cfg, verbose=False, regime_control_configs={"near_boundary": cand_cfg}
        )
        raw_df["candidate"] = name
        metadata_df["candidate"] = name
        processed_df["candidate"] = name

        stats = compute_stats(raw_df, processed_df, metadata_df, boundary, name)
        all_stats.append(stats)
        all_raw.append(raw_df)
        all_meta.append(metadata_df)

        print(f"  crossed={stats['pct_crossed_boundary']:.1f}%  gamma_term={stats['pct_terminated_gamma']:.1f}%  "
              f"ground_contact={stats['pct_terminated_ground_contact']:.1f}%")
        print(f"  median alpha8->cross={stats['median_time_alpha8_to_cross_s']:.2f}s  "
              f"median alpha12->cross={stats['median_time_alpha12_to_cross_s']:.2f}s")
        print(f"  frac crossings >=1s/2s/3s precursor: "
              f"{stats['frac_crossings_with_ge1s_precursor']:.1%} / "
              f"{stats['frac_crossings_with_ge2s_precursor']:.1%} / "
              f"{stats['frac_crossings_with_ge3s_precursor']:.1%}  "
              f"(n_crossings={stats['n_crossing_trajectories']})")

    stats_df = pd.DataFrame(all_stats)
    stats_df.to_csv(os.path.join(OUT_DIR, "candidate_calibration_summary.csv"), index=False)
    with open(os.path.join(OUT_DIR, "candidate_calibration_summary.json"), "w") as f:
        json.dump(all_stats, f, indent=2)

    combined_raw = pd.concat(all_raw, ignore_index=True)
    combined_meta = pd.concat(all_meta, ignore_index=True)
    combined_raw.to_parquet(os.path.join(OUT_DIR, "calibration_raw_trajectories.parquet"), index=False)
    combined_meta.to_csv(os.path.join(OUT_DIR, "calibration_metadata.csv"), index=False)

    print("\n\n=== SUMMARY (all candidates) ===")
    print(stats_df[["label", "n_trajectories", "pct_crossed_boundary", "pct_terminated_gamma",
                     "median_time_alpha8_to_cross_s", "frac_crossings_with_ge1s_precursor",
                     "frac_crossings_with_ge2s_precursor", "frac_crossings_with_ge3s_precursor"]]
          .to_string(index=False))

    print(f"\nOutputs written to {OUT_DIR}")


if __name__ == "__main__":
    main()
