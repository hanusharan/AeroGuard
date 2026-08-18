"""AeroGuard v0.3: generate the FULL dataset using the locked Candidate D
v3 control profile (outputs/v03_calibration/candidate_d_final_gate_report.md,
CASE A / READY) and audit it.

v0.3 differs from v0.2 ONLY in the "near_boundary"-equivalent regime,
replaced by "gradual_approach_v3" (locked Candidate D v3: same-sign +
zero-gap two-pulse sequencing from v2, + 7.0s combined-duration cap from
v3 -- aeroguard_dataset/control_profiles_candidate_d_v3.py, UNCHANGED
here). "normal" and "stall" control configs are byte-identical to
v0.1/v0.2 (NORMAL_CONTROL_CONFIG, STALL_CONTROL_CONFIG, imported not
redefined). Same dt/duration/V0/altitude ranges/validity envelope/
labeling horizon/70-15-15 split methodology as v0.1/v0.2.

Does not modify v0.1/v0.2 data, aeroguard/ physics, or any existing
calibration output -- everything is written to _v3-suffixed files /
dataset_audit_v3/.

TRAJECTORY COUNT (Task instruction #5 -- stated before generation):
Candidate D v3's observed crossing rate was 21/175 = 12.0% (calibration
run, outputs/v03_calibration/candidate_d_v3_summary.json). Wilson 95% CI
for this proportion: [8.0%, 17.6%]. v0.2's total crossing count (matching
target, "same or better") was 192 trajectories (31 near_boundary + 161
stall, trajectory_metadata_v2.csv). Using the CONSERVATIVE (95% CI lower
bound) rate of 8.0% rather than the point estimate, so the target is met
even under the more pessimistic end of the calibration-run uncertainty:
    N_gradual = ceil(192 / 0.080) = 2400
"normal" and "stall" are kept at v0.2's own ABSOLUTE counts (500 and 250
respectively) -- same configs, same counts, "preserved unchanged" in the
strongest sense -- with gradual_approach_v3 added on top to carry the
crossing-example target (this is also principled: stall-regime crossings
are known, from the reconciliation work, to have ~0.33s median precursor
-- adding more of them would not serve the actual research goal of
genuine multi-second precursors, so the target is sized against
gradual_approach_v3's OWN yield alone, not padded out by stall).
    N_total = 500 + 250 + 2400 = 3150

Run with:
    python scripts/generate_dataset_v3.py
"""
import dataclasses
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from aeroguard.aircraft import Aircraft
from aeroguard_dataset import paths
from aeroguard_dataset.audit import run_audit, render_markdown_report
from aeroguard_dataset.config import GenerationConfig, NORMAL_CONTROL_CONFIG, STALL_CONTROL_CONFIG, compute_validity_envelope
from aeroguard_dataset.control_profiles_candidate_d_v2 import CANDIDATE_D_V2_ELEVATOR_SPEC
from aeroguard_dataset.control_profiles_candidate_d_v3 import TOTAL_DURATION_CAP_S
from aeroguard_dataset.dataset_builder import DERIVED_COLUMNS, RAW_COLUMNS
from aeroguard_dataset.dataset_builder_v3 import GRADUAL_APPROACH_V3_REGIME_NAME, build_dataset_v3
from aeroguard_dataset.events import resolve_stall_boundary
from aeroguard_dataset.splitting import split_trajectory_ids, verify_no_overlap
from aeroguard_dataset.visualize import generate_all_plots

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_dataset import FEATURE_SCHEMA, _NumpyJSONEncoder, _aircraft_params_dict, _config_dict  # noqa: E402

SEED = 20260823  # fresh seed, distinct from v0.1/v0.2 (20260817) and all calibration runs
REGIME_COUNTS = {"normal": 500, "stall": 250, GRADUAL_APPROACH_V3_REGIME_NAME: 2400}
N_TOTAL = sum(REGIME_COUNTS.values())
DATASET_VERSION = "stage2-v0.3-full"

AUDIT_DIR_V3 = os.path.join(paths.OUTPUTS_DIR, "dataset_audit_v3")
AUDIT_PLOTS_DIR_V3 = os.path.join(AUDIT_DIR_V3, "plots")


