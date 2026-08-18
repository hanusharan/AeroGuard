"""Candidate D v3 — ONE additional narrowly-scoped fix on top of v2
(outputs/v03_calibration/candidate_d_followup_report.md, CASE B).

Does NOT modify control_profiles_candidate_d_v2.py, config.py,
control_profiles.py, or aeroguard/ physics. v2's same-sign / zero-gap
sequencing fix (which eliminated dive-then-zoom-climb crossings) is
reused unchanged via sample_same_sign_sequential_pulses(); this module
only adds a cap on top of its output.

DIAGNOSED MECHANISM (v2 follow-up report, §7-8): forcing both pulses to
the same sign removed the "lucky cancellation" that let borderline
non-crossing trajectories settle back to safety, so 73.3% of v2's
135 non-crossing trajectories ran away into the 45deg gamma envelope
instead. Checked directly against v2's own data (candidate_d_v2_metadata.csv):
gamma-terminated non-crossers reach only modest peak alpha (mean 4.2deg,
max 12.2deg) -- nowhere near the 16.07deg boundary -- but sustain it for a
long time (mean trajectory duration 9.5s, up to 14.4s, before hitting the
envelope), while completed_normally non-crossers (which run the full 20s
safely) have HIGHER peak alpha (mean 8.9deg) but reach it only briefly.
This confirms the mechanism is sustained TIME at elevated alpha (mostly
the pulses' hold phases), not peak magnitude -- gamma accumulates with
exposure duration, not amplitude.

THE FIX: cap the TOTAL combined active duration of the two pulses
(rise+hold+fall summed across both), trimming HOLD time first (since
hold is what sustains elevated alpha/gamma-accumulation; rise/fall shape
the transition and are left alone) down to a floor of 0 before ever
touching rise/fall, so most of the two-stage approach's rise-time
character (the part that produced the 90% clean-gradual-crossing rate in
v2) survives untouched. Sign and zero-gap sequencing from v2 are
unchanged. This is a purely generation-time (open-loop, deterministic)
computation on the already-sampled pulses -- no runtime feedback, no
physics change.

Cap value: 7.0s total (rise+hold+fall for pulse 1 + pulse 2 combined).
Chosen from v2's own data: non-crossers that blew the envelope needed a
mean ~9.5s of sustained exposure to do so (min 4.9s at the low end), while
v2's clean gradual CROSSINGS mostly resolved by ~6.2s (max observed
alpha8->cross among clean crossings was 6.23s) -- 7.0s sits just above
the crossing-relevant range and comfortably below the runaway range,
giving crossings room to complete while denying non-crossers the
sustained exposure that drove their gamma blowouts.
"""
from typing import List

import numpy as np

from aeroguard.dynamics import Controls
from aeroguard_dataset.config import ControlRangeSpec
from aeroguard_dataset.control_profiles import ControlProfile, Pulse
from aeroguard_dataset.control_profiles_candidate_d_v2 import (
    CANDIDATE_D_V2_ELEVATOR_SPEC,
    sample_same_sign_sequential_pulses,
)

TOTAL_DURATION_CAP_S = 7.0


def cap_total_pulse_duration(pulses: List[Pulse], cap_s: float = TOTAL_DURATION_CAP_S) -> List[Pulse]:
    """Trim hold time (first pulse 2's, then pulse 1's, down to a floor of
    0) until the combined rise+hold+fall of all pulses is <= cap_s. Rise
    and fall are never touched. Pulse starts are recomputed so pulse 2
    still begins exactly when pulse 1's (possibly now-shorter) fall ends
    -- v2's zero-gap invariant is preserved."""
    if len(pulses) < 2:
        return pulses

    p1, p2 = pulses[0], pulses[1]
    total = (p1.rise + p1.hold + p1.fall) + (p2.rise + p2.hold + p2.fall)
    excess = total - cap_s
    if excess <= 0:
        return pulses

    # trim pulse 2's hold first
    trim2 = min(p2.hold, excess)
    p2 = Pulse(start=p2.start, rise=p2.rise, hold=p2.hold - trim2, fall=p2.fall, magnitude=p2.magnitude)
    excess -= trim2

    # if still over cap, trim pulse 1's hold (and shift pulse 2's start back to match)
    if excess > 0:
        trim1 = min(p1.hold, excess)
        p1 = Pulse(start=p1.start, rise=p1.rise, hold=p1.hold - trim1, fall=p1.fall, magnitude=p1.magnitude)
        excess -= trim1

    new_p2_start = p1.start + p1.rise + p1.hold + p1.fall
    p2 = Pulse(start=new_p2_start, rise=p2.rise, hold=p2.hold, fall=p2.fall, magnitude=p2.magnitude)
    return [p1, p2]


def sample_capped_same_sign_pulses(rng: np.random.Generator, spec: ControlRangeSpec, duration_s: float,
                                    cap_s: float = TOTAL_DURATION_CAP_S) -> List[Pulse]:
    pulses = sample_same_sign_sequential_pulses(rng, spec, duration_s)
    return cap_total_pulse_duration(pulses, cap_s)


def build_candidate_d_v3_profile(
    rng: np.random.Generator, alpha_trim: float, throttle_trim: float, elevator_trim: float, duration_s: float,
    cap_s: float = TOTAL_DURATION_CAP_S,
) -> ControlProfile:
    elevator_pulses = sample_capped_same_sign_pulses(rng, CANDIDATE_D_V2_ELEVATOR_SPEC, duration_s, cap_s)
    return ControlProfile(
        elevator_trim=elevator_trim, throttle_trim=throttle_trim,
        elevator_pulses=elevator_pulses, throttle_pulses=[],
    )
