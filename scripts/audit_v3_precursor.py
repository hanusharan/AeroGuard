"""Full-scale precursor/physical-quality audit for the v0.3 dataset
(data/processed/processed_dataset_v3.parquet + trajectory_metadata_v3.csv),
reusing the exact corrected (direction-aligned, dip-aware) precursor
metric and 4-way physical classification from
scripts/calibrate_candidate_d_v3.py, applied now at full dataset scale
(317 gradual_approach_v3 crossings + 153 stall crossings) instead of the
35-175-trajectory calibration scale.

Read-only: does not modify data/*_v3.* or any other file. Writes new
summary files under outputs/dataset_audit_v3/.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

from aeroguard_dataset import paths
from calibrate_candidate_d_v3 import classify_trajectory, corrected_precursor_duration, transition_time  # noqa: E402

OUT_DIR = os.path.join(paths.OUTPUTS_DIR, "dataset_audit_v3")


def analyze_regime(raw_df, meta_df, regime, boundary_deg):
    crossers = meta_df[(meta_df["generation_mode"] == regime) & meta_df["whether_stall_occurred"] & meta_df["time_of_first_stall"].notna()]
    raw_idx = raw_df[raw_df["trajectory_id"].isin(crossers["trajectory_id"])].set_index("trajectory_id")

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
        max_gamma_pre_deg = float(np.degrees(np.max(np.abs(gamma[:i_cross + 1]))))

        rows.append({
            "trajectory_id": tid, "regime": regime, "cross_sign": cross_sign,
            "termination_reason": m["termination_reason"], "corrected_precursor_s": dur,
            "t_8_to_16_s": t_8_16, "t_12_to_16_s": t_12_16, "classification": cls,
            "max_alpha_deg": max_alpha_deg, "gamma_at_cross_deg": gamma_at_cross_deg,
            "max_gamma_pre_cross_deg": max_gamma_pre_deg,
        })
    return pd.DataFrame(rows)


def main():
    print("Loading v0.3 processed data + metadata (read-only)...")
    raw_df = pd.read_parquet(os.path.join(paths.DATA_RAW_DIR, "raw_telemetry_v3.parquet"))
    meta_df = pd.read_csv(os.path.join(paths.DATA_METADATA_DIR, "trajectory_metadata_v3.csv"))
    boundary_deg = 16.068034017008504  # resolved stall boundary, same aircraft, unchanged

    all_rows = []
    for regime in ["gradual_approach_v3", "stall"]:
        df = analyze_regime(raw_df, meta_df, regime, boundary_deg)
        all_rows.append(df)
        n_crossed = len(df)
        print(f"\n=== {regime}: n_crossings={n_crossed} ===")
        valid = df["corrected_precursor_s"].dropna()
        print(f"corrected precursor: n_used={len(valid)}, median={valid.median() if len(valid) else float('nan'):.2f}s")
        for sec in [0.5, 1, 2, 3, 4, 5]:
            frac = (valid >= sec).mean() if len(valid) else float("nan")
            print(f"  >= {sec}s: {frac:.1%}")
        print(f"median 8->16deg transition: {df['t_8_to_16_s'].median():.2f}s")
        print(f"median 12->16deg transition: {df['t_12_to_16_s'].median():.2f}s")
        print("classification counts:")
        print(df["classification"].value_counts())
        max_alpha_all = np.degrees(meta_df.loc[meta_df["generation_mode"] == regime, "maximum_alpha"].abs())
        small_margin = ((max_alpha_all >= boundary_deg) & (max_alpha_all <= boundary_deg + 5.0)).mean()
        print(f"small-margin crossing rate: {100*small_margin:.1f}%")

    combined = pd.concat(all_rows, ignore_index=True)
    combined.to_csv(os.path.join(OUT_DIR, "v3_precursor_classification.csv"), index=False)
    print(f"\nWrote {os.path.join(OUT_DIR, 'v3_precursor_classification.csv')}")


if __name__ == "__main__":
    main()
