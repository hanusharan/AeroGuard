"""All Stage 2 generation parameters, in one documented place.

Every numeric range used anywhere in the dataset-generation pipeline is
defined here, not scattered through the codebase, so the dataset is
fully described and reproducible from this one file plus the seed.
"""

from dataclasses import dataclass, field
from typing import Dict

from .paths import cl_max_of, stall_speed
from aeroguard.aircraft import Aircraft


@dataclass(frozen=True)
class ControlRangeSpec:
    """Bounds for one control channel's smooth perturbation pulses, for
    one generation regime. All magnitudes are added ON TOP of the trim
    value (see control_profiles.py), never replacing it.
    """

    magnitude_min: float
    magnitude_max: float
    rise_s_min: float
    rise_s_max: float
    hold_s_min: float
    hold_s_max: float
    fall_s_min: float
    fall_s_max: float


@dataclass(frozen=True)
class RegimeControlConfig:
    """Full control-perturbation spec for one regime (normal/boundary/stall).

    n_pulses_choices: possible pulse counts per active channel, sampled
        uniformly (e.g. (1, 2) means each active channel gets either 1
        or 2 pulses, chosen with equal probability).
    both_channels_prob: probability that BOTH elevator and throttle are
        perturbed in the same trajectory (vs. just one of them).
    elevator_prob_if_single: if only one channel is perturbed, the
        probability that it is the elevator (vs. throttle).
    """

    elevator: ControlRangeSpec
    throttle: ControlRangeSpec
    n_pulses_choices: tuple
    both_channels_prob: float
    elevator_prob_if_single: float


@dataclass(frozen=True)
class GenerationConfig:
    """Top-level configuration for the Stage 2 initial 1000-trajectory dataset."""

    # --- reproducibility -----------------------------------------------
    seed: int = 20260817
    dataset_version: str = "stage2-initial-1000-v1"

    # --- scale -----------------------------------------------------------
    n_trajectories: int = 1000

    # --- simulation ------------------------------------------------------
    # dt matches the existing simulation timestep used throughout the
    # project (scripts/simulate.py, scripts/validate_physics.py).
    dt: float = 0.01
    duration_s: float = 20.0

    # --- initial conditions ------------------------------------------------
    # Requested range is V0 in [30, 75] m/s. This is checked against the
    # aircraft's own stall speed at generation time (see
    # validate_v0_range below) rather than assumed valid.
    v0_min: float = 30.0
    v0_max: float = 75.0
    altitude_min: float = 500.0
    altitude_max: float = 2000.0

    # --- validity envelope (Stage 1 physics-validation findings) -----------
    # Stage 1 found the model becomes questionable below roughly
    # 0.5-0.7 * V_stall and beyond |gamma| ~ 45 deg. We enforce the more
    # permissive (lower) end of that speed range, 0.5*V_stall, as the
    # hard floor: the validated Stage-1 demo trajectory legitimately
    # dipped to ~52% of V_stall during an ordinary zoom-climb (not a
    # numerical breakdown), so a tighter 0.7*V_stall floor would
    # truncate physically fine boundary/stall-producing maneuvers that
    # are exactly what this dataset needs to capture. The gamma cap is
    # used as given (~45 deg).
    validity_v_floor_fraction_of_vstall: float = 0.5
    validity_gamma_max_deg: float = 45.0

    # --- labeling ------------------------------------------------------------
    labeling_horizon_s: float = 5.0

    # --- regime target proportions (Section 6) --------------------------------
    regime_proportions: Dict[str, float] = field(
        default_factory=lambda: {"normal": 0.50, "boundary": 0.25, "stall": 0.25}
    )


