"""AeroGuard Stage 2: generate the initial 1000-trajectory dataset and audit it.

This script does not modify the core physics (aeroguard/) or the trim
solver (scripts/simulate.py). It only calls them.

Run with:
    python scripts/generate_dataset.py
"""

import dataclasses
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from aeroguard.aircraft import Aircraft
from aeroguard_dataset import paths
from aeroguard_dataset.audit import run_audit, render_markdown_report
from aeroguard_dataset.config import GenerationConfig, REGIME_CONTROL_CONFIGS, compute_validity_envelope
from aeroguard_dataset.dataset_builder import build_dataset, RAW_COLUMNS, DERIVED_COLUMNS
from aeroguard_dataset.events import resolve_stall_boundary
from aeroguard_dataset.splitting import split_trajectory_ids, verify_no_overlap
from aeroguard_dataset.visualize import generate_all_plots


class _NumpyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


FEATURE_SCHEMA = {
    "raw_physics_observations": {
        "description": "Recorded directly from the RK4-simulated state and controls at each timestep. Never derived from other rows.",
        "columns": {
            "trajectory_id": "unique identifier for the trajectory this row belongs to",
            "time": "seconds since trajectory start",
            "V": "airspeed [m/s]",
            "alpha": "angle of attack [rad] = theta - gamma",
            "theta": "pitch angle [rad]",
            "gamma": "flight-path angle [rad]",
            "altitude": "altitude h [m]",
            "pitch_rate": "pitch rate q [rad/s]",
            "vertical_speed": "dh/dt = V*sin(gamma) [m/s]",
            "thrust": "thrust force T [N], from aerodynamics.thrust_force(throttle, aircraft)",
            "elevator": "commanded elevator deflection [rad] (raw command; thrust/lift/drag equations use aircraft's own internal clamping where applicable)",
            "throttle": "commanded throttle [dimensionless, nominally 0-1] (raw command; thrust_force() clamps internally for the physics)",
        },
    },
    "derived_features": {
        "description": "Computed in aeroguard_dataset/features.py from the raw columns above, using ONLY current and past samples of the SAME trajectory (causal). See features.causal_backward_difference.",
        "columns": {
            "dV_dt": "backward-difference dV/dt [m/s^2]; NaN on each trajectory's first row",
            "dalpha_dt": "backward-difference dalpha/dt [rad/s]; NaN on each trajectory's first row",
            "stall_margin": "alpha_at_cl_peak - alpha [rad] (signed; see features.py docstring for the negative-alpha caveat)",
            "is_unsafe": "boolean ground-truth event flag: |alpha| > alpha_at_cl_peak (the model's own CL(alpha) peak, numerically located -- see events.py). This IS the physics-defined stall/unsafe event, not a feature meant to be used as model input for predicting itself.",
        },
    },
    "future_outcome_label": {
        "description": "Computed in aeroguard_dataset/labeling.py from EACH TRAJECTORY'S OWN future simulated is_unsafe values. Must never be used as an input feature.",
        "columns": {
            "future_stall_5s": "1.0 if is_unsafe is True for any sample in (t, t+5s] within this trajectory, 0.0 if not, NaN if fewer than 5s of future data remain in this (possibly early-terminated) trajectory",
            "future_stall_5s_available": "boolean twin of future_stall_5s being non-NaN",
        },
    },
}


def _aircraft_params_dict(aircraft: Aircraft) -> dict:
    return dataclasses.asdict(aircraft)


def _config_dict(cfg: GenerationConfig) -> dict:
    d = dataclasses.asdict(cfg)
    return d


def _regime_control_configs_dict() -> dict:
    return {mode: dataclasses.asdict(spec) for mode, spec in REGIME_CONTROL_CONFIGS.items()}


