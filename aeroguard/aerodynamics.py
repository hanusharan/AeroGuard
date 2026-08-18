"""Aerodynamic force and coefficient models.

Stall emerges from a smooth mathematical blend between a linear
pre-stall lift curve and a decaying post-stall curve — there is no
discrete "if alpha > alpha_stall" branch anywhere in this module. The
blending technique (a logistic/sigmoid blend between two closed-form
lift curves) follows the standard approach used for small fixed-wing
UAV models, not a validated wind-tunnel-derived curve for any real
airframe.

The post-stall branch is an exponential decay anchored to the linear
curve's value at alpha_stall (see lift_coefficient docstring). An
earlier version used a flat-plate-theory curve
(2*sign(alpha)*sin(alpha)^2*cos(alpha)) here; that curve has its own
local maximum near 55 degrees, which produced a non-physical secondary
lift *rebound* around 25-30 degrees for this aircraft's parameters —
a range trajectories can plausibly reach. The exponential decay below
is monotonic for all alpha beyond alpha_stall, by construction, so no
such rebound can occur.
"""

import numpy as np

RHO_SEA_LEVEL = 1.225  # kg/m^3, constant air density (see README assumptions)
G = 9.81  # m/s^2


def _stall_blend(alpha: float, alpha_stall: float, rate: float) -> float:
    """Sigmoid-like blending function sigma(alpha) in [0, 1].

    sigma ~ 0 well inside the linear (pre-stall) region and
    sigma ~ 1 well past the critical angle of attack, with a smooth
    transition in between. Symmetric in +/- alpha_stall so the model
    also behaves sensibly for negative (inverted) angles of attack.
    """
    num = (
        1.0
        + np.exp(-rate * (alpha - alpha_stall))
        + np.exp(rate * (alpha + alpha_stall))
    )
    den = (1.0 + np.exp(-rate * (alpha - alpha_stall))) * (
        1.0 + np.exp(rate * (alpha + alpha_stall))
    )
    return num / den


def lift_coefficient(alpha: float, aircraft) -> float:
    """Nonlinear lift coefficient CL(alpha).

    Blends:
      * a linear pre-stall curve   CL_linear = CL0 + CL_alpha * alpha
      * a post-stall curve that decays exponentially past alpha_stall:
            CL_peak = CL0 + CL_alpha * alpha_stall
            excess  = max(|alpha| - alpha_stall, 0)
            CL_post = sign(alpha) * CL_peak * exp(-post_stall_decay_rate * excess)

    CL_peak is the value the *linear* curve would reach exactly at the
    critical angle of attack (the standard linear-extrapolation
    approximation of CLmax). CL_post is defined so it exactly equals
    CL_linear at alpha = alpha_stall (both branches agree there), and
    then decays monotonically toward zero as |alpha| grows further —
    it never exceeds CL_peak, and it never turns back upward. The
    `excess` clamp (a continuous max(), not a branch on "is this
    stalled") keeps CL_post flat at CL_peak for |alpha| <= alpha_stall,
    which keeps it from distorting the pre-stall region even where the
    blend weight sigma is not yet negligible.

    The blend weight sigma(alpha) transitions smoothly around
    +/- aircraft.alpha_stall, so the stall behaviour (rise, peak,
    monotonic fall) is an emergent property of the two curves and the
    blend, not a rule-based cutoff.
    """
    sigma = _stall_blend(alpha, aircraft.alpha_stall, aircraft.stall_transition_rate)

    cl_linear = aircraft.CL0 + aircraft.CL_alpha * alpha

    cl_peak = aircraft.CL0 + aircraft.CL_alpha * aircraft.alpha_stall
    excess = np.maximum(np.abs(alpha) - aircraft.alpha_stall, 0.0)
    cl_post_stall = np.sign(alpha) * cl_peak * np.exp(-aircraft.post_stall_decay_rate * excess)

    return (1.0 - sigma) * cl_linear + sigma * cl_post_stall


def drag_coefficient(cl: float, aircraft) -> float:
    """Parabolic drag polar: CD = CD0 + k * CL^2."""
    return aircraft.CD0 + aircraft.k * cl ** 2


def dynamic_pressure(rho: float, V: float) -> float:
    """q_bar = 0.5 * rho * V^2."""
    return 0.5 * rho * V ** 2


def lift_force(V: float, alpha: float, aircraft, rho: float = RHO_SEA_LEVEL) -> float:
    """L = 0.5 * rho * V^2 * S * CL(alpha)."""
    cl = lift_coefficient(alpha, aircraft)
    return dynamic_pressure(rho, V) * aircraft.wing_area * cl


def drag_force(V: float, alpha: float, aircraft, rho: float = RHO_SEA_LEVEL) -> float:
    """D = 0.5 * rho * V^2 * S * CD(CL(alpha))."""
    cl = lift_coefficient(alpha, aircraft)
    cd = drag_coefficient(cl, aircraft)
    return dynamic_pressure(rho, V) * aircraft.wing_area * cd


def thrust_force(throttle: float, aircraft) -> float:
    """Simple linear throttle-to-thrust map: T = throttle * T_max.

    throttle is clamped to [0, 1].
    """
    throttle = min(max(throttle, 0.0), 1.0)
    return throttle * aircraft.thrust_max