# ---------------------------------------------------------------------------
# Per-regime control-perturbation ranges (Section 5/7).
#
# Magnitudes started from the validated Stage-1 trim behaviour (a 0.02 rad
# elevator pulse from trim produced a ~2 deg alpha excursion; a 0.15 rad
# pulse produced a ~24 deg excursion, well past the ~16 deg stall
# boundary) and were then empirically calibrated with pilot batches (60-80
# trial trajectories per regime, several RNG seeds, run outside the final
# generation seed) measuring the fraction of trajectories crossing the
# actual CL(alpha)-peak stall boundary:
#   normal   : ~0% crossed,  mean max|alpha| ~4 deg   (comfortably safe)
#   boundary : ~30% crossed, mean max|alpha| ~15-18 deg (mixed: some
#              stay well under the ~16 deg boundary, some cross it --
#              this is the intended "some may cross, some may not")
#   stall    : ~75-78% crossed (consistent across seeds 7/123/999),
#              mean max|alpha| ~38-40 deg (reliably, but not
#              deterministically, produces post-stall excursions)
# These are properties of the calibration batches, not the final 1000-
# trajectory dataset -- the actual achieved proportions for the real
# dataset are computed and reported by the audit step (Section 16).
# ---------------------------------------------------------------------------

NORMAL_CONTROL_CONFIG = RegimeControlConfig(
    elevator=ControlRangeSpec(
        magnitude_min=0.01, magnitude_max=0.04,  # rad, ~0.6-2.3 deg
        rise_s_min=0.5, rise_s_max=2.0,
        hold_s_min=0.2, hold_s_max=1.5,
        fall_s_min=0.5, fall_s_max=2.0,
    ),
    throttle=ControlRangeSpec(
        magnitude_min=0.03, magnitude_max=0.10,  # throttle units, [0,1] scale
        rise_s_min=0.5, rise_s_max=2.5,
        hold_s_min=0.5, hold_s_max=2.0,
        fall_s_min=0.5, fall_s_max=2.5,
    ),
    n_pulses_choices=(1, 2),
    both_channels_prob=0.3,
    elevator_prob_if_single=0.5,
)

BOUNDARY_CONTROL_CONFIG = RegimeControlConfig(
    elevator=ControlRangeSpec(
        magnitude_min=0.07, magnitude_max=0.14,  # rad, ~4.0-8.0 deg
        rise_s_min=0.3, rise_s_max=1.5,
        hold_s_min=0.8, hold_s_max=3.5,
        fall_s_min=0.5, fall_s_max=2.5,
    ),
    throttle=ControlRangeSpec(
        magnitude_min=0.05, magnitude_max=0.15,
        rise_s_min=0.3, rise_s_max=2.0,
        hold_s_min=0.5, hold_s_max=2.5,
        fall_s_min=0.5, fall_s_max=2.0,
    ),
    n_pulses_choices=(1, 2),
    both_channels_prob=0.4,
    elevator_prob_if_single=0.7,
)

STALL_CONTROL_CONFIG = RegimeControlConfig(
    elevator=ControlRangeSpec(
        magnitude_min=0.19, magnitude_max=0.32,  # rad, ~10.9-18.3 deg
        rise_s_min=0.2, rise_s_max=1.0,
        hold_s_min=2.0, hold_s_max=5.0,
        fall_s_min=0.3, fall_s_max=1.5,
    ),
    throttle=ControlRangeSpec(
        magnitude_min=0.05, magnitude_max=0.20,
        rise_s_min=0.2, rise_s_max=1.5,
        hold_s_min=0.5, hold_s_max=3.0,
        fall_s_min=0.3, fall_s_max=1.5,
    ),
    n_pulses_choices=(1, 2),
    both_channels_prob=0.4,
    elevator_prob_if_single=0.85,
)

REGIME_CONTROL_CONFIGS = {
    "normal": NORMAL_CONTROL_CONFIG,
    "boundary": BOUNDARY_CONTROL_CONFIG,
    "stall": STALL_CONTROL_CONFIG,
}


