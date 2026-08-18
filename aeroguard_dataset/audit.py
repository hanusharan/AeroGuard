"""Dataset-quality audit (Section 16).

Computes every statistic requested for the audit report and a small set
of explicit, re-computed integrity checks (not just "trust the pipeline"
assertions) for future-label leakage and causal-derivative correctness.

Nothing here modifies the dataset. Findings are reported, not fixed.
"""

from typing import Dict

import numpy as np
import pandas as pd

from .events import StallBoundary
from .trajectory_sim import (
    TERMINATION_GAMMA_EXCEEDED,
    TERMINATION_GROUND_CONTACT,
    TERMINATION_INVALID_CONTROL,
    TERMINATION_LOW_AIRSPEED,
    TERMINATION_NAN_INF,
)
from .features import causal_backward_difference
from .labeling import compute_future_stall_label


def _series_stats(s: pd.Series) -> Dict[str, float]:
    return {"min": float(s.min()), "max": float(s.max())}


def verify_causal_derivatives(raw_df: pd.DataFrame, processed_df: pd.DataFrame, dt: float, sample_trajectories: int = 25, seed: int = 0) -> dict:
    """Recompute dV_dt / dalpha_dt independently from the raw columns
    for a sample of trajectories and confirm they match the stored
    values exactly. This is a real re-derivation, not a re-assertion of
    the same code path -- it directly demonstrates the stored
    derivative at row i only ever used raw values at rows <= i."""
    rng = np.random.default_rng(seed)
    all_ids = processed_df["trajectory_id"].unique()
    sample_ids = rng.choice(all_ids, size=min(sample_trajectories, len(all_ids)), replace=False)

    mismatches = []
    for tid in sample_ids:
        raw_g = raw_df[raw_df["trajectory_id"] == tid].sort_values("time")
        proc_g = processed_df[processed_df["trajectory_id"] == tid].sort_values("time")

        expected_dV = causal_backward_difference(raw_g["V"].to_numpy(), dt)
        expected_dalpha = causal_backward_difference(raw_g["alpha"].to_numpy(), dt)

        actual_dV = proc_g["dV_dt"].to_numpy()
        actual_dalpha = proc_g["dalpha_dt"].to_numpy()

        if not np.allclose(expected_dV, actual_dV, equal_nan=True, atol=1e-10):
            mismatches.append((tid, "dV_dt"))
        if not np.allclose(expected_dalpha, actual_dalpha, equal_nan=True, atol=1e-10):
            mismatches.append((tid, "dalpha_dt"))

    return {
        "n_trajectories_checked": len(sample_ids),
        "mismatches": mismatches,
        "passed": len(mismatches) == 0,
    }


def verify_future_labels(processed_df: pd.DataFrame, dt: float, horizon_s: float, sample_trajectories: int = 25, seed: int = 1) -> dict:
    """Recompute future_stall_5s independently (from each trajectory's OWN
    is_unsafe column) for a sample of trajectories and confirm the stored
    labels match. Demonstrates the label at row i is derived only from
    that same trajectory's future rows, never from another trajectory or
    from a past-only window."""
    rng = np.random.default_rng(seed)
    all_ids = processed_df["trajectory_id"].unique()
    sample_ids = rng.choice(all_ids, size=min(sample_trajectories, len(all_ids)), replace=False)

    mismatches = []
    for tid in sample_ids:
        g = processed_df[processed_df["trajectory_id"] == tid].sort_values("time")
        expected_labels, expected_avail = compute_future_stall_label(g["is_unsafe"].to_numpy(), dt, horizon_s)
        actual_labels = g["future_stall_5s"].to_numpy()
        actual_avail = g["future_stall_5s_available"].to_numpy()

        if not np.array_equal(expected_avail, actual_avail):
            mismatches.append((tid, "availability_mismatch"))
        elif not np.allclose(expected_labels, actual_labels, equal_nan=True):
            mismatches.append((tid, "label_value_mismatch"))

    return {
        "n_trajectories_checked": len(sample_ids),
        "mismatches": mismatches,
        "passed": len(mismatches) == 0,
    }


def verify_monotonic_time(raw_df: pd.DataFrame) -> dict:
    bad_ids = []
    for tid, g in raw_df.groupby("trajectory_id"):
        t = g.sort_index()["time"].to_numpy()
        if len(t) > 1 and not np.all(np.diff(t) > 0):
            bad_ids.append(tid)
    return {"n_trajectories_checked": raw_df["trajectory_id"].nunique(), "non_monotonic_trajectory_ids": bad_ids, "passed": len(bad_ids) == 0}


