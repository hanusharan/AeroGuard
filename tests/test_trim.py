"""Tests for the level-flight trim helper (scripts/simulate.py).

trim_level_flight() is not part of the core physics engine (aeroguard/),
it is a convenience helper used by the demo/validation scripts to pick a
sensible initial condition. These tests check that its returned state
actually satisfies equilibrium in all three of the relevant equations of
motion -- not approximately (as the old linear-CL version did), but to
near machine precision, since it is now solved numerically against the
actual nonlinear aerodynamic model via bisection.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from aeroguard.aircraft import Aircraft
from aeroguard.dynamics import Controls, equations_of_motion
from simulate import trim_level_flight, TRIM_ALPHA_LOWER_BOUND_DEG


@pytest.fixture
def aircraft():
    return Aircraft()


def _trim_derivatives(aircraft, V0):
    alpha_trim, throttle_trim, elevator_trim = trim_level_flight(aircraft, V0)
    state = np.array([V0, 0.0, alpha_trim, 1000.0, 0.0])  # gamma=0, theta=alpha_trim, q=0
    controls = Controls(throttle=throttle_trim, elevator=elevator_trim)
    d_state = equations_of_motion(0.0, state, controls, aircraft)
    return alpha_trim, throttle_trim, elevator_trim, d_state


def test_trim_elevator_matches_closed_form_solution(aircraft):
    alpha_trim, _, elevator_trim, _ = _trim_derivatives(aircraft, 45.0)
    expected = aircraft.alpha_stiffness * alpha_trim / aircraft.elevator_effectiveness
    assert elevator_trim == pytest.approx(expected)


def test_trim_dV_near_zero(aircraft):
    _, _, _, d_state = _trim_derivatives(aircraft, 45.0)
    assert abs(d_state[0]) < 1e-9


def test_trim_dgamma_near_zero(aircraft):
    # The numerical (bisection) solver achieves ~1e-11 deg/s in practice;
    # 1e-6 deg/s leaves generous headroom while still being far tighter
    # than the old linear-CL solver's ~0.2 deg/s residual.
    _, _, _, d_state = _trim_derivatives(aircraft, 45.0)
    assert np.degrees(abs(d_state[1])) < 1e-6


def test_trim_dq_near_zero(aircraft):
    _, _, _, d_state = _trim_derivatives(aircraft, 45.0)
    assert abs(d_state[4]) == pytest.approx(0.0, abs=1e-9)


def test_trim_dq_is_far_from_zero_without_elevator_correction(aircraft):
    """Sanity check that this is a real fix: with elevator=0 (the old
    behaviour) at the same trim alpha/throttle, dq/dt should NOT be
    near zero -- confirming the correction is actually doing something."""
    alpha_trim, throttle_trim, _, _ = _trim_derivatives(aircraft, 45.0)
    state = np.array([45.0, 0.0, alpha_trim, 1000.0, 0.0])
    controls_no_elevator_trim = Controls(throttle=throttle_trim, elevator=0.0)
    d_state = equations_of_motion(0.0, state, controls_no_elevator_trim, aircraft)
    assert abs(d_state[4]) > 0.1


@pytest.mark.parametrize("V0", [30.0, 35.0, 45.0, 55.0, 65.0, 75.0])
def test_trim_holds_across_several_airspeeds(aircraft, V0):
    """The numerical trim should satisfy all three equilibrium conditions
    to near machine precision across the intended operating range (well
    above stall speed, ~26 m/s for the default aircraft, and comfortably
    below where throttle saturates, ~90+ m/s)."""
    _, _, _, d_state = _trim_derivatives(aircraft, V0)
    assert abs(d_state[0]) < 1e-9
    assert np.degrees(abs(d_state[1])) < 1e-6
    assert abs(d_state[4]) == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("V0", [30.0, 35.0, 45.0, 55.0, 65.0, 75.0])
def test_trim_uses_actual_nonlinear_cl_not_linear_approximation(aircraft, V0):
    """The returned alpha must satisfy the level-flight residual computed
    from the actual lift_coefficient(), which differs from the old
    pure-linear approximation -- this directly checks that the solve is
    against the real (nonlinear) model, not the linear stand-in."""
    from aeroguard.aerodynamics import lift_coefficient

    alpha_trim, _, _, _ = _trim_derivatives(aircraft, V0)
    cl_actual = lift_coefficient(alpha_trim, aircraft)
    cl_pure_linear = aircraft.CL0 + aircraft.CL_alpha * alpha_trim
    # Near stall speed the nonlinear/linear gap is largest; away from it,
    # smaller but still nonzero. Either way it should be a real, nonzero
    # deviation -- i.e. the solver is not secretly just doing the old
    # linear solve.
    assert cl_actual != pytest.approx(cl_pure_linear, rel=1e-6)


@pytest.mark.parametrize("V0", [30.0, 35.0, 45.0, 55.0, 65.0, 75.0])
def test_trim_alpha_is_the_front_side_root_not_back_side(aircraft, V0):
    """The level-flight residual can have two roots near stall speed: an
    efficient 'front side' trim below alpha_stall, and a 'back side of
    the power curve' trim above it (see trim_level_flight docstring).
    The solver must always return the front-side one."""
    alpha_trim, _, _, _ = _trim_derivatives(aircraft, V0)
    assert alpha_trim < aircraft.alpha_stall


def test_trim_raises_below_stall_speed(aircraft):
    """No level-flight trim exists below the aircraft's stall speed (the
    residual is negative everywhere in the search bracket) -- the solver
    should fail loudly, not silently return a bogus alpha."""
    with pytest.raises(ValueError):
        trim_level_flight(aircraft, 15.0)  # well below ~26 m/s stall speed


def test_trim_bracket_lower_bound_is_reasonable():
    assert 0.0 < TRIM_ALPHA_LOWER_BOUND_DEG < 90.0
