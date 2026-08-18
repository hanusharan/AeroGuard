"""Candidate D v2 — ONE narrowly-scoped sequencing fix (reconciliation
follow-up, §7 of outputs/v03_calibration/reconciliation_report.md).

Does NOT modify aeroguard_dataset/config.py (GRADUAL_D_TWO_STAGE's elevator
ControlRangeSpec -- magnitude 0.05-0.09 rad, rise 1.5-3.0s, hold 0.5-2.0s,
fall 0.5-1.5s -- is imported, not redefined) or
aeroguard_dataset/control_profiles.py (Pulse/ControlProfile dataclasses and
the general-purpose sample_pulses()/build_control_profile() used by
v0.1/v0.2 and every other regime are untouched and still used elsewhere).
Does NOT touch aeroguard/ physics. Additive only.

DIAGNOSED MECHANISM (reconciliation report, Task 4): the general-purpose
sample_pulses() draws an INDEPENDENT random sign for every pulse. For a
two-pulse "two-stage approach" candidate, this means pulse 2 can fire with
the OPPOSITE sign from pulse 1 -- observed directly in traj_0013 (pulse 1
negative -> alpha dives to -0.3 deg, gamma to -26 deg; pulse 2 positive ->
alpha recovers and overshoots into a 42 deg zoom-climb before finally
crossing 8s later). sample_pulses() also inserts an unconditional
rng.uniform(0.3, 1.5)s idle gap between pulses regardless of where alpha
is, giving alpha room to relax back toward trim between pulses even when
signs happen to agree.

THE FIX (smallest additive change that removes exactly this mechanism,
without a feedback controller or any runtime state-awareness -- it only
changes how the two pulses are SEQUENCED/SIGNED at generation time, same
as any other control-profile parameter):
  1. Both pulses share ONE randomly-drawn sign (drawn once, applied to
     both), instead of one independent sign draw per pulse. This
     structurally rules out the sign-reversal dive/recovery mechanism --
     pulse 2 can never pull alpha back through zero and out the other
     side.
  2. The idle gap between pulse 1's fall and pulse 2's start is removed
     (pulse 2 starts exactly when pulse 1's fall phase ends), instead of
     the unconstrained 0.3-1.5s gap. Since pulse 1 (same sign, same
     magnitude range) is chosen so its hold phase already sits alpha near
     the approach region by construction of GRADUAL_D_TWO_STAGE's
     magnitude range, starting pulse 2 immediately (rather than after an
     idle window) keeps pulse 2's rise beginning from wherever pulse 1's
     fall leaves alpha, instead of after it has had time to relax back
     toward trim -- this is the generation-time proxy for "pulse 2
     activates only once alpha is at/above the approach region," achieved
     without observing alpha at runtime.

Magnitude/rise/hold/fall ranges per pulse and pulse count (2) are
unchanged from GRADUAL_D_TWO_STAGE -- only the sign-coupling and the
inter-pulse gap differ.
"""
from typing import List

import numpy as np

from aeroguard.dynamics import Controls
from aeroguard_dataset.config import ControlRangeSpec, GRADUAL_D_TWO_STAGE
from aeroguard_dataset.control_profiles import ControlProfile, Pulse

CANDIDATE_D_V2_ELEVATOR_SPEC: ControlRangeSpec = GRADUAL_D_TWO_STAGE.elevator


def sample_same_sign_sequential_pulses(rng: np.random.Generator, spec: ControlRangeSpec, duration_s: float) -> List[Pulse]:
    """Two pulses, one shared sign, zero idle gap between them (see module
    docstring for why). Falls back to fewer pulses only if duration_s is
    too short to fit both, mirroring sample_pulses()'s own fallback
    behavior."""
    pulses: List[Pulse] = []
    t_cursor = float(rng.uniform(0.5, max(0.6, duration_s * 0.3)))
    sign = float(rng.choice([-1.0, 1.0]))
    for _ in range(2):
        if t_cursor >= duration_s - 0.5:
            break
        rise = float(rng.uniform(spec.rise_s_min, spec.rise_s_max))
        hold = float(rng.uniform(spec.hold_s_min, spec.hold_s_max))
        fall = float(rng.uniform(spec.fall_s_min, spec.fall_s_max))
        mag_abs = float(rng.uniform(spec.magnitude_min, spec.magnitude_max))
        pulses.append(Pulse(start=t_cursor, rise=rise, hold=hold, fall=fall, magnitude=sign * mag_abs))
        t_cursor = t_cursor + rise + hold + fall  # zero gap: next pulse starts exactly as this one's fall ends
    return pulses


def build_candidate_d_v2_profile(
    rng: np.random.Generator, alpha_trim: float, throttle_trim: float, elevator_trim: float, duration_s: float
) -> ControlProfile:
    """Elevator-only (throttle inert, matching GRADUAL_D_TWO_STAGE)."""
    elevator_pulses = sample_same_sign_sequential_pulses(rng, CANDIDATE_D_V2_ELEVATOR_SPEC, duration_s)
    return ControlProfile(
        elevator_trim=elevator_trim, throttle_trim=throttle_trim,
        elevator_pulses=elevator_pulses, throttle_pulses=[],
    )