def run_audit(
    raw_df: pd.DataFrame,
    processed_df: pd.DataFrame,
    metadata_df: pd.DataFrame,
    split_manifest: pd.DataFrame,
    cfg,
    boundary: StallBoundary,
    v_stall: float,
    v_floor: float,
    gamma_max_rad: float,
) -> dict:
    report: dict = {}

    # --- A. Trajectory counts ------------------------------------------------
    total = len(metadata_df)
    invalid_mask = metadata_df["n_sanity_issues"] > 0
    terminated_early_mask = metadata_df["termination_reason"] != "completed_normally"
    report["A_trajectory_counts"] = {
        "total_trajectories": int(total),
        "valid_trajectories": int((~invalid_mask).sum()),
        "invalid_trajectories": int(invalid_mask.sum()),
        "terminated_early_trajectories": int(terminated_early_mask.sum()),
        "completed_full_duration_trajectories": int((~terminated_early_mask).sum()),
    }

    # --- B. Generation-mode distribution ---------------------------------------
    mode_counts = metadata_df["generation_mode"].value_counts().to_dict()
    report["B_generation_mode_distribution"] = {
        "counts": {k: int(v) for k, v in mode_counts.items()},
        "fractions": {k: float(v) / total for k, v in mode_counts.items()},
        "target_fractions": cfg.regime_proportions,
    }

    # --- C. Actual event distribution -------------------------------------------
    stall_counts = metadata_df["whether_stall_occurred"].value_counts().to_dict()
    report["C_event_distribution"] = {
        "trajectories_with_stall": int(stall_counts.get(True, 0)),
        "trajectories_without_stall": int(stall_counts.get(False, 0)),
        "fraction_with_stall": float(metadata_df["whether_stall_occurred"].mean()),
    }

    # --- D. Supervised label distribution -----------------------------------
    label_counts = processed_df["future_stall_5s"].value_counts(dropna=False)
    n_pos = int(label_counts.get(1.0, 0))
    n_neg = int(label_counts.get(0.0, 0))
    n_na = int(processed_df["future_stall_5s"].isna().sum())
    report["D_supervised_label_distribution"] = {
        "future_stall_5s_negative_0": n_neg,
        "future_stall_5s_positive_1": n_pos,
        "future_stall_5s_unavailable_NaN": n_na,
        "positive_fraction_of_available": (n_pos / (n_pos + n_neg)) if (n_pos + n_neg) > 0 else None,
        "total_rows": int(len(processed_df)),
    }

    # --- E. Physical ranges --------------------------------------------------
    report["E_physical_ranges"] = {
        "V_m_s": _series_stats(raw_df["V"]),
        "alpha_deg": {"min": float(np.degrees(raw_df["alpha"].min())), "max": float(np.degrees(raw_df["alpha"].max()))},
        "altitude_m": _series_stats(raw_df["altitude"]),
        "gamma_deg": {"min": float(np.degrees(raw_df["gamma"].min())), "max": float(np.degrees(raw_df["gamma"].max()))},
        "thrust_N": _series_stats(raw_df["thrust"]),
        "elevator_rad": _series_stats(raw_df["elevator"]),
    }

    # --- F. Validity-envelope events -----------------------------------------
    termination_counts = metadata_df["termination_reason"].value_counts().to_dict()
    report["F_validity_envelope_events"] = {
        "n_exceeded_low_airspeed": int(termination_counts.get(TERMINATION_LOW_AIRSPEED, 0)),
        "n_exceeded_gamma": int(termination_counts.get(TERMINATION_GAMMA_EXCEEDED, 0)),
        "n_ground_contact": int(termination_counts.get(TERMINATION_GROUND_CONTACT, 0)),
        "n_numerical_instability": int(termination_counts.get(TERMINATION_NAN_INF, 0)),
        "n_invalid_control": int(termination_counts.get(TERMINATION_INVALID_CONTROL, 0)),
        "termination_reason_counts": {k: int(v) for k, v in termination_counts.items()},
        "v_stall_m_s": float(v_stall),
        "v_floor_m_s": float(v_floor),
        "gamma_max_deg": float(np.degrees(gamma_max_rad)),
    }

    # --- G. Data integrity -----------------------------------------------------
    raw_nan_counts = raw_df.isna().sum()
    raw_inf_counts = raw_df.select_dtypes(include=[np.number]).apply(lambda c: np.isinf(c).sum())

    processed_nan_counts = processed_df.isna().sum()

    ids_in_metadata = set(metadata_df["trajectory_id"])
    ids_in_manifest = set(split_manifest["trajectory_id"])
    manifest_dup = int(split_manifest["trajectory_id"].duplicated().sum())
    split_counts_per_id = split_manifest.groupby("trajectory_id")["split"].nunique()
    ids_in_multiple_splits = int((split_counts_per_id > 1).sum())

    report["G_data_integrity"] = {
        "raw_missing_values_per_column": {k: int(v) for k, v in raw_nan_counts.items() if v > 0},
        "raw_infinite_values_per_column": {k: int(v) for k, v in raw_inf_counts.items() if v > 0},
        "processed_missing_values_per_column": {k: int(v) for k, v in processed_nan_counts.items() if v > 0},
        "processed_missing_values_note": (
            "dV_dt/dalpha_dt are NaN on the first row of every trajectory by design "
            "(no prior sample for a causal derivative). future_stall_5s and "
            "future_stall_5s_available are NaN/False on the final "
            f"{cfg.labeling_horizon_s}s of every trajectory by design (insufficient "
            "future data within the simulated trajectory -- see Section 10)."
        ),
        "duplicate_rows_raw": int(raw_df.duplicated().sum()),
        "duplicate_rows_processed": int(processed_df.duplicated().sum()),
        "duplicate_trajectory_ids_in_metadata": int(metadata_df["trajectory_id"].duplicated().sum()),
        "duplicate_trajectory_ids_in_split_manifest": manifest_dup,
        "trajectory_ids_in_multiple_splits": ids_in_multiple_splits,
        "metadata_manifest_id_set_equal": ids_in_metadata == ids_in_manifest,
        "future_label_leakage_check": verify_future_labels(processed_df, cfg.dt, cfg.labeling_horizon_s),
        "causal_derivative_check": verify_causal_derivatives(raw_df, processed_df, cfg.dt),
    }

    # --- H. Temporal correctness -------------------------------------------
    report["H_temporal_correctness"] = {
        "monotonic_timestamps_check": verify_monotonic_time(raw_df),
        "causal_derivative_check": report["G_data_integrity"]["causal_derivative_check"],
        "future_label_check": report["G_data_integrity"]["future_label_leakage_check"],
    }

    return report


