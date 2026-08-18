"""v0.3 full-dataset generation orchestrator.

Mirrors aeroguard_dataset/dataset_builder.py's generate_one_trajectory /
build_dataset exactly (same RAW_COLUMNS/DERIVED_COLUMNS schema, same
trim_level_flight / simulate_trajectory / compute_features_for_trajectory
/ compute_future_stall_label / sanity_check_trajectory calls, same
metadata_row fields, same regime-shuffling convention as
dataset_builder.assign_regimes) so v0.3 is directly comparable to v0.1/v0.2
row-for-row and column-for-column.

The ONE addition: build_dataset() cannot generate the locked Candidate D
v3 regime, because generate_one_trajectory() always calls the
general-purpose control_profiles.build_control_profile() (a RegimeControlConfig
-> pulses function), and Candidate D v3's profile builder
(control_profiles_candidate_d_v3.build_candidate_d_v3_profile) has a
different signature (no RegimeControlConfig; it has the same-sign/
zero-gap/duration-cap logic baked in). This module adds a per-regime
PROFILE BUILDER DISPATCH so "gradual_approach_v3" trajectories use the
locked Candidate D v3 builder while "normal"/"stall" trajectories use the
unmodified, standard build_control_profile() with NORMAL_CONTROL_CONFIG/
STALL_CONTROL_CONFIG (byte-identical to v0.1/v0.2 -- imported, never
redefined).

Does NOT modify aeroguard/, aeroguard_dataset/dataset_builder.py,
aeroguard_dataset/config.py, aeroguard_dataset/control_profiles.py, or
any v0.1/v0.2 data.
"""
import time
from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd

from aeroguard.aircraft import Aircraft

from .config import GenerationConfig, NORMAL_CONTROL_CONFIG, STALL_CONTROL_CONFIG, compute_validity_envelope, validate_v0_range
from .control_profiles import build_control_profile
from .control_profiles_candidate_d_v3 import TOTAL_DURATION_CAP_S, build_candidate_d_v3_profile
from .dataset_builder import DERIVED_COLUMNS, RAW_COLUMNS, TrajectoryOutput, sanity_check_trajectory
from .events import StallBoundary, first_unsafe_index, resolve_stall_boundary
from .features import compute_features_for_trajectory
from .labeling import compute_future_stall_label
from .paths import trim_level_flight
from .trajectory_sim import TrajectoryResult, simulate_trajectory

GRADUAL_APPROACH_V3_REGIME_NAME = "gradual_approach_v3"


def assign_regime_list(counts: dict, rng: np.random.Generator) -> List[str]:
    """Build an exact-count (not rounded-proportion) regime assignment list
    and shuffle it -- same shuffling convention as
    dataset_builder.assign_regimes (interleaved, not ID-ordered blocks),
    but driven by explicit per-regime COUNTS (500 normal / 250 stall /
    N gradual_approach_v3) rather than fractions, since the whole point of
    this run is a specific, statistically-justified absolute count for the
    gradual_approach_v3 regime (see scripts/generate_dataset_v3.py)."""
    modes: List[str] = []
    for mode, count in counts.items():
        modes.extend([mode] * count)
    modes_array = np.array(modes)
    rng.shuffle(modes_array)
    return modes_array.tolist()