# ---------------------------------------------------------------------------
# v0.2 near_boundary regime (dataset-generation refinement, physics unchanged).
#
# ROOT CAUSE (found by tracing an actual v0.1 STALL trajectory,
# traj_0002, in the generated dataset): its elevator pulse rose to
# ~0.28 rad by t=3.5s and then STAYED at that magnitude (the hold
# phase) through at least t=6.0s -- 2.5+ seconds AFTER alpha had
# already crossed the ~16 deg boundary at t=3.73s. alpha kept climbing
# the entire time the elevator was held (8.6 -> 26.3 -> 44.7 -> 53.6 ->
# 56.9 deg from t=3.5 to t=6.0), because the pulse is open-loop and
# time-based -- it has no awareness that the boundary was already
# crossed, so it keeps commanding a large deflection well past the
# point where a "clean crossing" data point would have been most
# useful. BOUNDARY_CONTROL_CONFIG's hold (0.8-3.5s) has the same
# mechanism, just less extreme, which is why it also both under-covers
# the 8-16 deg transition zone (bimodal: mostly mild, occasionally
# extreme) and contributes materially to the 319/1000 gamma-envelope
# terminations observed in Dataset v0.1.
#
# FIX: near_boundary uses a much SHORTER pulse -- fast rise (0.4-1.0s),
# short-or-no hold (0-0.4s), and a fast-but-not-instant fall
# (0.6-1.6s), so the elevator releases and the restoring dynamics
# (alpha_stiffness, pitch damping -- unchanged aeroguard/ physics) get
# a chance to act shortly after any crossing, instead of continuing to
# pump energy in for several more seconds.
#
# CALIBRATED (100-200 trial trajectories per candidate, several RNG
# seeds distinct from the generation seed, using the real
# simulate_trajectory() with validity-envelope enforcement -- see
# Stage 2 v0.2 report for the full candidate comparison table). Final
# choice (magnitude 0.12-0.20 rad, rise 0.4-1.0s, hold 0-0.4s, fall
# 0.6-1.6s) achieved, consistently across 4 seeds: ~11-17% of
# trajectories crossing the boundary, only ~2-7% terminating on the
# gamma envelope (vs. a much higher share of BOUNDARY/STALL
# trajectories in v0.1), and 38-50% of trajectories spending >0.5s
# with alpha in the 8-16 deg transition zone.
# ---------------------------------------------------------------------------

NEAR_BOUNDARY_CONTROL_CONFIG = RegimeControlConfig(
    elevator=ControlRangeSpec(
        magnitude_min=0.12, magnitude_max=0.20,  # rad, ~6.9-11.5 deg
        rise_s_min=0.4, rise_s_max=1.0,
        hold_s_min=0.0, hold_s_max=0.4,
        fall_s_min=0.6, fall_s_max=1.6,
    ),
    throttle=ControlRangeSpec(
        magnitude_min=0.03, magnitude_max=0.10,
        rise_s_min=0.3, rise_s_max=2.0,
        hold_s_min=0.3, hold_s_max=1.5,
        fall_s_min=0.5, fall_s_max=2.0,
    ),
    n_pulses_choices=(1,),  # a single clean approach per trajectory (rise=approach, fall=partial recovery)
    both_channels_prob=0.2,
    elevator_prob_if_single=0.85,
)

# v0.2 regime mix: STALL is left byte-for-byte identical to v0.1
# (preserves genuinely aggressive/departure/recovery examples at the
# same 25% share). NORMAL is also unchanged. Only "boundary" is
# replaced by the recalibrated "near_boundary" regime, at the same 25%
# share -- BOUNDARY_CONTROL_CONFIG itself is left in this file
# (unused by V2) purely for side-by-side reference/comparison.
REGIME_CONTROL_CONFIGS_V2 = {
    "normal": NORMAL_CONTROL_CONFIG,
    "near_boundary": NEAR_BOUNDARY_CONTROL_CONFIG,
    "stall": STALL_CONTROL_CONFIG,
}


