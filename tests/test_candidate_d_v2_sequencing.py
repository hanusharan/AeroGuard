"""Focused tests for the Candidate D v2 sequencing fix
(aeroguard_dataset/control_profiles_candidate_d_v2.py): both pulses must
share one sign, and pulse 2 must start exactly when pulse 1's fall phase
ends (no idle gap) -- the two structural changes that eliminate the
sign-reversal dive-then-zoom-climb mechanism found in the original
GRADUAL_D_TWO_STAGE candidate (reconciliation report, Task 4).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from aeroguard_dataset.config import GRADUAL_D_TWO_STAGE
from aeroguard_dataset.control_profiles_candidate_d_v2 import (
    CANDIDATE_D_V2_ELEVATOR_SPEC,
    sample_same_sign_sequential_pulses,
)


def test_elevator_spec_matches_original_candidate_d():
    """Magnitude/rise/hold/fall ranges must be unchanged from
    GRADUAL_D_TWO_STAGE -- only sequencing/signing differs."""
    assert CANDIDATE_D_V2_ELEVATOR_SPEC is GRADUAL_D_TWO_STAGE.elevator


def test_two_pulses_always_same_sign():
    rng = np.random.default_rng(0)
    for _ in range(200):
        pulses = sample_same_sign_sequential_pulses(rng, CANDIDATE_D_V2_ELEVATOR_SPEC, duration_s=20.0)
        if len(pulses) == 2:
            assert np.sign(pulses[0].magnitude) == np.sign(pulses[1].magnitude)


def test_zero_gap_between_pulses():
    """Pulse 2 must start exactly when pulse 1's fall ends (start + rise +
    hold + fall), not after an idle gap."""
    rng = np.random.default_rng(1)
    for _ in range(200):
        pulses = sample_same_sign_sequential_pulses(rng, CANDIDATE_D_V2_ELEVATOR_SPEC, duration_s=20.0)
        if len(pulses) == 2:
            p1, p2 = pulses
            expected_start = p1.start + p1.rise + p1.hold + p1.fall
            assert abs(p2.start - expected_start) < 1e-9


def test_pulses_within_original_magnitude_and_timing_ranges():
    rng = np.random.default_rng(2)
    spec = CANDIDATE_D_V2_ELEVATOR_SPEC
    for _ in range(200):
        pulses = sample_same_sign_sequential_pulses(rng, spec, duration_s=20.0)
        for p in pulses:
            assert spec.magnitude_min <= abs(p.magnitude) <= spec.magnitude_max
            assert spec.rise_s_min <= p.rise <= spec.rise_s_max
            assert spec.hold_s_min <= p.hold <= spec.hold_s_max
            assert spec.fall_s_min <= p.fall <= spec.fall_s_max


def test_build_profile_produces_elevator_only_control():
    from aeroguard.aircraft import Aircraft
    from aeroguard_dataset.control_profiles_candidate_d_v2 import build_candidate_d_v2_profile
    from aeroguard_dataset.paths import trim_level_flight

    aircraft = Aircraft()
    rng = np.random.default_rng(3)
    alpha_trim, throttle_trim, elevator_trim = trim_level_flight(aircraft, 45.0)
    profile = build_candidate_d_v2_profile(rng, alpha_trim, throttle_trim, elevator_trim, 20.0)
    assert len(profile.throttle_pulses) == 0
    controls_at_trim = profile(0.0)
    assert np.isclose(controls_at_trim.throttle, throttle_trim)
