import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aeroguard.aerodynamics import G, RHO_SEA_LEVEL, drag_force
from aeroguard.aircraft import Aircraft
from aeroguard.dynamics import Controls, alpha_of, equations_of_motion


@pytest.fixture
def aircraft():
    return Aircraft()


def test_alpha_of_state():
    state = np.array([50.0, np.radians(2.0), np.radians(6.0), 1000.0, 0.0])
    assert alpha_of(state) == pytest.approx(np.radians(4.0))


def test_climb_rate_matches_v_sin_gamma(aircraft):
    V = 40.0
    gamma = np.radians(5.0)
    state = np.array([V, gamma, np.radians(6.0), 1000.0, 0.0])
    controls = Controls(throttle=0.5, elevator=0.0)

    d_state = equations_of_motion(0.0, state, controls, aircraft)
    dh_dt = d_state[3]

    assert dh_dt == pytest.approx(V * np.sin(gamma))


def test_dtheta_equals_pitch_rate(aircraft):
    q = np.radians(3.0)
    state = np.array([40.0, 0.0, np.radians(4.0), 1000.0, q])
    controls = Controls(throttle=0.5, elevator=0.0)

    d_state = equations_of_motion(0.0, state, controls, aircraft)
    dtheta_dt = d_state[2]

    assert dtheta_dt == pytest.approx(q)


def test_positive_elevator_increases_pitch_rate_derivative(aircraft):
    """With everything else held fixed, a larger elevator deflection
    should increase dq/dt in this simplified linear pitch model."""
    state = np.array([40.0, 0.0, np.radians(4.0), 1000.0, 0.0])

    controls_small = Controls(throttle=0.5, elevator=0.05)
    controls_large = Controls(throttle=0.5, elevator=0.2)

    dq_small = equations_of_motion(0.0, state, controls_small, aircraft)[4]
    dq_large = equations_of_motion(0.0, state, controls_large, aircraft)[4]

    assert dq_large > dq_small


def test_pitch_damping_reduces_dq_for_nonzero_q(aircraft):
    """Higher pitch rate q should pull dq/dt down (damping), all else equal."""
    state_low_q = np.array([40.0, 0.0, np.radians(4.0), 1000.0, 0.0])
    state_high_q = np.array([40.0, 0.0, np.radians(4.0), 1000.0, np.radians(20.0)])
    controls = Controls(throttle=0.5, elevator=0.0)

    dq_low = equations_of_motion(0.0, state_low_q, controls, aircraft)[4]
    dq_high = equations_of_motion(0.0, state_high_q, controls, aircraft)[4]

    assert dq_high < dq_low


def test_throttle_zero_gives_less_thrust_forward_accel_than_full_throttle(aircraft):
    state = np.array([40.0, 0.0, np.radians(4.0), 1000.0, 0.0])

    controls_idle = Controls(throttle=0.0, elevator=0.0)
    controls_full = Controls(throttle=1.0, elevator=0.0)

    dV_idle = equations_of_motion(0.0, state, controls_idle, aircraft)[0]
    dV_full = equations_of_motion(0.0, state, controls_full, aircraft)[0]

    assert dV_full > dV_idle


def test_approximate_level_trim_gives_near_zero_dv_and_dgamma(aircraft):
    """At an algebraically-computed trim point (L=W, T*cos(alpha)=D,
    gamma=0), dV/dt and dgamma/dt should be close to zero."""
    V0 = 45.0
    q_bar = 0.5 * RHO_SEA_LEVEL * V0 ** 2
    cl_trim = aircraft.mass * G / (q_bar * aircraft.wing_area)
    alpha_trim = (cl_trim - aircraft.CL0) / aircraft.CL_alpha

    D_trim = drag_force(V0, alpha_trim, aircraft)
    throttle_trim = D_trim / (aircraft.thrust_max * np.cos(alpha_trim))

    gamma0 = 0.0
    theta0 = alpha_trim + gamma0
    state = np.array([V0, gamma0, theta0, 1000.0, 0.0])
    controls = Controls(throttle=throttle_trim, elevator=0.0)

    d_state = equations_of_motion(0.0, state, controls, aircraft)
    dV, dgamma = d_state[0], d_state[1]

    assert dV == pytest.approx(0.0, abs=1e-2)
    assert dgamma == pytest.approx(0.0, abs=1e-2)
