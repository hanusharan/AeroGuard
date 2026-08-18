"""Orchestrates generation of the full trajectory dataset.

Threads a single seeded numpy Generator through the entire run, in a
fixed order (regime assignment, then per-trajectory V0/altitude/control
sampling), so the whole dataset is reproducible from one seed.
"""

import time
from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd

from aeroguard.aircraft import Aircraft

from .config import GenerationConfig, REGIME_CONTROL_CONFIGS, compute_validity_envelope, validate_v0_range
from .control_profiles import build_control_profile
from .events import resolve_stall_boundary, StallBoundary, first_unsafe_index
from .features import compute_features_for_trajectory
from .labeling import compute_future_stall_label
from .paths import trim_level_flight
from .trajectory_sim import simulate_trajectory, TrajectoryResult, VALIDITY_ENVELOPE_TERMINATIONS

RAW_COLUMNS = [
    "trajectory_id", "time", "V", "alpha", "theta", "gamma", "altitude",
    "pitch_rate", "vertical_speed", "thrust", "elevator", "throttle",
]
DERIVED_COLUMNS = ["dV_dt", "dalpha_dt", "stall_margin", "is_unsafe", "future_stall_5s", "future_stall_5s_available"]


def sanity_check_trajectory(result: TrajectoryResult) -> List[str]:
    """Post-hoc sanity checks (Section 18). Returns a list of issue
    strings; empty list means clean. Never deletes or silently alters
    the trajectory -- issues are recorded for the audit."""
    issues: List[str] = []

    if len(result.t) == 0:
        issues.append("empty_trajectory")
        return issues

    if not np.all(np.isfinite(result.V)) or not np.all(np.isfinite(result.alpha)) or not np.all(np.isfinite(result.altitude)):
        issues.append("nan_or_inf_in_raw_state")

    if np.any(result.V <= 0):
        issues.append("nonpositive_airspeed")

    if len(result.t) > 1 and not np.all(np.diff(result.t) > 0):
        issues.append("non_monotonic_timestamps")

    if len(result.t) > 1:
        dt_steps = np.diff(result.t)
        if not np.allclose(dt_steps, dt_steps[0], rtol=1e-6):
            issues.append("irregular_timestep")

    if np.any(result.throttle < -1.0) or np.any(result.throttle > 2.0):
        # Commanded throttle far outside [0,1]; thrust_force() clamps it
        # internally so the physics itself stayed correct, but the raw
        # command is unusual enough to flag.
        issues.append("throttle_command_far_outside_unit_range")

    if np.any(np.abs(result.elevator) > 1.0):  # ~57 deg, well beyond any configured perturbation range
        issues.append("elevator_command_unexpectedly_large")

    return issues


@dataclass
class TrajectoryOutput:
    raw_frame: pd.DataFrame
    processed_frame: pd.DataFrame
    metadata_row: dict


def assign_regimes(rng: np.random.Generator, n: int, proportions: dict) -> List[str]:
    """Deterministically assign a generation regime to each of the n
    trajectory slots, honoring the target proportions (rounded to whole
    trajectories) and shuffled so regimes interleave rather than forming
    ID-ordered blocks."""
    counts = {mode: int(round(p * n)) for mode, p in proportions.items()}
    # Rounding can leave the total off by a trajectory or two; fix up
    # deterministically against the largest bucket.
    diff = n - sum(counts.values())
    if diff != 0:
        largest_mode = max(counts, key=counts.get)
        counts[largest_mode] += diff

    modes: List[str] = []
    for mode, count in counts.items():
        modes.extend([mode] * count)

    modes_array = np.array(modes)
    rng.shuffle(modes_array)
    return modes_array.tolist()