# ---------------------------------------------------------------------------
# v0.3 CANDIDATE regimes (precursor-diagnosis stage, NOT yet a dataset).
#
# Root cause (see outputs/precursor_diagnosis/precursor_diagnosis_report.md,
# Phase 2): alpha's equilibrium under this pitch model is set almost entirely
# by elevator deflection (alpha_eq ~= 3.2 * delta_e, independent of V/throttle
# -- verified empirically: a full throttle cut for 19s moved alpha < 0.5 deg).
# NEAR_BOUNDARY_CONTROL_CONFIG and STALL_CONTROL_CONFIG both use SHORT-rise
# pulses (0.2-1.0s) whose magnitude implies an equilibrium alpha far past the
# ~16 deg boundary (22-68 deg) -- because the pitch response's rate is
# proportional to distance-from-equilibrium, aiming far past the boundary
# makes the boundary get crossed during the FASTEST part of the response
# (measured median 8->16deg transition: 0.37s), not a slow tail.
#
# These candidates instead use a much SLOWER elevator rise (2-5s, vs 0.2-1.0s)
# with magnitude tuned so the implied equilibrium sits only modestly past the
# boundary. This makes the forcing timescale (elevator rise) dominate over the
# aircraft's natural ~0.4-0.5s short-period response, so alpha quasi-statically
# tracks the elevator ramp instead of snapping toward a distant target --
# directly verified in Phase 2 (rise=4.0s, magnitude=0.11 rad produced a smooth
# 4deg->15.5deg climb over ~4.6s through the unmodified physics engine).
#
# Only elevator is perturbed (both_channels_prob=0.0) since throttle does not
# move alpha in this model -- keeping the mechanism isolated to what actually
# works. NORMAL_CONTROL_CONFIG and STALL_CONTROL_CONFIG are unchanged; these
# candidates are only ever used standalone in scripts/calibrate_v3.py, never
# substituted into REGIME_CONTROL_CONFIGS_V2 (v0.2 stays exactly as generated).
# ---------------------------------------------------------------------------

_PLACEHOLDER_THROTTLE_SPEC = ControlRangeSpec(
    magnitude_min=0.0, magnitude_max=0.0,
    rise_s_min=0.5, rise_s_max=1.0, hold_s_min=0.0, hold_s_max=0.5, fall_s_min=0.5, fall_s_max=1.0,
)

GRADUAL_A_TIGHT_MARGIN = RegimeControlConfig(
    elevator=ControlRangeSpec(
        magnitude_min=0.07, magnitude_max=0.10,  # rad; implied alpha_eq ~= 22.4-32.0 deg
        rise_s_min=3.0, rise_s_max=4.5,
        hold_s_min=0.5, hold_s_max=2.0,
        fall_s_min=1.0, fall_s_max=2.0,
    ),
    throttle=_PLACEHOLDER_THROTTLE_SPEC,
    n_pulses_choices=(1,),
    both_channels_prob=0.0,
    elevator_prob_if_single=1.0,
)

GRADUAL_B_MODERATE_MARGIN = RegimeControlConfig(
    elevator=ControlRangeSpec(
        magnitude_min=0.10, magnitude_max=0.13,  # rad; implied alpha_eq ~= 32.0-41.6 deg
        rise_s_min=2.5, rise_s_max=4.0,
        hold_s_min=0.5, hold_s_max=2.0,
        fall_s_min=0.8, fall_s_max=1.8,
    ),
    throttle=_PLACEHOLDER_THROTTLE_SPEC,
    n_pulses_choices=(1,),
    both_channels_prob=0.0,
    elevator_prob_if_single=1.0,
)

GRADUAL_C_HIGH_MARGIN = RegimeControlConfig(
    elevator=ControlRangeSpec(
        magnitude_min=0.13, magnitude_max=0.17,  # rad; implied alpha_eq ~= 41.6-54.4 deg
        rise_s_min=2.0, rise_s_max=3.5,
        hold_s_min=0.5, hold_s_max=1.5,
        fall_s_min=0.6, fall_s_max=1.5,
    ),
    throttle=_PLACEHOLDER_THROTTLE_SPEC,
    n_pulses_choices=(1,),
    both_channels_prob=0.0,
    elevator_prob_if_single=1.0,
)

GRADUAL_D_TWO_STAGE = RegimeControlConfig(
    elevator=ControlRangeSpec(
        magnitude_min=0.05, magnitude_max=0.09,  # rad; two sequential pulses in this range
        rise_s_min=1.5, rise_s_max=3.0,
        hold_s_min=0.5, hold_s_max=2.0,
        fall_s_min=0.5, fall_s_max=1.5,
    ),
    throttle=_PLACEHOLDER_THROTTLE_SPEC,
    n_pulses_choices=(2,),  # first pulse establishes a plateau near/below boundary; second pushes further
    both_channels_prob=0.0,
    elevator_prob_if_single=1.0,
)

