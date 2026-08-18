"""Phase 1 diagnostic: does v0.2 contain a genuine multi-second stall precursor?

Read-only analysis over the ALREADY-GENERATED v0.2 dataset
(data/processed/processed_dataset_v2.parquet + data/metadata/trajectory_metadata_v2.csv).
Does not touch aeroguard/ physics, does not regenerate v0.2, does not train any ML model.

For every real stall-crossing trajectory, looks up the row at exactly
{5,4,3,2,1,0.5,0}s before the first-stall time (t_of_first_stall, from metadata,
itself derived from events.first_unsafe_index during dataset_builder) and compares
the feature distributions there against a "safe" background: one randomly chosen
row from each trajectory that never stalls (whether_stall_occurred == False),
which includes both normal-regime and near-boundary-regime trajectories that
approached but never crossed the boundary.

Outputs -> outputs/precursor_diagnosis/:
  precursor_stats.csv          per (lead_time, feature): n, pos/neg mean+std, Cohen's d, AUC
  ramp_timing_stats.json       alpha 8->16deg and 12deg->crossing timing stats (real v0.2 data)
  precursor_diagnosis_report.md
  01_alpha_before_crossing.png   sample alpha(t) traces aligned to crossing time
  02_auc_vs_leadtime.png         single-feature separability AUC vs lead time
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
from sklearn.metrics import roc_auc_score

from aeroguard.aircraft import Aircraft
from aeroguard_dataset import paths  # noqa: F401  (sets up sys.path)
from aeroguard_dataset.events import resolve_stall_boundary

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs", "precursor_diagnosis")
os.makedirs(OUT_DIR, exist_ok=True)

LEAD_TIMES = [5.0, 4.0, 3.0, 2.0, 1.0, 0.5, 0.0]
FEATURES = ["alpha", "stall_margin", "V", "gamma", "pitch_rate", "elevator", "throttle", "dalpha_dt", "dV_dt"]

RNG_SEED = 20260817


def cohens_d(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if len(a) < 2 or len(b) < 2:
        return np.nan
    na, nb = len(a), len(b)
    va, vb = a.var(ddof=1), b.var(ddof=1)
    pooled_sd = np.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    if pooled_sd == 0:
        return np.nan
    return (a.mean() - b.mean()) / pooled_sd


def auc_separability(a, b):
    """AUC of a single feature distinguishing positive (a) vs negative (b) rows.
    0.5 = no separability, 1.0 (or 0.0) = perfect separability."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    mask_a = np.isfinite(a)
    mask_b = np.isfinite(b)
    a, b = a[mask_a], b[mask_b]
    if len(a) < 2 or len(b) < 2:
        return np.nan
    y = np.concatenate([np.ones(len(a)), np.zeros(len(b))])
    x = np.concatenate([a, b])
    auc = roc_auc_score(y, x)
    return max(auc, 1 - auc)  # symmetric: direction-agnostic separability


