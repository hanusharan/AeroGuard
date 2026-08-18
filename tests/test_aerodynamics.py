import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aeroguard.aircraft import Aircraft
from aeroguard.aerodynamics import (
    drag_coefficient,
    drag_force,
    lift_coefficient,
    lift_force,
    thrust_force,
)


@pytest.fixture
def aircraft():
    return Aircraft()


def test_cl_matches_linear_model_well_below_stall(aircraft):
    # The post-stall branch is anchored at CL_peak (the linear curve's
    # own value at alpha_stall), which is larger than the near-zero
    # values the old flat-plate branch had here. So the same small blend
    # leakage this far from stall now shows up as a slightly larger (but
    # still small, ~1.3%) relative deviation from pure-linear at 5 deg.
    alpha = np.radians(5.0)
    expected = aircraft.CL0 + aircraft.CL_alpha * alpha
    actual = lift_coefficient(alpha, aircraft)
    assert actual == pytest.approx(expected, rel=2e-2)


def test_cl_zero_alpha_close_to_cl0(aircraft):
    # The smooth blend has a small amount of leakage from the post-stall
    # curve even at alpha=0 (by design, there is no hard cutoff), so this
    # is checked to be *close* rather than exact.
    assert lift_coefficient(0.0, aircraft) == pytest.approx(aircraft.CL0, abs=5e-3)


def test_cl_increases_with_alpha_in_linear_region(aircraft):
    alphas = np.radians(np.linspace(-5, 10, 20))
    cls = [lift_coefficient(a, aircraft) for a in alphas]
    assert np.all(np.diff(cls) > 0)


def test_cl_drops_after_stall_onset(aircraft):
    """Stall must emerge from the curve shape: CL well past the critical
    angle of attack should be lower than CL near the critical angle,
    with no explicit if-alpha>threshold branch involved in computing it."""
    alpha_near_stall = aircraft.alpha_stall
    alpha_deep_stall = aircraft.alpha_stall + np.radians(20)

    cl_near = lift_coefficient(alpha_near_stall, aircraft)
    cl_deep = lift_coefficient(alpha_deep_stall, aircraft)

    assert cl_deep < cl_near


def test_cl_has_a_peak_beyond_which_it_decreases(aircraft):
    alphas = np.radians(np.linspace(0, 40, 200))
    cls = np.array([lift_coefficient(a, aircraft) for a in alphas])
    peak_idx = np.argmax(cls)

    # Peak should not be at the very last sample (i.e. CL genuinely
    # turns over and decreases within the sampled range).
    assert peak_idx < len(cls) - 1
    assert cls[-1] < cls[peak_idx]


def test_cl_monotonically_decreases_over_16_to_30_degrees(aircraft):
    """This is the range the original flat-plate post-stall curve
    rebounded in (local min ~24 deg, rising again toward 30 deg). The
    corrected exponential-decay branch must be strictly monotonically
    decreasing here, with no rebound of any kind."""
    alphas_deg = np.arange(16.0, 30.01, 0.5)
    cls = np.array([lift_coefficient(np.radians(d), aircraft) for d in alphas_deg])
    assert np.all(np.diff(cls) < 0)


def test_cl_monotonically_decreases_well_beyond_stall(aircraft):
    """Broader sweep than the 16-30 deg range above: no rebound should
    appear anywhere out to 90 deg either (the old flat-plate curve's
    own peak was at ~55 deg)."""
    alphas_deg = np.arange(16.0, 90.01, 1.0)
    cls = np.array([lift_coefficient(np.radians(d), aircraft) for d in alphas_deg])
    assert np.all(np.diff(cls) < 0)


def test_cl_peak_is_at_or_near_alpha_stall(aircraft):
    """With the new anchored-decay construction, CL_post(alpha_stall)
    equals CL_linear(alpha_stall) exactly, so the overall peak should
    sit right at alpha_stall rather than drifting away from it."""
    alphas_deg = np.linspace(0, 40, 400)
    cls = np.array([lift_coefficient(np.radians(d), aircraft) for d in alphas_deg])
    peak_alpha_deg = alphas_deg[np.argmax(cls)]
    assert peak_alpha_deg == pytest.approx(np.degrees(aircraft.alpha_stall), abs=1.0)


def test_cl_continuous_across_stall_transition(aircraft):
    """No jump in CL value when crossing alpha_stall, sampled at a very
    fine step, i.e. no hidden if-alpha>stall discontinuity."""
    alpha_stall_deg = np.degrees(aircraft.alpha_stall)
    alphas_deg = np.linspace(alpha_stall_deg - 1.0, alpha_stall_deg + 1.0, 2001)
    cls = np.array([lift_coefficient(np.radians(d), aircraft) for d in alphas_deg])
    # Largest step between adjacent samples should be tiny relative to
    # the overall CL scale, i.e. no discrete jump anywhere in the sweep.
    assert np.max(np.abs(np.diff(cls))) < 0.01


def test_cl_symmetric_about_zero_for_symmetric_lift_curve_params():
    # With CL0 = 0 the model should be odd-symmetric in alpha.
    aircraft = Aircraft(CL0=0.0)
    for alpha_deg in [3, 10, 20, 30]:
        alpha = np.radians(alpha_deg)
        cl_pos = lift_coefficient(alpha, aircraft)
        cl_neg = lift_coefficient(-alpha, aircraft)
        assert cl_pos == pytest.approx(-cl_neg, abs=1e-9)


def test_drag_polar_formula(aircraft):
    for cl in [-0.5, 0.0, 0.3, 1.0, 1.5]:
        expected = aircraft.CD0 + aircraft.k * cl ** 2
        assert drag_coefficient(cl, aircraft) == pytest.approx(expected)


def test_drag_coefficient_never_below_cd0(aircraft):
    alphas = np.radians(np.linspace(-30, 30, 50))
    for a in alphas:
        cl = lift_coefficient(a, aircraft)
        cd = drag_coefficient(cl, aircraft)
        assert cd >= aircraft.CD0


def test_lift_force_scales_with_v_squared(aircraft):
    alpha = np.radians(4.0)
    L1 = lift_force(30.0, alpha, aircraft)
    L2 = lift_force(60.0, alpha, aircraft)
    assert L2 == pytest.approx(4.0 * L1, rel=1e-6)


def test_drag_force_scales_with_v_squared(aircraft):
    alpha = np.radians(4.0)
    D1 = drag_force(30.0, alpha, aircraft)
    D2 = drag_force(60.0, alpha, aircraft)
    assert D2 == pytest.approx(4.0 * D1, rel=1e-6)


def test_thrust_is_linear_in_throttle_and_clamped(aircraft):
    assert thrust_force(0.0, aircraft) == pytest.approx(0.0)
    assert thrust_force(1.0, aircraft) == pytest.approx(aircraft.thrust_max)
    assert thrust_force(0.5, aircraft) == pytest.approx(0.5 * aircraft.thrust_max)
    # out-of-range throttle is clamped, not extrapolated
    assert thrust_force(-1.0, aircraft) == pytest.approx(0.0)
    assert thrust_force(2.0, aircraft) == pytest.approx(aircraft.thrust_max)
