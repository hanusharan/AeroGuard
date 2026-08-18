import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aeroguard.integrator import integrate, rk4_step


def test_rk4_step_matches_analytical_exponential_decay():
    """dy/dt = -y  =>  y(t) = y0 * exp(-t). RK4 should be very accurate
    over a single small step."""

    def f(t, y):
        return -y

    y0 = np.array([1.0])
    dt = 0.01
    y1 = rk4_step(f, 0.0, y0, dt)
    expected = np.array([np.exp(-dt)])
    assert y1 == pytest.approx(expected, abs=1e-9)


def test_integrate_exponential_decay_over_time():
    def f(t, y):
        return -y

    y0 = np.array([1.0])
    t, y = integrate(f, y0, (0.0, 2.0), 0.001)

    expected_final = np.exp(-2.0)
    assert y[-1, 0] == pytest.approx(expected_final, abs=1e-6)


def test_integrate_shape_and_time_grid():
    def f(t, y):
        return np.zeros_like(y)

    y0 = np.array([1.0, 2.0])
    t, y = integrate(f, y0, (0.0, 1.0), 0.1)

    assert len(t) == 11
    assert y.shape == (11, 2)
    assert t[0] == pytest.approx(0.0)
    assert t[-1] == pytest.approx(1.0)


def test_integrate_constant_velocity_motion():
    """dy/dt = v (constant) => y(t) = y0 + v*t exactly, RK4 should be exact
    for a linear (constant-derivative) problem regardless of step size."""

    def f(t, y):
        return np.array([2.5])

    y0 = np.array([0.0])
    t, y = integrate(f, y0, (0.0, 4.0), 0.5)

    expected = 2.5 * t
    assert y[:, 0] == pytest.approx(expected, abs=1e-10)