def main():
    print("Loading v0.2 processed dataset + metadata (cached, not regenerated)...")
    df = pd.read_parquet(os.path.join(paths.DATA_PROCESSED_DIR, "processed_dataset_v2.parquet"))
    meta = pd.read_csv(os.path.join(paths.DATA_METADATA_DIR, "trajectory_metadata_v2.csv"))

    aircraft = Aircraft()
    boundary = resolve_stall_boundary(aircraft)
    boundary_deg = np.degrees(boundary.alpha_at_cl_peak)
    print(f"Stall boundary (CL peak): {boundary_deg:.2f} deg")

    df["time_r"] = df["time"].round(2)

    crossing_meta = meta[meta["whether_stall_occurred"] & meta["time_of_first_stall"].notna()].copy()
    safe_meta = meta[~meta["whether_stall_occurred"]].copy()
    print(f"Crossing trajectories: {len(crossing_meta)} / Safe (never-stall) trajectories: {len(safe_meta)}")

    # ---- background ("safe") sample: 1 random row per safe trajectory ----
    rng = np.random.default_rng(RNG_SEED)
    safe_df = df[df["trajectory_id"].isin(safe_meta["trajectory_id"])]
    safe_rows = []
    for tid, g in safe_df.groupby("trajectory_id", sort=False):
        idx = rng.integers(0, len(g))
        safe_rows.append(g.iloc[idx])
    safe_sample = pd.DataFrame(safe_rows).reset_index(drop=True)
    safe_sample.to_csv(os.path.join(OUT_DIR, "safe_background_sample.csv"), index=False)
    print(f"Safe background sample: {len(safe_sample)} rows (1 per safe trajectory)")

    # ---- positive samples: row at each lead time before crossing, per trajectory ----
    lead_frames = {}
    for lt in LEAD_TIMES:
        cm = crossing_meta.copy()
        cm["target_time"] = (cm["time_of_first_stall"] - lt).round(2)
        cm = cm[cm["target_time"] >= 0.0]
        merged = cm.merge(
            df, left_on=["trajectory_id", "target_time"], right_on=["trajectory_id", "time_r"], how="inner"
        )
        lead_frames[lt] = merged
        print(f"  lead={lt:>4.1f}s : {len(merged)}/{len(crossing_meta)} crossing trajectories have a row that far back")

    # ---- stats table ----
    records = []
    for lt in LEAD_TIMES:
        pos = lead_frames[lt]
        for feat in FEATURES:
            pos_vals = pos[feat].values
            neg_vals = safe_sample[feat].values
            d = cohens_d(pos_vals, neg_vals)
            auc = auc_separability(pos_vals, neg_vals)
            records.append({
                "lead_time_s": lt,
                "feature": feat,
                "n_pos": int(np.isfinite(pos_vals).sum()),
                "n_neg": int(np.isfinite(neg_vals).sum()),
                "pos_mean": float(np.nanmean(pos_vals)),
                "pos_std": float(np.nanstd(pos_vals)),
                "neg_mean": float(np.nanmean(neg_vals)),
                "neg_std": float(np.nanstd(neg_vals)),
                "cohens_d": float(d) if np.isfinite(d) else None,
                "auc": float(auc) if np.isfinite(auc) else None,
            })
    stats_df = pd.DataFrame(records)
    stats_df.to_csv(os.path.join(OUT_DIR, "precursor_stats.csv"), index=False)
    print(f"\nWrote {os.path.join(OUT_DIR, 'precursor_stats.csv')}")

    # ---- ramp timing: alpha 8deg->16deg and 12deg->crossing, from real trajectories ----
    print("\nComputing ramp timing (alpha 8->16 deg, 12deg->crossing) from real trajectories...")
    raw_df = pd.read_parquet(os.path.join(paths.DATA_RAW_DIR, "raw_telemetry_v2.parquet"))
    ramp_times_8_16 = []
    ramp_times_12_cross = []
    for tid, tcross in zip(crossing_meta["trajectory_id"], crossing_meta["time_of_first_stall"]):
        g = raw_df[raw_df["trajectory_id"] == tid].sort_values("time")
        alpha_deg = np.degrees(g["alpha"].values)
        t = g["time"].values
        pre = t <= tcross + 1e-9
        alpha_pre = alpha_deg[pre]
        t_pre = t[pre]
        # last crossing of 8deg (rising) and last crossing of 16deg (rising) before/at t_cross
        above8 = np.where(alpha_pre >= 8.0)[0]
        above12 = np.where(alpha_pre >= 12.0)[0]
        above16 = np.where(alpha_pre >= 16.0)[0]
        if len(above8) and len(above16):
            t8 = t_pre[above8[0]]
            t16 = t_pre[above16[0]]
            if t16 >= t8:
                ramp_times_8_16.append(t16 - t8)
        if len(above12):
            t12 = t_pre[above12[0]]
            ramp_times_12_cross.append(tcross - t12)

    ramp_stats = {
        "n_crossing_trajectories": int(len(crossing_meta)),
        "n_with_8_16_ramp": len(ramp_times_8_16),
        "median_alpha_8_to_16_deg_s": float(np.median(ramp_times_8_16)) if ramp_times_8_16 else None,
        "mean_alpha_8_to_16_deg_s": float(np.mean(ramp_times_8_16)) if ramp_times_8_16 else None,
        "p25_alpha_8_to_16_deg_s": float(np.percentile(ramp_times_8_16, 25)) if ramp_times_8_16 else None,
        "p75_alpha_8_to_16_deg_s": float(np.percentile(ramp_times_8_16, 75)) if ramp_times_8_16 else None,
        "n_with_12_to_cross": len(ramp_times_12_cross),
        "median_alpha_12_to_crossing_s": float(np.median(ramp_times_12_cross)) if ramp_times_12_cross else None,
        "mean_alpha_12_to_crossing_s": float(np.mean(ramp_times_12_cross)) if ramp_times_12_cross else None,
        "p25_alpha_12_to_crossing_s": float(np.percentile(ramp_times_12_cross, 25)) if ramp_times_12_cross else None,
        "p75_alpha_12_to_crossing_s": float(np.percentile(ramp_times_12_cross, 75)) if ramp_times_12_cross else None,
        "boundary_deg": float(boundary_deg),
    }
    with open(os.path.join(OUT_DIR, "ramp_timing_stats.json"), "w") as f:
        json.dump(ramp_stats, f, indent=2)
    print(json.dumps(ramp_stats, indent=2))

    # ---- plot: sample alpha(t) traces aligned to crossing ----
    print("\nPlotting sample alpha(t) traces aligned to crossing time...")
    fig, ax = plt.subplots(figsize=(9, 6))
    sample_ids = crossing_meta["trajectory_id"].sample(n=min(25, len(crossing_meta)), random_state=RNG_SEED)
    for tid in sample_ids:
        tcross = crossing_meta.loc[crossing_meta["trajectory_id"] == tid, "time_of_first_stall"].iloc[0]
        g = raw_df[raw_df["trajectory_id"] == tid].sort_values("time")
        t_rel = g["time"].values - tcross
        mask = (t_rel >= -6) & (t_rel <= 1)
        ax.plot(t_rel[mask], np.degrees(g["alpha"].values[mask]), alpha=0.5, lw=1)
    ax.axhline(boundary_deg, color="red", ls="--", label=f"stall boundary ({boundary_deg:.1f} deg)")
    ax.axvline(0, color="black", ls=":", label="crossing time")
    ax.set_xlabel("time relative to crossing [s]")
    ax.set_ylabel("alpha [deg]")
    ax.set_title("v0.2: alpha(t) aligned to first stall crossing (25 random samples)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "01_alpha_before_crossing.png"), dpi=120)
    plt.close(fig)

    # ---- plot: AUC vs lead time per feature ----
    fig, ax = plt.subplots(figsize=(8, 5))
    for feat in FEATURES:
        sub = stats_df[stats_df["feature"] == feat].sort_values("lead_time_s", ascending=False)
        ax.plot(sub["lead_time_s"], sub["auc"], marker="o", label=feat)
    ax.axhline(0.5, color="gray", ls=":", label="chance")
    ax.set_xlabel("lead time before crossing [s]")
    ax.set_ylabel("single-feature separability AUC (vs safe background)")
    ax.invert_xaxis()
    ax.set_title("v0.2: precursor separability by lead time")
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "02_auc_vs_leadtime.png"), dpi=120)
    plt.close(fig)

    print(f"\nDone. Outputs in {OUT_DIR}")


if __name__ == "__main__":
    main()
