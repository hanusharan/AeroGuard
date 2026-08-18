"""v0.3 CANDIDATE control profiles for the precursor-signal calibration
experiment (Phase 3/4 of the precursor diagnosis task). NOT part of the
validated v0.1/v0.2 dataset generation path -- REGIME_CONTROL_CONFIGS_V2
in config.py is untouched, and nothing here is imported by
scripts/generate_dataset*.py.

Rationale (see outputs/precursor_diagnosis/ for the full evidence):

Phase 1/2 findings on v0.2 traced real trajectories and found that in both
the `near_boundary` and `stall` regimes, alpha/elevator/pitch_rate are
essentially FLAT from 5s to ~1s before crossing, then rise sharply in the
final <1s (near_boundary median alpha 8deg->crossing = 0.54s; stall =
0.33s). The elevator pulse's own RISE TIME (0.4-1.0s for near_boundary,
0.2-1.0s for stall) is comparable to or shorter than this transit time --
the pulse's rise phase alone accounts for almost the entire approach, so
there is no extended quasi-steady approach phase for a classifier to pick
up on multiple seconds out.

Additionally, the `stall` regime's long hold (2.0-5.0s) drives ~3.5s
median of near-peak elevator AFTER crossing (deep post-stall, frequently
tripping the 45deg gamma envelope: 105/161 stall-regime crossings, plus a
further 56/250 stall-regime trajectories that hit the gamma envelope
WITHOUT ever crossing alpha_stall at all -- 22% of the entire stall
regime allocation produces no usable stall example either way).

Hypothesis to test: lengthening the elevator pulse's RISE time (to
2.5-7s, well beyond the observed <1s natural transit time) while keeping
magnitude in a broadly similar range to NEAR_BOUNDARY_CONTROL_CONFIG,
and keeping hold/fall short (as near_boundary already does, to avoid deep
post-stall), should stretch the alpha approach out to a genuine multi-
second precursor window -- IF the aircraft's alpha response tracks the
slow ramp quasi-statically (plausible given alpha_stiffness provides a
restoring moment) rather than being rate-independent.

Five candidates spanning magnitude x rise-time x hold-time, to be
calibrated empirically (Phase 4) rather than assumed:
  v03_a: gentle_long_rise            -- baseline hypothesis
  v03_b: gentle_longer_rise_lower_mag -- slower rise, lower magnitude
  v03_c: moderate_rise_higher_mag     -- shorter rise, higher magnitude (control)
  v03_d: very_gentle_rise             -- most extreme rise stretch
  v03_e: gentle_rise_short_hold       -- same rise as (a), near-zero hold
         (isolates rise-time effect from hold-time effect)

Throttle channel, pulse count, and channel-selection probabilities are
left identical to NEAR_BOUNDARY_CONTROL_CONFIG (config.py) throughout --
only the elevator ControlRangeSpec differs between candidates, per the
task's "prefer modifying only control-profile parameters" instruction.
"""

from aeroguard_dataset.config import ControlRangeSpec, RegimeControlConfig

_NEAR_BOUNDARY_THROTTLE = ControlRangeSpec(
    magnitude_min=0.03, magnitude_max=0.10,
    rise_s_min=0.3, rise_s_max=2.0,
    hold_s_min=0.3, hold_s_max=1.5,
    fall_s_min=0.5, fall_s_max=2.0,
)

_COMMON = dict(n_pulses_choices=(1,), both_channels_prob=0.2, elevator_prob_if_single=0.85)

V03_A_GENTLE_LONG_RISE = RegimeControlConfig(
    elevator=ControlRangeSpec(
        magnitude_min=0.14, magnitude_max=0.20,
        rise_s_min=3.0, rise_s_max=5.0,
        hold_s_min=1.0, hold_s_max=3.0,
        fall_s_min=1.0, fall_s_max=2.0,
    ),
    throttle=_NEAR_BOUNDARY_THROTTLE,
    **_COMMON,
)

V03_B_GENTLE_LONGER_RISE_LOWER_MAG = RegimeControlConfig(
    elevator=ControlRangeSpec(
        magnitude_min=0.12, magnitude_max=0.17,
        rise_s_min=4.0, rise_s_max=6.0,
        hold_s_min=1.0, hold_s_max=2.5,
        fall_s_min=1.0, fall_s_max=2.0,
    ),
    throttle=_NEAR_BOUNDARY_THROTTLE,
    **_COMMON,
)

V03_C_MODERATE_RISE_HIGHER_MAG = RegimeControlConfig(
    elevator=ControlRangeSpec(
        magnitude_min=0.16, magnitude_max=0.24,
        rise_s_min=2.0, rise_s_max=3.5,
        hold_s_min=1.0, hold_s_max=2.5,
        fall_s_min=1.0, fall_s_max=2.0,
    ),
    throttle=_NEAR_BOUNDARY_THROTTLE,
    **_COMMON,
)

V03_D_VERY_GENTLE_RISE = RegimeControlConfig(
    elevator=ControlRangeSpec(
        magnitude_min=0.15, magnitude_max=0.22,
        rise_s_min=5.0, rise_s_max=7.0,
        hold_s_min=0.5, hold_s_max=2.0,
        fall_s_min=1.5, fall_s_max=2.5,
    ),
    throttle=_NEAR_BOUNDARY_THROTTLE,
    **_COMMON,
)

V03_E_GENTLE_RISE_SHORT_HOLD = RegimeControlConfig(
    elevator=ControlRangeSpec(
        magnitude_min=0.16, magnitude_max=0.23,
        rise_s_min=3.0, rise_s_max=5.0,
        hold_s_min=0.0, hold_s_max=0.5,
        fall_s_min=1.0, fall_s_max=2.0,
    ),
    throttle=_NEAR_BOUNDARY_THROTTLE,
    **_COMMON,
)

V03_CANDIDATES = {
    "v03_a_gentle_long_rise": V03_A_GENTLE_LONG_RISE,
    "v03_b_gentle_longer_rise_lower_mag": V03_B_GENTLE_LONGER_RISE_LOWER_MAG,
    "v03_c_moderate_rise_higher_mag": V03_C_MODERATE_RISE_HIGHER_MAG,
    "v03_d_very_gentle_rise": V03_D_VERY_GENTLE_RISE,
    "v03_e_gentle_rise_short_hold": V03_E_GENTLE_RISE_SHORT_HOLD,
}
