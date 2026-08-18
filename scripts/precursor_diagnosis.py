"""Phase 1/2 precursor-signal diagnosis (read-only analysis of v0.2 data).

Does NOT modify aeroguard/, aeroguard_dataset/, v0.2 data, or any existing
outputs. Reads data/processed/processed_dataset_v2.parquet (raw per-step
telemetry, all 1000 trajectories, unfiltered) + data/metadata/
trajectory_metadata_v2.csv (regime = generation_mode, whether_stall_occurred,
time_of_first_stall) and writes new CSVs/plots under
outputs/precursor_diagnosis/.

Two analyses:

1. Exact-offset trajectory trace: for every trajectory that crosses
   alpha_stall, sample V/alpha/gamma/pitch_rate/elevator/stall_margin at
   exactly {5,4,3,2,1,0.5,0}s before its FIRST crossing (time_of_first_stall
   from metadata), by nearest-row lookup (dt=0.01). This answers Q1/Q2/Q4
   directly: "how do these quantities evolve during the 5s before crossing,
   by regime."

2. Near-crossing vs. safe separability (extends the existing cached
   ml_temporal physics_diagnosis methodology -- same near/safe definition
   using time_to_stall -- to include a 0.5s bucket and a per-regime split,
   which the cached outputs/ml_temporal/metrics/physics_diagnosis.csv did
   not have). Answers Q5: AUC-based statistical separability at 2-5s.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs" / "precursor_diagnosis"
OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "plots").mkdir(exist_ok=True)

VARS = ["alpha", "V", "gamma", "pitch_rate", "elevator", "stall_margin"]
OFFSETS_S = [5.0, 4.0, 3.0, 2.0, 1.0, 0.5, 0.0]
DT = 0.01


def load_data():
    proc = pd.read_parquet(REPO_ROOT / "data" / "processed" / "processed_dataset_v2.parquet")
    meta = pd.read_csv(REPO_ROOT / "data" / "metadata" / "trajectory_metadata_v2.csv")
    return proc, meta


# ---------------------------------------------------------------------------
# Analysis 1: exact-offset trace before first crossing
# ---------------------------------------------------------------------------

def build_exact_offset_table(proc: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    """Direction-aligned: stall-regime crossings can be nose-up (alpha > +alpha_stall)
    OR nose-down/spin (alpha < -alpha_stall) -- see crossing_ramp_mechanism.csv,
    ~39% of stall crossings are negative-alpha. Raw (signed) alpha/stall_margin/
    pitch_rate/elevator averaged across both directions cancel out (mean alpha
    artificially near 0 even at the crossing sample itself). We flip the sign of
    direction-dependent variables by the sign of alpha at the actual crossing
    sample so all trajectories are expressed as "approach toward the boundary
    that was actually crossed" -- gamma and V are direction-agnostic and left
    unsigned.
    """
    crossers = meta[meta["whether_stall_occurred"]].copy()
    proc_idx = proc.set_index("trajectory_id")
    dir_vars = {"alpha", "stall_margin", "pitch_rate", "elevator"}

    rows = []
    for _, m in crossers.iterrows():
        tid = m["trajectory_id"]
        regime = m["generation_mode"]
        t_cross = m["time_of_first_stall"]
        g = proc_idx.loc[[tid]] if tid in proc_idx.index else None
        if g is None or len(g) == 0:
            continue
        times = g["time"].to_numpy()
        # crossing sign: look up the actual sample nearest t_cross
        i_cross = int(np.argmin(np.abs(times - t_cross)))
        sign = 1.0 if g.iloc[i_cross]["alpha"] >= 0 else -1.0
        for off in OFFSETS_S:
            target = t_cross - off
            if target < times[0] - 1e-6:
                continue  # not enough runway before crossing for this offset
            j = int(np.searchsorted(times, target))
            j = min(max(j, 0), len(times) - 1)
            # nearest of j, j-1
            if j > 0 and abs(times[j - 1] - target) < abs(times[j] - target):
                j = j - 1
            if abs(times[j] - target) > 5 * DT:
                continue  # trajectory doesn't actually have data here (early termination)
            row = {"trajectory_id": tid, "regime": regime, "offset_before_crossing_s": off,
                   "t_cross": t_cross, "actual_t": times[j], "crossing_sign": sign,
                   "termination_reason": m["termination_reason"]}
            for v in VARS:
                val = g.iloc[j][v]
                if v in dir_vars:
                    val = val * sign if v != "stall_margin" else val  # margin is already |.|-referenced sign-consistent below
                row[v] = val
            # stall_margin as generated is alpha_at_cl_peak - alpha (positive-side only);
            # for a direction-aligned "margin to the crossed boundary" use alpha_at_cl_peak - sign*alpha
            row["stall_margin"] = ALPHA_STALL_RAD - sign * g.iloc[j]["alpha"]
            rows.append(row)
    return pd.DataFrame(rows)


def summarize_exact_offset(df: pd.DataFrame) -> pd.DataFrame:
    agg = df.groupby(["regime", "offset_before_crossing_s"])[VARS].agg(["count", "mean", "median", "std"])
    agg.columns = ["_".join(c) for c in agg.columns]
    return agg.reset_index().sort_values(["regime", "offset_before_crossing_s"], ascending=[True, False])


# ---------------------------------------------------------------------------
# Analysis 2: near-crossing vs safe separability by regime (extends cached
# physics_diagnosis.csv methodology with 0.5s bucket + regime split)
# ---------------------------------------------------------------------------

DIAG_LEAD_TIMES = [5.0, 4.0, 3.0, 2.0, 1.0, 0.5]
DIAG_VARS = ["alpha", "V", "gamma", "pitch_rate", "elevator", "stall_margin",
             "dV_dt", "dalpha_dt", "dgamma_dt", "dq_dt"]


def load_temporal_panels():
    parts = []
    for split in ["train", "val", "test"]:
        p = pd.read_parquet(REPO_ROOT / "data" / "ml_temporal" / f"temporal_{split}.parquet")
        p["split"] = split
        parts.append(p)
    panel = pd.concat(parts, ignore_index=True)
    meta = pd.read_csv(REPO_ROOT / "data" / "metadata" / "trajectory_metadata_v2.csv")
    panel = panel.merge(meta[["trajectory_id", "generation_mode"]], on="trajectory_id", how="left")
    panel = panel.rename(columns={"generation_mode": "regime"})
    return panel


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan")
    va, vb = np.var(a, ddof=1), np.var(b, ddof=1)
    pooled = np.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    if pooled == 0:
        return float("nan")
    return float((np.mean(a) - np.mean(b)) / pooled)


def separability_by_regime(panel: pd.DataFrame, tolerance_s: float = 0.25,
                            safe_threshold_s: float = 10.0) -> pd.DataFrame:
    rows = []
    for regime in ["near_boundary", "stall", "normal"]:
        sub = panel[panel["regime"] == regime]
        tts = sub["time_to_stall"].to_numpy()
        safe_mask = np.isnan(tts) | (tts > safe_threshold_s)
        for L in DIAG_LEAD_TIMES:
            tol = 0.15 if L == 0.5 else tolerance_s
            near_mask = (tts > L - tol) & (tts <= L + tol)
            for var in DIAG_VARS:
                if var not in sub.columns:
                    continue
                near_vals = sub.loc[near_mask, var].dropna().to_numpy()
                safe_vals = sub.loc[safe_mask, var].dropna().to_numpy()
                if len(near_vals) < 10 or len(safe_vals) < 10:
                    auc, d = float("nan"), float("nan")
                else:
                    labels = np.concatenate([np.ones(len(near_vals)), np.zeros(len(safe_vals))])
                    scores = np.concatenate([near_vals, safe_vals])
                    try:
                        raw_auc = roc_auc_score(labels, scores)
                        auc = max(raw_auc, 1 - raw_auc)
                    except ValueError:
                        auc = float("nan")
                    d = cohens_d(near_vals, safe_vals)
                rows.append({
                    "regime": regime, "lead_time_s": L, "variable": var,
                    "n_near_crossing": len(near_vals), "n_safe": len(safe_vals),
                    "separability_auc": auc, "cohens_d": d,
                    "near_mean": float(np.mean(near_vals)) if len(near_vals) else None,
                    "safe_mean": float(np.mean(safe_vals)) if len(safe_vals) else None,
                })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_exact_offset(df: pd.DataFrame):
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    for ax, var in zip(axes.flat, VARS):
        for regime, marker in [("near_boundary", "o"), ("stall", "s")]:
            sub = df[df["regime"] == regime]
            g = sub.groupby("offset_before_crossing_s")[var].agg(["mean", "std", "count"])
            g = g.sort_index(ascending=False)
            x = g.index.to_numpy()
            ax.errorbar(x, g["mean"], yerr=g["std"] / np.sqrt(g["count"].clip(lower=1)),
                        marker=marker, label=regime, capsize=3)
        ax.invert_xaxis()
        ax.set_xlabel("seconds before crossing")
        ax.set_ylabel(var)
        ax.set_title(f"{var} vs. time-to-crossing")
        ax.legend()
        ax.axvline(0, color="red", linestyle="--", alpha=0.3)
    fig.suptitle("Evolution of state variables in the 5s before an alpha_stall crossing (v0.2 data)")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "plots" / "01_variable_evolution_before_crossing.png", dpi=120)
    plt.close(fig)


def plot_auc_heatmap(sep_df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, regime in zip(axes, ["near_boundary", "stall"]):
        sub = sep_df[sep_df["regime"] == regime]
        piv = sub.pivot(index="variable", columns="lead_time_s", values="separability_auc")
        piv = piv[sorted(piv.columns, reverse=True)]
        im = ax.imshow(piv.to_numpy(), cmap="viridis", vmin=0.5, vmax=1.0, aspect="auto")
        ax.set_xticks(range(len(piv.columns)))
        ax.set_xticklabels([f"{c}s" for c in piv.columns])
        ax.set_yticks(range(len(piv.index)))
        ax.set_yticklabels(piv.index)
        ax.set_title(f"Separability AUC (near-crossing vs safe) -- {regime}")
        for i in range(piv.shape[0]):
            for j in range(piv.shape[1]):
                val = piv.to_numpy()[i, j]
                if not np.isnan(val):
                    ax.text(j, i, f"{val:.2f}", ha="center", va="center", color="white", fontsize=8)
        fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "plots" / "02_separability_auc_heatmap.png", dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Analysis 3 (Phase 2 mechanism): ramp speed from alpha=8deg to crossing,
# and elevator-hold-past-crossing duration, per crossing trajectory.
# ---------------------------------------------------------------------------

ALPHA_STALL_RAD = 0.280440097919249  # = alpha + stall_margin, verified constant in the dataset
ALPHA_8DEG_RAD = np.radians(8.0)
ALPHA_12DEG_RAD = np.radians(12.0)


def crossing_ramp_analysis(proc: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    crossers = meta[meta["whether_stall_occurred"]].copy()
    proc_idx = proc.set_index("trajectory_id")
    rows = []
    for _, m in crossers.iterrows():
        tid = m["trajectory_id"]
        g = proc_idx.loc[[tid]] if tid in proc_idx.index else None
        if g is None or len(g) == 0:
            continue
        t = g["time"].to_numpy()
        a = g["alpha"].to_numpy()
        elev = g["elevator"].to_numpy()
        unsafe = a > ALPHA_STALL_RAD
        if not unsafe.any():
            continue
        i_cross = int(np.argmax(unsafe))
        t_cross = t[i_cross]
        # last time alpha was below 8deg, strictly before crossing, on a rising approach
        below8 = np.where((a[:i_cross] < ALPHA_8DEG_RAD))[0]
        t_alpha8 = t[below8[-1]] if len(below8) else np.nan
        below12 = np.where((a[:i_cross] < ALPHA_12DEG_RAD))[0]
        t_alpha12 = t[below12[-1]] if len(below12) else np.nan
        # elevator peak magnitude and time it first reaches within 5% of peak, vs t_cross
        peak_elev_idx = int(np.argmax(np.abs(elev[: min(i_cross + 200, len(elev))])))
        t_elev_peak = t[peak_elev_idx]
        # how long after crossing does elevator stay near its peak magnitude (>=80% of peak)?
        peak_mag = abs(elev[peak_elev_idx])
        after = np.abs(elev[i_cross:]) >= 0.8 * peak_mag if peak_mag > 1e-6 else np.array([])
        hold_after_cross_s = float(np.sum(after) * DT) if len(after) else 0.0
        rows.append({
            "trajectory_id": tid, "regime": m["generation_mode"],
            "termination_reason": m["termination_reason"],
            "t_cross": t_cross,
            "time_alpha8_to_cross_s": (t_cross - t_alpha8) if not np.isnan(t_alpha8) else np.nan,
            "time_alpha12_to_cross_s": (t_cross - t_alpha12) if not np.isnan(t_alpha12) else np.nan,
            "t_elev_peak_minus_t_cross_s": t_elev_peak - t_cross,
            "elevator_peak_rad": peak_mag,
            "elevator_hold_ge80pct_after_cross_s": hold_after_cross_s,
            "duration_actual_s": m["duration_actual_s"],
        })
    return pd.DataFrame(rows)


def main():
    print("Loading v0.2 processed data + metadata...")
    proc, meta = load_data()
    print(f"  processed rows: {len(proc):,}  trajectories: {meta.shape[0]}")

    print("Building exact-offset trace table (Q1/Q2/Q4)...")
    exact_df = build_exact_offset_table(proc, meta)
    exact_df.to_csv(OUT_DIR / "exact_offset_raw.csv", index=False)
    summary = summarize_exact_offset(exact_df)
    summary.to_csv(OUT_DIR / "exact_offset_summary_by_regime.csv", index=False)
    print(f"  {len(exact_df)} (trajectory, offset) rows -> exact_offset_summary_by_regime.csv")

    print("Loading cached ml_temporal panels for separability analysis (Q5)...")
    panel = load_temporal_panels()
    print(f"  panel rows: {len(panel):,}")

    print("Computing near-crossing vs safe separability by regime (AUC + Cohen's d)...")
    sep_df = separability_by_regime(panel)
    sep_df.to_csv(OUT_DIR / "separability_by_regime.csv", index=False)

    print("Computing ramp-speed / elevator-hold mechanism analysis (Phase 2)...")
    ramp_df = crossing_ramp_analysis(proc, meta)
    ramp_df.to_csv(OUT_DIR / "crossing_ramp_mechanism.csv", index=False)
    print(ramp_df.groupby("regime")[["time_alpha8_to_cross_s", "time_alpha12_to_cross_s",
                                       "elevator_hold_ge80pct_after_cross_s"]].median())
    print("\nfraction of crossings with >=1s / >=2s / >=3s alpha8->cross window, by regime:")
    for regime, g in ramp_df.groupby("regime"):
        v = g["time_alpha8_to_cross_s"].dropna()
        print(f"  {regime}: n={len(v)}, >=1s: {(v>=1).mean():.2%}, >=2s: {(v>=2).mean():.2%}, >=3s: {(v>=3).mean():.2%}")

    print("Plotting...")
    plot_exact_offset(exact_df)
    plot_auc_heatmap(sep_df)

    # quick console summary
    print("\n=== Crossing counts by regime ===")
    print(meta.groupby("generation_mode")["whether_stall_occurred"].agg(["sum", "count"]))

    print("\n=== Max separability AUC by regime/lead_time (across all variables) ===")
    best = sep_df.groupby(["regime", "lead_time_s"])["separability_auc"].max().reset_index()
    print(best.pivot(index="lead_time_s", columns="regime", values="separability_auc").sort_index(ascending=False))

    with open(OUT_DIR / "run_manifest.json", "w") as f:
        json.dump({
            "inputs": [
                "data/processed/processed_dataset_v2.parquet (read-only)",
                "data/metadata/trajectory_metadata_v2.csv (read-only)",
                "data/ml_temporal/temporal_{train,val,test}.parquet (read-only, cached)",
            ],
            "n_crossing_trajectories_total": int(meta["whether_stall_occurred"].sum()),
            "n_crossing_by_regime": meta.groupby("generation_mode")["whether_stall_occurred"].sum().to_dict(),
        }, f, indent=2)
    print(f"\nDone. Outputs written to {OUT_DIR}")


if __name__ == "__main__":
    main()
