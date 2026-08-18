"""Focused tests for the generalization-experiment alternative mechanism
(aeroguard_dataset/control_profiles_alt_single.py): the single pulse's
rise+hold+fall must never exceed TOTAL_DURATION_CAP_S, achieved by
trimming hold time only (never rise/fall), and the mechanism must always
produce exactly one elevator pulse with no throttle perturbation.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from aeroguard_dataset.control_profiles import Pulse
from aeroguard_dataset.control_profiles_alt_single import (
    ALT_SINGLE_ELEVATOR_SPEC,
    TOTAL_DURATION_CAP_S,
    build_alt_single_pulse_profile,
    cap_single_pulse_duration,
    sample_capped_single_pulse,
)


def _duration(p):
    return p.rise + p.hold + p.fall


def test_duration_never_exceeds_cap_when_achievable():
    rng = np.random.default_rng(0)
    rise_fall_floor_max = ALT_SINGLE_ELEVATOR_SPEC.rise_s_max + ALT_SINGLE_ELEVATOR_SPEC.fall_s_max
    for _ in range(300):
        pulses = sample_capped_single_pulse(rng, ALT_SINGLE_ELEVATOR_SPEC, duration_s=20.0)
        if len(pulses) == 1:
            bound = max(TOTAL_DURATION_CAP_S, rise_fall_floor_max)
            assert _duration(pulses[0]) <= bound + 1e-9
            assert pulses[0].hold >= 0.0


def test_cap_only_trims_hold_never_rise_or_fall():
    p = Pulse(start=1.0, rise=3.0, hold=2.0, fall=1.5, magnitude=0.09)  # rise+fall=4.5 < cap
    capped = cap_single_pulse_duration(p, cap_s=6.0)
    assert capped.rise == p.rise and capped.fall == p.fall
    assert capped.hold <= p.hold
    assert abs(_duration(capped) - 6.0) < 1e-9


def test_cap_no_op_when_already_under_cap():
    p = Pulse(start=1.0, rise=1.5, hold=0.5, fall=1.0, magnitude=0.08)
    assert _duration(p) < TOTAL_DURATION_CAP_S
    capped = cap_single_pulse_duration(p)
    assert capped.hold == p.hold


def test_hold_floor_is_zero_not_negative():
    p = Pulse(start=0.5, rise=4.5, hold=2.0, fall=2.0, magnitude=0.10)  # rise+fall=6.5 > cap=6.0
    capped = cap_single_pulse_duration(p, cap_s=6.0)
    assert capped.hold >= 0.0
    assert capped.rise == p.rise and capped.fall == p.fall


def test_profile_has_exactly_one_elevator_pulse_and_no_throttle():
    rng = np.random.default_rng(3)
    for _ in range(50):
        profile = build_alt_single_pulse_profile(rng, alpha_trim=0.02, throttle_trim=0.4, elevator_trim=0.01, duration_s=20.0)
        assert len(profile.elevator_pulses) == 1
        assert len(profile.throttle_pulses) == 0


def test_structurally_distinct_from_candidate_d_two_pulse_shape():
    """The whole point of this mechanism (task Phase 2) is a single-hump
    alpha response, not Candidate D's two-pulse staircase -- verify the
    generated profile is never a 2-pulse (or more) sequence."""
    rng = np.random.default_rng(4)
    for _ in range(50):
        pulses = sample_capped_single_pulse(rng, ALT_SINGLE_ELEVATOR_SPEC, duration_s=20.0)
        assert len(pulses) <= 1
