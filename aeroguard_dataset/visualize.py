"""Dataset-audit visualizations (Section 17).

Uses representative samples (a handful of individual trajectories, and
random row subsamples for scatter plots) rather than plotting all 1000
trajectories at once.
"""

import os
from typing import List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .events import StallBoundary

N_SAMPLE_TRAJECTORIES = 6
SCATTER_SUBSAMPLE_N = 30_000


def _pick_sample_ids(metadata_df: pd.DataFrame, mask: pd.Series, n: int, seed: int) -> List[str]:
    candidates = metadata_df.loc[mask, "trajectory_id"].to_numpy()
    if len(candidates) == 0:
        return []
    rng = np.random.default_rng(seed)
    n = min(n, len(candidates))
    return list(rng.choice(candidates, size=n, replace=False))


def _plot_sample_trajectories(raw_df: pd.DataFrame, ids: List[str], boundary: StallBoundary, title: str, save_path: str):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    boundary_deg = np.degrees(boundary.alpha_at_cl_peak)

    for tid in ids:
        g = raw_df[raw_df["trajectory_id"] == tid].sort_values("time")
        axes[0].plot(g["time"], np.degrees(g["alpha"]), linewidth=1.3, label=tid)
        axes[1].plot(g["time"], g["V"], linewidth=1.3, label=tid)

    axes[0].axhline(boundary_deg, color="r", linestyle="--", linewidth=1, label="stall boundary")
    axes[0].axhline(-boundary_deg, color="r", linestyle="--", linewidth=1)
    axes[0].set_xlabel("time [s]")
    axes[0].set_ylabel("alpha [deg]")
    axes[0].set_title(f"{title}: angle of attack vs time")
    axes[0].legend(fontsize=7, loc="upper right")
    axes[0].grid(True)

    axes[1].set_xlabel("time [s]")
    axes[1].set_ylabel("airspeed V [m/s]")
    axes[1].set_title(f"{title}: airspeed vs time")
    axes[1].legend(fontsize=7, loc="upper right")
    axes[1].grid(True)

    fig.suptitle(f"{title} (n={len(ids)} sample trajectories, not all {raw_df['trajectory_id'].nunique()})")
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_normal_samples(raw_df, metadata_df, boundary, out_dir, seed):
    ids = _pick_sample_ids(metadata_df, metadata_df["generation_mode"] == "normal", N_SAMPLE_TRAJECTORIES, seed)
    _plot_sample_trajectories(raw_df, ids, boundary, "Sample NORMAL trajectories", os.path.join(out_dir, "01_sample_normal_trajectories.png"))


def plot_near_boundary_samples(raw_df, metadata_df, boundary, out_dir, seed):
    """"Near-boundary" here selects by OUTCOME (max|alpha| close to the
    actual stall boundary), regardless of which generation mode produced
    it -- a different, complementary notion from the "boundary-focused"
    generation mode (which is about HOW the trajectory was generated).
    """
    boundary_deg = np.degrees(boundary.alpha_at_cl_peak)
    max_alpha_deg = np.degrees(metadata_df["maximum_alpha"].abs())
    near_mask = (max_alpha_deg - boundary_deg).abs() <= 5.0
    ids = _pick_sample_ids(metadata_df, near_mask, N_SAMPLE_TRAJECTORIES, seed)
    _plot_sample_trajectories(raw_df, ids, boundary, "Sample NEAR-BOUNDARY trajectories (by outcome)", os.path.join(out_dir, "02_sample_near_boundary_trajectories.png"))


def plot_stall_samples(raw_df, metadata_df, boundary, out_dir, seed):
    ids = _pick_sample_ids(metadata_df, metadata_df["whether_stall_occurred"], N_SAMPLE_TRAJECTORIES, seed)
    _plot_sample_trajectories(raw_df, ids, boundary, "Sample STALL trajectories (event occurred)", os.path.join(out_dir, "03_sample_stall_trajectories.png"))


def plot_alpha_distribution(raw_df, boundary, out_dir):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(np.degrees(raw_df["alpha"]), bins=120, color="steelblue")
    boundary_deg = np.degrees(boundary.alpha_at_cl_peak)
    ax.axvline(boundary_deg, color="r", linestyle="--", linewidth=1, label="stall boundary")
    ax.axvline(-boundary_deg, color="r", linestyle="--", linewidth=1)
    ax.set_xlabel("angle of attack alpha [deg]")
    ax.set_ylabel("count (all timesteps, all trajectories)")
    ax.set_title("Alpha distribution across the full dataset")
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "04_alpha_distribution.png"), dpi=150)
    plt.close(fig)


def plot_airspeed_distribution(raw_df, v_stall, v_floor, out_dir):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(raw_df["V"], bins=120, color="seagreen")
    ax.axvline(v_stall, color="orange", linestyle="--", linewidth=1, label=f"V_stall ({v_stall:.1f} m/s)")
    ax.axvline(v_floor, color="r", linestyle="--", linewidth=1, label=f"validity floor ({v_floor:.1f} m/s)")
    ax.set_xlabel("airspeed V [m/s]")
    ax.set_ylabel("count (all timesteps, all trajectories)")
    ax.set_title("Airspeed distribution across the full dataset")
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "05_airspeed_distribution.png"), dpi=150)
    plt.close(fig)