def generate_one_trajectory_v3(
    idx: int,
    regime: str,
    rng: np.random.Generator,
    aircraft: Aircraft,
    cfg: GenerationConfig,
    boundary: StallBoundary,
    v_floor: float,
    gamma_max_rad: float,
) -> TrajectoryOutput:
    trajectory_id = f"traj_{idx:05d}"

    V0 = float(rng.uniform(cfg.v0_min, cfg.v0_max))
    h0 = float(rng.uniform(cfg.altitude_min, cfg.altitude_max))
    alpha_trim, throttle_trim, elevator_trim = trim_level_flight(aircraft, V0)

    if regime == GRADUAL_APPROACH_V3_REGIME_NAME:
        profile = build_candidate_d_v3_profile(rng, alpha_trim, throttle_trim, elevator_trim, cfg.duration_s,
                                                cap_s=TOTAL_DURATION_CAP_S)
    elif regime == "normal":
        profile = build_control_profile(rng, NORMAL_CONTROL_CONFIG, alpha_trim, throttle_trim, elevator_trim, cfg.duration_s)
    elif regime == "stall":
        profile = build_control_profile(rng, STALL_CONTROL_CONFIG, alpha_trim, throttle_trim, elevator_trim, cfg.duration_s)
    else:
        raise ValueError(f"unknown v0.3 regime: {regime}")

    result = simulate_trajectory(
        trajectory_id=trajectory_id, aircraft=aircraft, control_profile=profile,
        V0=V0, gamma0=0.0, alpha0=alpha_trim, h0=h0, q0=0.0,
        duration_s=cfg.duration_s, dt=cfg.dt, v_floor=v_floor, gamma_max_rad=gamma_max_rad,
    )

    features = compute_features_for_trajectory(result, boundary, cfg.dt)
    labels, label_available = compute_future_stall_label(features["is_unsafe"], cfg.dt, cfg.labeling_horizon_s)
    sanity_issues = sanity_check_trajectory(result)

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

    metadata_row = {
        "trajectory_id": trajectory_id, "generation_mode": regime, "random_seed": cfg.seed,
        "initial_airspeed": V0, "initial_altitude": h0, "initial_alpha": alpha_trim,
        "trim_throttle": throttle_trim, "trim_elevator": elevator_trim,
        "maximum_alpha": float(np.max(result.alpha)) if len(result.alpha) else np.nan,
        "minimum_alpha": float(np.min(result.alpha)) if len(result.alpha) else np.nan,
        "minimum_airspeed": float(np.min(result.V)) if len(result.V) else np.nan,
        "maximum_airspeed": float(np.max(result.V)) if len(result.V) else np.nan,
        "maximum_abs_gamma": float(np.max(np.abs(result.gamma))) if len(result.gamma) else np.nan,
        "whether_stall_occurred": stall_occurred, "time_of_first_stall": time_of_first_stall,
        "whether_validity_envelope_was_exceeded": result.validity_envelope_exceeded,
        "termination_reason": result.termination_reason, "n_steps": len(result.t),
        "duration_actual_s": float(result.t[-1]) if len(result.t) else 0.0,
        "n_sanity_issues": len(sanity_issues), "sanity_issues": ";".join(sanity_issues) if sanity_issues else "",
    }
    return TrajectoryOutput(raw_frame=raw_frame, processed_frame=processed_frame, metadata_row=metadata_row)


def build_dataset_v3(cfg: GenerationConfig, regime_counts: dict, verbose: bool = True):
    """regime_counts: exact per-regime trajectory counts, e.g.
    {"normal": 500, "stall": 250, "gradual_approach_v3": 2400}. Sum must
    equal cfg.n_trajectories. Returns (raw_df, processed_df, metadata_df, v0_check)."""
    assert sum(regime_counts.values()) == cfg.n_trajectories, (sum(regime_counts.values()), cfg.n_trajectories)

    aircraft = Aircraft()
    v0_check = validate_v0_range(aircraft, cfg)
    if not v0_check["v0_min_above_vstall"]:
        raise ValueError(f"Requested v0_min={cfg.v0_min} is not above stall speed ({v0_check['v_stall_m_s']:.2f} m/s)")

    boundary = resolve_stall_boundary(aircraft)
    v_stall, v_floor, gamma_max_rad = compute_validity_envelope(aircraft, cfg)

    master_rng = np.random.default_rng(cfg.seed)
    regimes = assign_regime_list(regime_counts, master_rng)

    raw_frames, processed_frames, metadata_rows = [], [], []
    t_start = time.time()
    for i, regime in enumerate(regimes):
        out = generate_one_trajectory_v3(i, regime, master_rng, aircraft, cfg, boundary, v_floor, gamma_max_rad)
        raw_frames.append(out.raw_frame)
        processed_frames.append(out.processed_frame)
        metadata_rows.append(out.metadata_row)
        if verbose and (i + 1) % 250 == 0:
            elapsed = time.time() - t_start
            print(f"  generated {i + 1}/{cfg.n_trajectories} trajectories ({elapsed:.1f}s elapsed)")

    raw_df = pd.concat(raw_frames, ignore_index=True)
    processed_df = pd.concat(processed_frames, ignore_index=True)
    metadata_df = pd.DataFrame(metadata_rows)
    if verbose:
        print(f"Done: {cfg.n_trajectories} trajectories in {time.time() - t_start:.1f}s")
    return raw_df, processed_df, metadata_df, v0_check