def generate_one_trajectory(
    idx: int,
    regime: str,
    rng: np.random.Generator,
    aircraft: Aircraft,
    cfg: GenerationConfig,
    boundary: StallBoundary,
    v_floor: float,
    gamma_max_rad: float,
    regime_control_configs: dict = None,
) -> TrajectoryOutput:
    """regime_control_configs defaults to the v0.1 REGIME_CONTROL_CONFIGS
    if not given, so existing (v0.1) callers are unaffected. Pass
    config.REGIME_CONTROL_CONFIGS_V2 (or any other regime-name ->
    RegimeControlConfig mapping) to generate under a different
    control-profile strategy without touching this function's logic."""
    if regime_control_configs is None:
        regime_control_configs = REGIME_CONTROL_CONFIGS

    trajectory_id = f"traj_{idx:04d}"

    V0 = float(rng.uniform(cfg.v0_min, cfg.v0_max))
    h0 = float(rng.uniform(cfg.altitude_min, cfg.altitude_max))

    alpha_trim, throttle_trim, elevator_trim = trim_level_flight(aircraft, V0)

    profile = build_control_profile(
        rng, regime_control_configs[regime], alpha_trim, throttle_trim, elevator_trim, cfg.duration_s
    )

    result = simulate_trajectory(
        trajectory_id=trajectory_id,
        aircraft=aircraft,
        control_profile=profile,
        V0=V0,
        gamma0=0.0,
        alpha0=alpha_trim,
        h0=h0,
        q0=0.0,
        duration_s=cfg.duration_s,
        dt=cfg.dt,
        v_floor=v_floor,
        gamma_max_rad=gamma_max_rad,
    )

    features = compute_features_for_trajectory(result, boundary, cfg.dt)
    labels, label_available = compute_future_stall_label(features["is_unsafe"], cfg.dt, cfg.labeling_horizon_s)

    sanity_issues = sanity_check_trajectory(result)

    raw_frame = pd.DataFrame({
        "trajectory_id": result.trajectory_id,
        "time": result.t,
        "V": result.V,
        "alpha": result.alpha,
        "theta": result.theta,
        "gamma": result.gamma,
        "altitude": result.altitude,
        "pitch_rate": result.pitch_rate,
        "vertical_speed": result.vertical_speed,
        "thrust": result.thrust,
        "elevator": result.elevator,
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
        "trajectory_id": trajectory_id,
        "generation_mode": regime,
        "random_seed": cfg.seed,
        "initial_airspeed": V0,
        "initial_altitude": h0,
        "initial_alpha": alpha_trim,
        "trim_throttle": throttle_trim,
        "trim_elevator": elevator_trim,
        "maximum_alpha": float(np.max(result.alpha)) if len(result.alpha) else np.nan,
        "minimum_alpha": float(np.min(result.alpha)) if len(result.alpha) else np.nan,
        "minimum_airspeed": float(np.min(result.V)) if len(result.V) else np.nan,
        "maximum_airspeed": float(np.max(result.V)) if len(result.V) else np.nan,
        "maximum_abs_gamma": float(np.max(np.abs(result.gamma))) if len(result.gamma) else np.nan,
        "whether_stall_occurred": stall_occurred,
        "time_of_first_stall": time_of_first_stall,
        "whether_validity_envelope_was_exceeded": result.validity_envelope_exceeded,
        "termination_reason": result.termination_reason,
        "n_steps": len(result.t),
        "duration_actual_s": float(result.t[-1]) if len(result.t) else 0.0,
        "n_sanity_issues": len(sanity_issues),
        "sanity_issues": ";".join(sanity_issues) if sanity_issues else "",
    }

    return TrajectoryOutput(raw_frame=raw_frame, processed_frame=processed_frame, metadata_row=metadata_row)


def build_dataset(cfg: GenerationConfig, verbose: bool = True, regime_control_configs: dict = None):
    """Generate the full dataset. Returns (raw_df, processed_df, metadata_df, v0_check).

    regime_control_configs: optional override, defaults to the v0.1
    REGIME_CONTROL_CONFIGS (see generate_one_trajectory). cfg's own
    regime_proportions keys must match this mapping's keys.
    """
    aircraft = Aircraft()

    v0_check = validate_v0_range(aircraft, cfg)
    if not v0_check["v0_min_above_vstall"]:
        raise ValueError(
            f"Requested v0_min={cfg.v0_min} is not above the aircraft's stall speed "
            f"({v0_check['v_stall_m_s']:.2f} m/s) -- trim would be unsolvable for some "
            f"sampled V0. Adjust GenerationConfig.v0_min before generating."
        )

    boundary = resolve_stall_boundary(aircraft)
    v_stall, v_floor, gamma_max_rad = compute_validity_envelope(aircraft, cfg)

    master_rng = np.random.default_rng(cfg.seed)
    regimes = assign_regimes(master_rng, cfg.n_trajectories, cfg.regime_proportions)

    raw_frames = []
    processed_frames = []
    metadata_rows = []

    t_start = time.time()
    for i, regime in enumerate(regimes):
        out = generate_one_trajectory(i, regime, master_rng, aircraft, cfg, boundary, v_floor, gamma_max_rad, regime_control_configs=regime_control_configs)
        raw_frames.append(out.raw_frame)
        processed_frames.append(out.processed_frame)
        metadata_rows.append(out.metadata_row)

        if verbose and (i + 1) % 100 == 0:
            elapsed = time.time() - t_start
            print(f"  generated {i + 1}/{cfg.n_trajectories} trajectories ({elapsed:.1f}s elapsed)")

    raw_df = pd.concat(raw_frames, ignore_index=True)
    processed_df = pd.concat(processed_frames, ignore_index=True)
    metadata_df = pd.DataFrame(metadata_rows)

    if verbose:
        print(f"Done: {cfg.n_trajectories} trajectories in {time.time() - t_start:.1f}s")

    return raw_df, processed_df, metadata_df, v0_check