def plot_future_label_distribution(processed_df, out_dir):
    counts = processed_df["future_stall_5s"].value_counts(dropna=False)
    labels = []
    values = []
    for key, name in [(0.0, "0 (safe)"), (1.0, "1 (stall within 5s)"), (np.nan, "unavailable (NaN)")]:
        if pd.isna(key):
            v = int(processed_df["future_stall_5s"].isna().sum())
        else:
            v = int(counts.get(key, 0))
        labels.append(name)
        values.append(v)

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(labels, values, color=["seagreen", "crimson", "gray"])
    ax.set_ylabel("row count")
    ax.set_title("future_stall_5s label distribution")
    for i, v in enumerate(values):
        ax.text(i, v, f"{v:,}", ha="center", va="bottom")
    ax.grid(True, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "06_future_stall_label_distribution.png"), dpi=150)
    plt.close(fig)


def _subsample(df: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    if len(df) <= n:
        return df
    return df.sample(n=n, random_state=seed)


def plot_alpha_vs_airspeed(processed_df, boundary, out_dir, seed):
    sample = _subsample(processed_df, SCATTER_SUBSAMPLE_N, seed)
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = np.where(sample["is_unsafe"], "crimson", "steelblue")
    ax.scatter(sample["V"], np.degrees(sample["alpha"]), s=2, c=colors, alpha=0.3)
    ax.axhline(np.degrees(boundary.alpha_at_cl_peak), color="k", linestyle="--", linewidth=1)
    ax.axhline(-np.degrees(boundary.alpha_at_cl_peak), color="k", linestyle="--", linewidth=1)
    ax.set_xlabel("airspeed V [m/s]")
    ax.set_ylabel("angle of attack alpha [deg]")
    ax.set_title(f"alpha vs airspeed (random sample of {len(sample):,} rows; red = post-stall)")
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "07_alpha_vs_airspeed_scatter.png"), dpi=150)
    plt.close(fig)


def plot_alpha_vs_dalpha_dt(processed_df, boundary, out_dir, seed):
    sample = _subsample(processed_df.dropna(subset=["dalpha_dt"]), SCATTER_SUBSAMPLE_N, seed)
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = np.where(sample["is_unsafe"], "crimson", "steelblue")
    ax.scatter(np.degrees(sample["alpha"]), np.degrees(sample["dalpha_dt"]), s=2, c=colors, alpha=0.3)
    ax.axvline(np.degrees(boundary.alpha_at_cl_peak), color="k", linestyle="--", linewidth=1)
    ax.axvline(-np.degrees(boundary.alpha_at_cl_peak), color="k", linestyle="--", linewidth=1)
    ax.set_xlabel("angle of attack alpha [deg]")
    ax.set_ylabel("dalpha/dt [deg/s]")
    ax.set_title(f"alpha vs dalpha/dt (random sample of {len(sample):,} rows; red = post-stall)")
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "08_alpha_vs_dalpha_dt_scatter.png"), dpi=150)
    plt.close(fig)


def plot_stall_margin_distribution(processed_df, out_dir):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(np.degrees(processed_df["stall_margin"]), bins=120, color="darkorange")
    ax.axvline(0.0, color="r", linestyle="--", linewidth=1, label="margin = 0 (at positive boundary)")
    ax.set_xlabel("stall_margin [deg] = alpha_at_cl_peak - alpha")
    ax.set_ylabel("count")
    ax.set_title("stall_margin distribution across the full dataset")
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "09_stall_margin_distribution.png"), dpi=150)
    plt.close(fig)


def plot_validity_envelope_violations(metadata_df, v_floor, gamma_max_rad, out_dir):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    term_counts = metadata_df["termination_reason"].value_counts()
    axes[0].bar(term_counts.index, term_counts.values, color="slategray")
    axes[0].set_ylabel("trajectory count")
    axes[0].set_title("Termination reason across all trajectories")
    axes[0].tick_params(axis="x", rotation=30)
    for label in axes[0].get_xticklabels():
        label.set_ha("right")
    axes[0].grid(True, axis="y")

    exceeded = metadata_df["whether_validity_envelope_was_exceeded"]
    colors = np.where(exceeded, "crimson", "steelblue")
    axes[1].scatter(metadata_df["minimum_airspeed"], np.degrees(metadata_df["maximum_abs_gamma"]), s=10, c=colors, alpha=0.6)
    axes[1].axvline(v_floor, color="k", linestyle="--", linewidth=1, label=f"V floor ({v_floor:.1f} m/s)")
    axes[1].axhline(np.degrees(gamma_max_rad), color="k", linestyle=":", linewidth=1, label=f"gamma max ({np.degrees(gamma_max_rad):.0f} deg)")
    axes[1].set_xlabel("trajectory minimum airspeed [m/s]")
    axes[1].set_ylabel("trajectory maximum |gamma| [deg]")
    axes[1].set_title("Per-trajectory envelope proximity (red = exceeded)")
    axes[1].legend(fontsize=8)
    axes[1].grid(True)

    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "10_validity_envelope_violations.png"), dpi=150)
    plt.close(fig)


def generate_all_plots(raw_df, processed_df, metadata_df, boundary, v_stall, v_floor, gamma_max_rad, out_dir, seed):
    os.makedirs(out_dir, exist_ok=True)
    plot_normal_samples(raw_df, metadata_df, boundary, out_dir, seed)
    plot_near_boundary_samples(raw_df, metadata_df, boundary, out_dir, seed)
    plot_stall_samples(raw_df, metadata_df, boundary, out_dir, seed)
    plot_alpha_distribution(raw_df, boundary, out_dir)
    plot_airspeed_distribution(raw_df, v_stall, v_floor, out_dir)
    plot_future_label_distribution(processed_df, out_dir)
    plot_alpha_vs_airspeed(processed_df, boundary, out_dir, seed)
    plot_alpha_vs_dalpha_dt(processed_df, boundary, out_dir, seed)
    plot_stall_margin_distribution(processed_df, out_dir)
    plot_validity_envelope_violations(metadata_df, v_floor, gamma_max_rad, out_dir)