def main():
    paths.ensure_data_dirs()
    os.makedirs(AUDIT_PLOTS_DIR_V3, exist_ok=True)

    print("=" * 70)
    print("v0.3 TRAJECTORY COUNT JUSTIFICATION")
    print("=" * 70)
    p_hat = 21 / 175
    z = 1.959964
    n_cal = 175
    denom = 1 + z**2 / n_cal
    center = (p_hat + z**2 / (2 * n_cal)) / denom
    half = (z / denom) * math.sqrt(p_hat * (1 - p_hat) / n_cal + z**2 / (4 * n_cal**2))
    ci_lo, ci_hi = center - half, center + half
    print(f"Candidate D v3 calibration crossing rate: {p_hat:.1%} (21/175)")
    print(f"Wilson 95% CI: [{ci_lo:.1%}, {ci_hi:.1%}]")
    print(f"v0.2 total crossing count (target): 192")
    print(f"N_gradual (point estimate 12.0%): {math.ceil(192/p_hat)}")
    print(f"N_gradual (conservative, CI lower bound {ci_lo:.1%}): {math.ceil(192/ci_lo)} -> using 2400")
    print(f"Regime counts: {REGIME_COUNTS}  (normal/stall = v0.2's own absolute counts, unchanged)")
    print(f"N_total = {N_TOTAL}")

    cfg = dataclasses.replace(
        GenerationConfig(), seed=SEED, n_trajectories=N_TOTAL, dataset_version=DATASET_VERSION,
        regime_proportions={k: v / N_TOTAL for k, v in REGIME_COUNTS.items()},
    )
    aircraft = Aircraft()
    boundary = resolve_stall_boundary(aircraft)
    v_stall, v_floor, gamma_max_rad = compute_validity_envelope(aircraft, cfg)

    print("\nResolved configuration for this run:")
    print(f"  dataset_version = {cfg.dataset_version}")
    print(f"  seed            = {cfg.seed}")
    print(f"  n_trajectories  = {cfg.n_trajectories}")
    print(f"  regime_counts   = {REGIME_COUNTS}")
    print(f"  dt = {cfg.dt}s, duration = {cfg.duration_s}s")
    print(f"  V0 range = [{cfg.v0_min}, {cfg.v0_max}] m/s, altitude range = [{cfg.altitude_min}, {cfg.altitude_max}] m")
    print(f"  validity envelope: V_stall={v_stall:.4f} m/s, V_floor={v_floor:.4f} m/s, gamma_max={np.degrees(gamma_max_rad):.1f} deg")
    print(f"  stall boundary alpha = {np.degrees(boundary.alpha_at_cl_peak):.4f} deg")
    print(f"  gradual_approach_v3: elevator mag=[{CANDIDATE_D_V2_ELEVATOR_SPEC.magnitude_min},{CANDIDATE_D_V2_ELEVATOR_SPEC.magnitude_max}] rad, "
          f"rise=[{CANDIDATE_D_V2_ELEVATOR_SPEC.rise_s_min},{CANDIDATE_D_V2_ELEVATOR_SPEC.rise_s_max}]s, "
          f"hold=[{CANDIDATE_D_V2_ELEVATOR_SPEC.hold_s_min},{CANDIDATE_D_V2_ELEVATOR_SPEC.hold_s_max}]s, "
          f"fall=[{CANDIDATE_D_V2_ELEVATOR_SPEC.fall_s_min},{CANDIDATE_D_V2_ELEVATOR_SPEC.fall_s_max}]s, "
          f"same-sign + zero-gap sequencing, {TOTAL_DURATION_CAP_S}s combined-duration cap")

    print("\nGenerating trajectories (v0.3 regime mix)...")
    raw_df, processed_df, metadata_df, v0_check = build_dataset_v3(cfg, REGIME_COUNTS, verbose=True)

    regime_counts_actual = metadata_df["generation_mode"].value_counts().to_dict()
    print(f"\nRegime counts (actual): {regime_counts_actual}")
    assert regime_counts_actual == REGIME_COUNTS, (regime_counts_actual, REGIME_COUNTS)

    print("\nSplitting by trajectory_id (70/15/15)...")
    manifest = split_trajectory_ids(metadata_df["trajectory_id"].tolist(), cfg.seed)
    verify_no_overlap(manifest)
    print(f"  {manifest['split'].value_counts().to_dict()}")

    print("\nSaving v0.3 datasets to data/ (versioned filenames, v0.1/v0.2 files untouched)...")
    raw_path = os.path.join(paths.DATA_RAW_DIR, "raw_telemetry_v3.parquet")
    processed_path = os.path.join(paths.DATA_PROCESSED_DIR, "processed_dataset_v3.parquet")
    metadata_path = os.path.join(paths.DATA_METADATA_DIR, "trajectory_metadata_v3.csv")
    manifest_path = os.path.join(paths.DATA_SPLITS_DIR, "split_manifest_v3.csv")
    gen_config_path = os.path.join(paths.DATA_METADATA_DIR, "generation_config_v3.json")
    feature_schema_path = os.path.join(paths.DATA_METADATA_DIR, "feature_schema_v3.json")

    raw_df.to_parquet(raw_path, index=False)
    processed_df.to_parquet(processed_path, index=False)
    metadata_df.to_csv(metadata_path, index=False)
    manifest.to_csv(manifest_path, index=False)

    full_config = {
        "dataset_version": cfg.dataset_version,
        "seed": cfg.seed,
        "generation_config": _config_dict(cfg),
        "aircraft_parameters": _aircraft_params_dict(aircraft),
        "regime_counts": REGIME_COUNTS,
        "regime_control_configs": {
            "normal": dataclasses.asdict(NORMAL_CONTROL_CONFIG),
            "stall": dataclasses.asdict(STALL_CONTROL_CONFIG),
            "gradual_approach_v3": {
                "elevator_spec": dataclasses.asdict(CANDIDATE_D_V2_ELEVATOR_SPEC),
                "sequencing": "same_sign_zero_gap (v2 fix)",
                "combined_duration_cap_s": TOTAL_DURATION_CAP_S,
                "n_pulses": 2,
                "throttle": "inert",
                "source": "aeroguard_dataset/control_profiles_candidate_d_v3.py (locked, CASE A)",
            },
        },
        "trajectory_count_justification": {
            "candidate_d_v3_calibration_crossing_rate": p_hat,
            "wilson_95pct_ci": [ci_lo, ci_hi],
            "v02_target_crossing_count": 192,
            "n_gradual_conservative": REGIME_COUNTS[GRADUAL_APPROACH_V3_REGIME_NAME],
            "n_normal": REGIME_COUNTS["normal"], "n_stall": REGIME_COUNTS["stall"],
            "n_total": N_TOTAL,
        },
        "resolved_validity_envelope": {"v_stall_m_s": v_stall, "v_floor_m_s": v_floor, "gamma_max_rad": gamma_max_rad, "gamma_max_deg": np.degrees(gamma_max_rad)},
        "resolved_stall_boundary": {"alpha_at_cl_peak_rad": boundary.alpha_at_cl_peak, "alpha_at_cl_peak_deg": np.degrees(boundary.alpha_at_cl_peak), "cl_max": boundary.cl_max},
        "v0_range_validation": v0_check,
        "train_val_test_fractions": {"train": 0.70, "val": 0.15, "test": 0.15},
        "raw_columns": RAW_COLUMNS,
        "derived_columns": DERIVED_COLUMNS,
        "note": "gradual_approach_v3 replaces near_boundary; normal and stall are byte-identical to v0.1/v0.2 configs, at v0.2's own absolute counts.",
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
    report_md_path = os.path.join(AUDIT_DIR_V3, "audit_report_v3.md")
    report_json_path = os.path.join(AUDIT_DIR_V3, "audit_report_v3.json")
    with open(report_md_path, "w") as f:
        f.write(md_report)
    with open(report_json_path, "w") as f:
        json.dump(report, f, indent=2, cls=_NumpyJSONEncoder)
    print(f"  audit report (md)  -> {report_md_path}")
    print(f"  audit report (json)-> {report_json_path}")

    print("\nGenerating audit plots...")
    generate_all_plots(raw_df, processed_df, metadata_df, boundary, v_stall, v_floor, gamma_max_rad, AUDIT_PLOTS_DIR_V3, cfg.seed)
    print(f"  plots -> {AUDIT_PLOTS_DIR_V3}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(md_report)


if __name__ == "__main__":
    main()