def main():
    paths.ensure_data_dirs()

    cfg = GenerationConfig()
    aircraft = Aircraft()

    print(f"AeroGuard Stage 2 dataset generation")
    print(f"  version={cfg.dataset_version}  seed={cfg.seed}  n_trajectories={cfg.n_trajectories}")
    print(f"  dt={cfg.dt}s  duration={cfg.duration_s}s")

    boundary = resolve_stall_boundary(aircraft)
    v_stall, v_floor, gamma_max_rad = compute_validity_envelope(aircraft, cfg)
    print(f"  stall boundary alpha = {np.degrees(boundary.alpha_at_cl_peak):.3f} deg (CLmax={boundary.cl_max:.4f})")
    print(f"  V_stall={v_stall:.2f} m/s, validity V floor={v_floor:.2f} m/s, gamma max={np.degrees(gamma_max_rad):.1f} deg")

    print("\nGenerating trajectories...")
    raw_df, processed_df, metadata_df, v0_check = build_dataset(cfg, verbose=True)

    print("\nSplitting by trajectory_id (70/15/15)...")
    manifest = split_trajectory_ids(metadata_df["trajectory_id"].tolist(), cfg.seed)
    verify_no_overlap(manifest)
    print(f"  {manifest['split'].value_counts().to_dict()}")

    print("\nSaving datasets to data/ ...")
    raw_path = os.path.join(paths.DATA_RAW_DIR, "raw_telemetry.parquet")
    processed_path = os.path.join(paths.DATA_PROCESSED_DIR, "processed_dataset.parquet")
    metadata_path = os.path.join(paths.DATA_METADATA_DIR, "trajectory_metadata.csv")
    manifest_path = os.path.join(paths.DATA_SPLITS_DIR, "split_manifest.csv")
    gen_config_path = os.path.join(paths.DATA_METADATA_DIR, "generation_config.json")
    feature_schema_path = os.path.join(paths.DATA_METADATA_DIR, "feature_schema.json")

    raw_df.to_parquet(raw_path, index=False)
    processed_df.to_parquet(processed_path, index=False)
    metadata_df.to_csv(metadata_path, index=False)
    manifest.to_csv(manifest_path, index=False)

    full_config = {
        "dataset_version": cfg.dataset_version,
        "seed": cfg.seed,
        "generation_config": _config_dict(cfg),
        "aircraft_parameters": _aircraft_params_dict(aircraft),
        "regime_control_configs": _regime_control_configs_dict(),
        "resolved_validity_envelope": {
            "v_stall_m_s": v_stall,
            "v_floor_m_s": v_floor,
            "gamma_max_rad": gamma_max_rad,
            "gamma_max_deg": np.degrees(gamma_max_rad),
        },
        "resolved_stall_boundary": {
            "alpha_at_cl_peak_rad": boundary.alpha_at_cl_peak,
            "alpha_at_cl_peak_deg": np.degrees(boundary.alpha_at_cl_peak),
            "cl_max": boundary.cl_max,
        },
        "v0_range_validation": v0_check,
        "train_val_test_fractions": {"train": 0.70, "val": 0.15, "test": 0.15},
        "raw_columns": RAW_COLUMNS,
        "derived_columns": DERIVED_COLUMNS,
    }
    with open(gen_config_path, "w") as f:
        json.dump(full_config, f, indent=2, cls=_NumpyJSONEncoder)

    with open(feature_schema_path, "w") as f:
        json.dump(FEATURE_SCHEMA, f, indent=2)

    print(f"  raw telemetry      -> {raw_path}  ({len(raw_df):,} rows)")
    print(f"  processed dataset  -> {processed_path}  ({len(processed_df):,} rows)")
    print(f"  metadata           -> {metadata_path}  ({len(metadata_df):,} rows)")
    print(f"  split manifest     -> {manifest_path}")
    print(f"  generation config  -> {gen_config_path}")
    print(f"  feature schema     -> {feature_schema_path}")

    print("\nRunning dataset audit...")
    report = run_audit(raw_df, processed_df, metadata_df, manifest, cfg, boundary, v_stall, v_floor, gamma_max_rad)
    md_report = render_markdown_report(report, cfg, v0_check)

    os.makedirs(paths.AUDIT_DIR, exist_ok=True)
    report_md_path = os.path.join(paths.AUDIT_DIR, "audit_report.md")
    report_json_path = os.path.join(paths.AUDIT_DIR, "audit_report.json")
    with open(report_md_path, "w") as f:
        f.write(md_report)
    with open(report_json_path, "w") as f:
        json.dump(report, f, indent=2, cls=_NumpyJSONEncoder)

    print(f"  audit report (md)  -> {report_md_path}")
    print(f"  audit report (json)-> {report_json_path}")

    print("\nGenerating audit plots...")
    generate_all_plots(raw_df, processed_df, metadata_df, boundary, v_stall, v_floor, gamma_max_rad, paths.AUDIT_PLOTS_DIR, cfg.seed)
    print(f"  plots -> {paths.AUDIT_PLOTS_DIR}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(md_report)


if __name__ == "__main__":
    main()
