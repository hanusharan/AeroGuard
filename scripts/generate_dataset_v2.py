"""AeroGuard Stage 2: generate the FULL v0.2 dataset (1000 trajectories) and audit it.

v0.2 differs from v0.1 ONLY in the "near_boundary" control-profile
regime (REGIME_CONTROL_CONFIGS_V2, calibrated on a 150-trajectory batch
-- see outputs/dataset_audit_v2_calibration/). "normal" and "stall" are
byte-for-byte identical to v0.1. Same seed, same V0/altitude ranges,
same validity envelope, same 70/15/15 split methodology.

This does not modify or overwrite the v0.1 outputs -- everything is
written to _v2-suffixed files / dataset_audit_v2/ so the two datasets
can be compared directly afterward.

Does not modify aeroguard/ (physics), scripts/simulate.py (trim solver),
or any existing test.

Run with:
    python scripts/generate_dataset_v2.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from aeroguard.aircraft import Aircraft
from aeroguard_dataset import paths
from aeroguard_dataset.audit import run_audit, render_markdown_report
from aeroguard_dataset.config import (
    REGIME_CONTROL_CONFIGS,
    REGIME_CONTROL_CONFIGS_V2,
    compute_validity_envelope,
    make_generation_config_v2,
)
from aeroguard_dataset.dataset_builder import build_dataset, RAW_COLUMNS, DERIVED_COLUMNS
from aeroguard_dataset.events import resolve_stall_boundary
from aeroguard_dataset.splitting import split_trajectory_ids, verify_no_overlap
from aeroguard_dataset.visualize import generate_all_plots

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_dataset import (  # noqa: E402 -- reuse, don't duplicate
    FEATURE_SCHEMA,
    _NumpyJSONEncoder,
    _aircraft_params_dict,
    _config_dict,
)

N_TRAJECTORIES = 1000
SEED = 20260817


def _verify_using_v2_configs():
    """Section requirement: verify (not assume) that the runner is
    actually wired to REGIME_CONTROL_CONFIGS_V2, not the v0.1 mapping."""
    assert set(REGIME_CONTROL_CONFIGS_V2.keys()) == {"normal", "near_boundary", "stall"}, REGIME_CONTROL_CONFIGS_V2.keys()
    assert "boundary" not in REGIME_CONTROL_CONFIGS_V2, "v0.1's 'boundary' key should not be present in V2"
    assert REGIME_CONTROL_CONFIGS_V2["normal"] is REGIME_CONTROL_CONFIGS["normal"], "normal must be unchanged from v0.1"
    assert REGIME_CONTROL_CONFIGS_V2["stall"] is REGIME_CONTROL_CONFIGS["stall"], "stall must be unchanged from v0.1"
    nb = REGIME_CONTROL_CONFIGS_V2["near_boundary"]
    old_boundary = REGIME_CONTROL_CONFIGS["boundary"]
    assert nb is not old_boundary
    assert (nb.elevator.hold_s_min, nb.elevator.hold_s_max) != (old_boundary.elevator.hold_s_min, old_boundary.elevator.hold_s_max)
    print("VERIFIED: using REGIME_CONTROL_CONFIGS_V2 (normal/stall identical objects to v0.1; near_boundary is new)")
    print(f"  near_boundary elevator: magnitude=[{nb.elevator.magnitude_min},{nb.elevator.magnitude_max}] rad, "
          f"rise=[{nb.elevator.rise_s_min},{nb.elevator.rise_s_max}]s, hold=[{nb.elevator.hold_s_min},{nb.elevator.hold_s_max}]s, "
          f"fall=[{nb.elevator.fall_s_min},{nb.elevator.fall_s_max}]s")
    print(f"  (v0.1 boundary for comparison) elevator: magnitude=[{old_boundary.elevator.magnitude_min},{old_boundary.elevator.magnitude_max}] rad, "
          f"hold=[{old_boundary.elevator.hold_s_min},{old_boundary.elevator.hold_s_max}]s  <- note the much longer hold this replaces")


def main():
    paths.ensure_data_dirs()

    _verify_using_v2_configs()

    cfg = make_generation_config_v2(n_trajectories=N_TRAJECTORIES, seed=SEED)
    aircraft = Aircraft()

    boundary = resolve_stall_boundary(aircraft)
    v_stall, v_floor, gamma_max_rad = compute_validity_envelope(aircraft, cfg)

    print("\nResolved configuration for this run:")
    print(f"  dataset_version = {cfg.dataset_version}")
    print(f"  seed            = {cfg.seed}")
    print(f"  n_trajectories  = {cfg.n_trajectories}")
    print(f"  regime_proportions = {cfg.regime_proportions}  (keys must match REGIME_CONTROL_CONFIGS_V2)")
    print(f"  dt = {cfg.dt}s, duration = {cfg.duration_s}s")
    print(f"  V0 range = [{cfg.v0_min}, {cfg.v0_max}] m/s")
    print(f"  altitude range = [{cfg.altitude_min}, {cfg.altitude_max}] m")
    print(f"  validity envelope: V_stall={v_stall:.4f} m/s, V_floor={v_floor:.4f} m/s "
          f"({cfg.validity_v_floor_fraction_of_vstall}*V_stall), gamma_max={np.degrees(gamma_max_rad):.1f} deg")
    print(f"  stall boundary alpha = {np.degrees(boundary.alpha_at_cl_peak):.4f} deg (CLmax={boundary.cl_max:.4f})")
    print(f"  labeling horizon = {cfg.labeling_horizon_s}s")

    print("\nGenerating trajectories (v0.2 regime mix)...")
    raw_df, processed_df, metadata_df, v0_check = build_dataset(
        cfg, verbose=True, regime_control_configs=REGIME_CONTROL_CONFIGS_V2
    )

    regime_counts = metadata_df["generation_mode"].value_counts().to_dict()
    print(f"\nRegime counts: {regime_counts}")
    assert sum(regime_counts.values()) == N_TRAJECTORIES

    print("\nSplitting by trajectory_id (70/15/15)...")
    manifest = split_trajectory_ids(metadata_df["trajectory_id"].tolist(), cfg.seed)
    verify_no_overlap(manifest)
    print(f"  {manifest['split'].value_counts().to_dict()}")

    print("\nSaving v0.2 datasets to data/ (versioned filenames, v0.1 files untouched)...")
    raw_path = os.path.join(paths.DATA_RAW_DIR, "raw_telemetry_v2.parquet")
    processed_path = os.path.join(paths.DATA_PROCESSED_DIR, "processed_dataset_v2.parquet")
    metadata_path = os.path.join(paths.DATA_METADATA_DIR, "trajectory_metadata_v2.csv")
    manifest_path = os.path.join(paths.DATA_SPLITS_DIR, "split_manifest_v2.csv")
    gen_config_path = os.path.join(paths.DATA_METADATA_DIR, "generation_config_v2.json")
    feature_schema_path = os.path.join(paths.DATA_METADATA_DIR, "feature_schema_v2.json")

    raw_df.to_parquet(raw_path, index=False)
    processed_df.to_parquet(processed_path, index=False)
    metadata_df.to_csv(metadata_path, index=False)
    manifest.to_csv(manifest_path, index=False)

    full_config = {
        "dataset_version": cfg.dataset_version,
        "seed": cfg.seed,
        "generation_config": _config_dict(cfg),
        "aircraft_parameters": _aircraft_params_dict(aircraft),
        "regime_control_configs": {mode: __import__("dataclasses").asdict(spec) for mode, spec in REGIME_CONTROL_CONFIGS_V2.items()},
        "resolved_validity_envelope": {
            "v_stall_m_s": v_stall, "v_floor_m_s": v_floor,
            "gamma_max_rad": gamma_max_rad, "gamma_max_deg": np.degrees(gamma_max_rad),
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
        "note": "near_boundary uses REGIME_CONTROL_CONFIGS_V2; normal and stall are identical to v0.1.",
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

    os.makedirs(paths.AUDIT_DIR_V2, exist_ok=True)
    report_md_path = os.path.join(paths.AUDIT_DIR_V2, "audit_report_v2.md")
    report_json_path = os.path.join(paths.AUDIT_DIR_V2, "audit_report_v2.json")
    with open(report_md_path, "w") as f:
        f.write(md_report)
    with open(report_json_path, "w") as f:
        json.dump(report, f, indent=2, cls=_NumpyJSONEncoder)
    print(f"  audit report (md)  -> {report_md_path}")
    print(f"  audit report (json)-> {report_json_path}")

    print("\nGenerating audit plots...")
    generate_all_plots(raw_df, processed_df, metadata_df, boundary, v_stall, v_floor, gamma_max_rad, paths.AUDIT_PLOTS_DIR_V2, cfg.seed)
    print(f"  plots -> {paths.AUDIT_PLOTS_DIR_V2}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(md_report)


if __name__ == "__main__":
    main()
