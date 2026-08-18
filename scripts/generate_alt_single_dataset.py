"""Generalization experiment, Phase 4 (part 1) — generate the minimal
alternative-mechanism trajectory sets needed for the generalization test.

Two batches, both using aeroguard_dataset/control_profiles_alt_single.py
(the Phase-3-gated mechanism), same schema/pipeline as
aeroguard_dataset/dataset_builder_v3.py's generate_one_trajectory_v3
(RAW_COLUMNS/DERIVED_COLUMNS, future_stall_5s labeling, sanity checks) so
the resulting parquet files are feature-identical to the frozen v0.3
dataset and can be run through the SAME temporal-feature-panel /
model-evaluation code unchanged:

  1. "holdout" (N=300): used ONLY to evaluate the frozen v0.3 primary
     model (never trained on anything) -- the forward-direction check.
  2. "train_val" (N=350): split 80/20 (trajectory-level, reusing
     aeroguard_dataset.splitting.split_trajectory_ids's convention) for
     the cheap reverse-direction check (train a fresh model on the
     alternative mechanism, test on held-out gradual_approach_v3).

Both batches use a seed offset from the Phase-3 calibration seed so the
RNG streams are disjoint (no trajectory overlap with the calibration
batch or between these two batches). Does NOT touch data/, aeroguard/,
aeroguard_dataset/config.py, aeroguard_dataset/dataset_builder*.py, or
any existing v0.1/v0.2/v0.3 file. Writes only to
outputs/ml_v03_generalization/data/ (new, isolated).

Run with:
    python scripts/generate_alt_single_dataset.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from aeroguard.aircraft import Aircraft
from aeroguard_dataset import paths
from aeroguard_dataset.config import GenerationConfig, compute_validity_envelope
from aeroguard_dataset.control_profiles_alt_single import build_alt_single_pulse_profile
from aeroguard_dataset.events import first_unsafe_index, resolve_stall_boundary
from aeroguard_dataset.features import compute_features_for_trajectory
from aeroguard_dataset.labeling import compute_future_stall_label
from aeroguard_dataset.paths import trim_level_flight
from aeroguard_dataset.splitting import split_trajectory_ids, verify_no_overlap
from aeroguard_dataset.trajectory_sim import simulate_trajectory

OUT_DIR = os.path.join(paths.OUTPUTS_DIR, "ml_v03_generalization", "data")
os.makedirs(OUT_DIR, exist_ok=True)

BASE_SEED = 20260817
HOLDOUT_SEED = BASE_SEED + 1000  # disjoint from calibration (BASE_SEED) and train_val
TRAIN_VAL_SEED = BASE_SEED + 2000
N_HOLDOUT = 300
N_TRAIN_VAL = 350
DT = 0.01
DURATION_S = 20.0
REGIME_NAME = "gradual_alt_single_capped"


def generate_batch(n: int, seed: int, id_prefix: str):
    aircraft = Aircraft()
    boundary = resolve_stall_boundary(aircraft)
    cfg = GenerationConfig()
    v_stall, v_floor, gamma_max_rad = compute_validity_envelope(aircraft, cfg)
    rng = np.random.default_rng(seed)

    raw_frames, processed_frames, metadata_rows = [], [], []
    t0 = time.time()
    for i in range(n):
        tid = f"{id_prefix}_{i:05d}"
        V0 = float(rng.uniform(cfg.v0_min, cfg.v0_max))
        h0 = float(rng.uniform(cfg.altitude_min, cfg.altitude_max))
        alpha_trim, throttle_trim, elevator_trim = trim_level_flight(aircraft, V0)
        profile = build_alt_single_pulse_profile(rng, alpha_trim, throttle_trim, elevator_trim, DURATION_S)

        result = simulate_trajectory(
            trajectory_id=tid, aircraft=aircraft, control_profile=profile,
            V0=V0, gamma0=0.0, alpha0=alpha_trim, h0=h0, q0=0.0,
            duration_s=DURATION_S, dt=DT, v_floor=v_floor, gamma_max_rad=gamma_max_rad,
        )
        features = compute_features_for_trajectory(result, boundary, DT)
        labels, label_available = compute_future_stall_label(features["is_unsafe"], DT, cfg.labeling_horizon_s)

        raw_frame = pd.DataFrame({
            "trajectory_id": result.trajectory_id, "time": result.t, "V": result.V, "alpha": result.alpha,
            "theta": result.theta, "gamma": result.gamma, "altitude": result.altitude, "pitch_rate": result.pitch_rate,
            "vertical_speed": result.vertical_speed, "thrust": result.thrust, "elevator": result.elevator,
            "throttle": result.throttle,
        })
        processed_frame = raw_frame.copy()
        processed_frame["dV_dt"] = features["dV_dt"]
        processed_frame["dalpha_dt"] = features["dalpha_dt"]
        processed_frame["stall_margin"] = features["stall_margin"]
        processed_frame["is_unsafe"] = features["is_unsafe"]
        processed_frame["future_stall_5s"] = labels
        processed_frame["future_stall_5s_available"] = label_available

        stall_occurred = bool(np.any(features["is_unsafe"]))
        first_idx = first_unsafe_index(result.alpha, boundary)
        time_of_first_stall = float(result.t[first_idx]) if first_idx is not None else None

        raw_frames.append(raw_frame)
        processed_frames.append(processed_frame)
        metadata_rows.append({
            "trajectory_id": tid, "generation_mode": REGIME_NAME, "random_seed": seed,
            "initial_airspeed": V0, "initial_altitude": h0, "initial_alpha": alpha_trim,
            "maximum_alpha": float(np.max(result.alpha)) if len(result.alpha) else np.nan,
            "minimum_alpha": float(np.min(result.alpha)) if len(result.alpha) else np.nan,
            "maximum_abs_gamma": float(np.max(np.abs(result.gamma))) if len(result.gamma) else np.nan,
            "whether_stall_occurred": stall_occurred, "time_of_first_stall": time_of_first_stall,
            "termination_reason": result.termination_reason, "n_steps": len(result.t),
            "duration_actual_s": float(result.t[-1]) if len(result.t) else 0.0,
        })
        if (i + 1) % 100 == 0:
            print(f"  [{id_prefix}] {i + 1}/{n} ({time.time() - t0:.1f}s elapsed)")

    raw_df = pd.concat(raw_frames, ignore_index=True)
    processed_df = pd.concat(processed_frames, ignore_index=True)
    metadata_df = pd.DataFrame(metadata_rows)
    print(f"  [{id_prefix}] done: {n} trajectories in {time.time() - t0:.1f}s, "
          f"{int(metadata_df['whether_stall_occurred'].sum())} crossings "
          f"({100 * metadata_df['whether_stall_occurred'].mean():.1f}%)")
    return raw_df, processed_df, metadata_df


def main():
    print(f"=== Generating HOLDOUT batch (forward-direction test set): n={N_HOLDOUT}, seed={HOLDOUT_SEED} ===")
    holdout_raw, holdout_processed, holdout_meta = generate_batch(N_HOLDOUT, HOLDOUT_SEED, "altF_holdout")
    holdout_processed.to_parquet(os.path.join(OUT_DIR, "alt_holdout_processed.parquet"), index=False)
    holdout_meta.to_csv(os.path.join(OUT_DIR, "alt_holdout_metadata.csv"), index=False)
    holdout_meta.assign(split="test").to_csv(os.path.join(OUT_DIR, "alt_holdout_split_manifest.csv"), index=False,
                                              columns=["trajectory_id", "split"])

    print(f"\n=== Generating TRAIN_VAL batch (reverse-direction check): n={N_TRAIN_VAL}, seed={TRAIN_VAL_SEED} ===")
    tv_raw, tv_processed, tv_meta = generate_batch(N_TRAIN_VAL, TRAIN_VAL_SEED, "altF_trainval")
    tv_processed.to_parquet(os.path.join(OUT_DIR, "alt_trainval_processed.parquet"), index=False)
    tv_meta.to_csv(os.path.join(OUT_DIR, "alt_trainval_metadata.csv"), index=False)

    # 80/20 trajectory-level train/val split (reuse the project's own
    # split_trajectory_ids convention, but with an 80/20 split instead of
    # the dataset-generation-stage 70/15/15 -- there is no held-out TEST
    # role here, since evaluation happens on the frozen v0.3 test split's
    # gradual_approach_v3 rows instead).
    import aeroguard_dataset.splitting as splitting_mod
    orig_train_frac, orig_val_frac, orig_test_frac = (
        splitting_mod.TRAIN_FRACTION, splitting_mod.VAL_FRACTION, splitting_mod.TEST_FRACTION,
    )
    splitting_mod.TRAIN_FRACTION, splitting_mod.VAL_FRACTION, splitting_mod.TEST_FRACTION = 0.80, 0.20, 0.0
    try:
        manifest = split_trajectory_ids(tv_meta["trajectory_id"].tolist(), seed=TRAIN_VAL_SEED)
    finally:
        splitting_mod.TRAIN_FRACTION, splitting_mod.VAL_FRACTION, splitting_mod.TEST_FRACTION = (
            orig_train_frac, orig_val_frac, orig_test_frac,
        )
    manifest = manifest[manifest["split"] != "test"]  # test_frac=0 should already guarantee this; belt & suspenders
    verify_no_overlap(manifest)
    manifest.to_csv(os.path.join(OUT_DIR, "alt_trainval_split_manifest.csv"), index=False)
    print(f"  train_val split: {(manifest['split'] == 'train').sum()} train / {(manifest['split'] == 'val').sum()} val")

    print(f"\nDone. Outputs in {OUT_DIR}")


if __name__ == "__main__":
    main()
