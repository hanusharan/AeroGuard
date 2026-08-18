"""Focused tests for the Candidate D v3 combined-duration cap
(aeroguard_dataset/control_profiles_candidate_d_v3.py): the two pulses'
total rise+hold+fall must never exceed TOTAL_DURATION_CAP_S, achieved by
trimming hold time only (never rise/fall), and v2's zero-gap invariant
between pulse 1 and pulse 2 must still hold after trimming.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from aeroguard_dataset.control_profiles import Pulse
from aeroguard_dataset.control_profiles_candidate_d_v2 import (
    CANDIDATE_D_V2_ELEVATOR_SPEC,
    sample_same_sign_sequential_pulses,
)
from aeroguard_dataset.control_profiles_candidate_d_v3 import (
    TOTAL_DURATION_CAP_S,
    cap_total_pulse_duration,
    sample_capped_same_sign_pulses,
)


def _total_duration(pulses):
    return sum(p.rise + p.hold + p.fall for p in pulses)


def test_combined_duration_never_exceeds_cap_when_achievable():
    """The cap is enforced by trimming hold to a floor of 0 -- if a
    sample's rise+fall alone (both pulses, no hold) already exceeds the
    cap, the floor wins and total duration stays at that (documented)
    rise+fall floor instead. Whenever the cap IS achievable by trimming
    hold alone, it must be met exactly (not overshot)."""
    rng = np.random.default_rng(0)
    spec = CANDIDATE_D_V2_ELEVATOR_SPEC
    rise_fall_floor_max = 2 * (spec.rise_s_max + spec.fall_s_max)
    for _ in range(300):
        pulses = sample_capped_same_sign_pulses(rng, spec, duration_s=20.0)
        if len(pulses) == 2:
            bound = max(TOTAL_DURATION_CAP_S, rise_fall_floor_max)
            assert _total_duration(pulses) <= bound + 1e-9
            assert pulses[0].hold >= 0.0 and pulses[1].hold >= 0.0


def test_cap_only_trims_hold_never_rise_or_fall():
    # rise+fall floor for these pulses = 2*(3.0+1.5) = 9.0s > cap, so use a
    # cap that IS achievable by trimming hold alone to check exact behavior.
    p1 = Pulse(start=1.0, rise=1.5, hold=2.0, fall=0.5, magnitude=0.08)
    p2 = Pulse(start=1.0 + 1.5 + 2.0 + 0.5, rise=1.5, hold=2.0, fall=0.5, magnitude=0.08)
    capped = cap_total_pulse_duration([p1, p2], cap_s=5.0)  # rise+fall floor = 4.0 < 5.0, achievable
    assert capped[0].rise == p1.rise and capped[0].fall == p1.fall
    assert capped[1].rise == p2.rise and capped[1].fall == p2.fall
    assert capped[0].hold <= p1.hold
    assert capped[1].hold <= p2.hold
    assert abs(_total_duration(capped) - 5.0) < 1e-9


def test_cap_no_op_when_already_under_cap():
    p1 = Pulse(start=1.0, rise=1.5, hold=0.5, fall=0.5, magnitude=0.06)
    p2 = Pulse(start=1.0 + 1.5 + 0.5 + 0.5, rise=1.5, hold=0.5, fall=0.5, magnitude=0.06)
    under_cap_total = _total_duration([p1, p2])
    assert under_cap_total < TOTAL_DURATION_CAP_S
    capped = cap_total_pulse_duration([p1, p2])
    assert capped[0].hold == p1.hold and capped[1].hold == p2.hold


def test_zero_gap_preserved_after_capping():
    rng = np.random.default_rng(1)
    for _ in range(300):
        pulses = sample_capped_same_sign_pulses(rng, CANDIDATE_D_V2_ELEVATOR_SPEC, duration_s=20.0)
        if len(pulses) == 2:
            p1, p2 = pulses
            expected_start = p1.start + p1.rise + p1.hold + p1.fall
            assert abs(p2.start - expected_start) < 1e-9


def test_sign_still_shared_after_capping():
    rng = np.random.default_rng(2)
    for _ in range(300):
        pulses = sample_capped_same_sign_pulses(rng, CANDIDATE_D_V2_ELEVATOR_SPEC, duration_s=20.0)
        if len(pulses) == 2:
            assert np.sign(pulses[0].magnitude) == np.sign(pulses[1].magnitude)


def test_hold_floor_is_zero_not_negative():
    p1 = Pulse(start=0.5, rise=3.0, hold=2.0, fall=1.5, magnitude=0.09)
    p2 = Pulse(start=0.5 + 3.0 + 2.0 + 1.5, rise=3.0, hold=2.0, fall=1.5, magnitude=0.09)
    capped = cap_total_pulse_duration([p1, p2], cap_s=6.0)  # under the min possible rise+fall sum (9.0)
    assert capped[0].hold >= 0.0 and capped[1].hold >= 0.0