GRADUAL_E_SLOW_RISE_SLOW_RECOVERY = RegimeControlConfig(
    elevator=ControlRangeSpec(
        magnitude_min=0.10, magnitude_max=0.14,  # rad; implied alpha_eq ~= 32.0-44.8 deg
        rise_s_min=3.0, rise_s_max=5.0,
        hold_s_min=0.0, hold_s_max=0.5,  # minimal hold: crossing (if any) happens mid-ramp/near peak
        fall_s_min=1.5, fall_s_max=3.0,  # slow-ish recovery too, for cleaner post-crossing recovery examples
    ),
    throttle=_PLACEHOLDER_THROTTLE_SPEC,
    n_pulses_choices=(1,),
    both_channels_prob=0.0,
    elevator_prob_if_single=1.0,
)

GRADUAL_APPROACH_CANDIDATES = {
    "gradual_A_tight_margin": GRADUAL_A_TIGHT_MARGIN,
    "gradual_B_moderate_margin": GRADUAL_B_MODERATE_MARGIN,
    "gradual_C_high_margin": GRADUAL_C_HIGH_MARGIN,
    "gradual_D_two_stage": GRADUAL_D_TWO_STAGE,
    "gradual_E_slow_rise_slow_recovery": GRADUAL_E_SLOW_RISE_SLOW_RECOVERY,
}


def make_v03_calibration_config(n_trajectories: int, seed: int = 20260817) -> GenerationConfig:
    """Small CALIBRATION-ONLY config (Phase 4): splits n_trajectories evenly
    across the 5 GRADUAL_APPROACH_CANDIDATES regimes. Not a dataset version --
    used only by scripts/calibrate_v3.py, never written to data/."""
    import dataclasses

    n_candidates = len(GRADUAL_APPROACH_CANDIDATES)
    share = 1.0 / n_candidates
    return dataclasses.replace(
        GenerationConfig(),
        seed=seed,
        n_trajectories=n_trajectories,
        dataset_version="stage2-v0.3-calibration",
        regime_proportions={name: share for name in GRADUAL_APPROACH_CANDIDATES},
    )


def make_generation_config_v2(n_trajectories: int, seed: int = 20260817) -> GenerationConfig:
    """v0.2 top-level config: identical to v0.1's GenerationConfig defaults
    (same seed, same V0/altitude ranges, same validity envelope, same
    labeling horizon -- none of that is what v0.2 changes) except the
    regime_proportions keys, which must match REGIME_CONTROL_CONFIGS_V2
    ("near_boundary" instead of "boundary"), and n_trajectories/dataset_version.
    """
    import dataclasses

    return dataclasses.replace(
        GenerationConfig(),
        seed=seed,
        n_trajectories=n_trajectories,
        dataset_version="stage2-v0.2-calibration",
        regime_proportions={"normal": 0.50, "near_boundary": 0.25, "stall": 0.25},
    )


def compute_validity_envelope(aircraft: Aircraft, cfg: GenerationConfig):
    """Resolve the documented validity envelope into concrete numbers for
    this aircraft, using the actual physics model (not hardcoded values).

    Returns (v_stall, v_floor, gamma_max_rad).
    """
    import numpy as np

    cl_max, _alpha_at_peak = cl_max_of(aircraft)
    v_stall = stall_speed(aircraft, cl_max)
    v_floor = cfg.validity_v_floor_fraction_of_vstall * v_stall
    gamma_max_rad = np.radians(cfg.validity_gamma_max_deg)
    return v_stall, v_floor, gamma_max_rad


def validate_v0_range(aircraft: Aircraft, cfg: GenerationConfig) -> dict:
    """Check the requested V0 sampling range against the aircraft's own
    stall speed, rather than assuming it is valid (Section 4 requirement).

    Returns a dict summary suitable for logging into the generation config
    saved to disk.
    """
    v_stall, v_floor, _ = compute_validity_envelope(aircraft, cfg)
    return {
        "v_stall_m_s": v_stall,
        "v_floor_m_s": v_floor,
        "requested_v0_min": cfg.v0_min,
        "requested_v0_max": cfg.v0_max,
        "v0_min_margin_over_vstall": cfg.v0_min / v_stall,
        "v0_max_margin_over_vstall": cfg.v0_max / v_stall,
        "v0_min_above_vstall": cfg.v0_min > v_stall,
        "v0_min_above_v_floor": cfg.v0_min > v_floor,
    }