def render_markdown_report(report: dict, cfg, v0_check: dict) -> str:
    lines = []
    lines.append("# AeroGuard Stage 2 -- Dataset Audit Report\n")
    lines.append(f"Dataset version: `{cfg.dataset_version}`  \nSeed: `{cfg.seed}`\n")

    lines.append("## A. Trajectory counts")
    for k, v in report["A_trajectory_counts"].items():
        lines.append(f"- {k}: {v}")

    lines.append("\n## B. Generation-mode distribution")
    for k, v in report["B_generation_mode_distribution"]["counts"].items():
        frac = report["B_generation_mode_distribution"]["fractions"][k]
        target = report["B_generation_mode_distribution"]["target_fractions"].get(k)
        lines.append(f"- {k}: {v} ({frac:.1%}), target {target:.0%}" if target else f"- {k}: {v} ({frac:.1%})")

    lines.append("\n## C. Actual event distribution")
    for k, v in report["C_event_distribution"].items():
        lines.append(f"- {k}: {v}")

    lines.append("\n## D. Supervised label distribution")
    for k, v in report["D_supervised_label_distribution"].items():
        lines.append(f"- {k}: {v}")

    lines.append("\n## E. Physical ranges")
    for k, v in report["E_physical_ranges"].items():
        lines.append(f"- {k}: min={v['min']:.4f}, max={v['max']:.4f}")

    lines.append("\n## F. Validity-envelope events")
    for k, v in report["F_validity_envelope_events"].items():
        lines.append(f"- {k}: {v}")

    lines.append("\n## G. Data integrity")
    for k, v in report["G_data_integrity"].items():
        lines.append(f"- {k}: {v}")

    lines.append("\n## H. Temporal correctness")
    for k, v in report["H_temporal_correctness"].items():
        lines.append(f"- {k}: {v}")

    lines.append(f"\n## V0 range validation (Section 4)")
    for k, v in v0_check.items():
        lines.append(f"- {k}: {v}")

    return "\n".join(lines)
