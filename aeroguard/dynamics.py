"""2D longitudinal equations of motion.

State vector (numpy array, order fixed):
    state = [V, gamma, theta, h, q]

    V     : airspeed [m/s]
    gamma : flight-path angle [rad]
    theta : pitch angle [rad]
    h     : altitude [m]
    q     : pitch rate [rad/s]

Angle of attack is not stored as an independent state; it is derived:
    alpha = theta - gamma

Controls:
    throttle : [0, 1], maps to thrust via aerodynamics.thrust_force
    elevator : elevator deflection [rad], drives pitch rate via a
               simplified linear short-period pitching-moment model
"""

from dataclasses import dataclass

import numpy as np

from .aerodynamics import G, RHO_SEA_LEVEL, drag_force, lift_force, thrust_force

N_STATES = 5
STATE_NAMES = ("V", "gamma", "theta", "h", "q")


@dataclass
class Controls:
    throttle: float  # [0, 1]
    elevator: float  # [rad]


def alpha_of(state: np.ndarray) -> float:
    """Angle of attack alpha = theta - gamma."""
    _, gamma, theta, _, _ = state
    return theta - gamma


def equations_of_motion(
    t: float,
    state: np.ndarray,
    controls: Controls,
    aircraft,
    rho: float = RHO_SEA_LEVEL,
) -> np.ndarray:
    """Compute d(state)/dt for the 2D longitudinal model.

    Implements:
        m*dV/dt     = T*cos(alpha) - D - m*g*sin(gamma)
        m*V*dgamma/dt = L + T*sin(alpha) - m*g*cos(gamma)
        dh/dt       = V*sin(gamma)
        dtheta/dt   = q
        dq/dt       = simplified linear pitch-response model (see below)
    """
    V, gamma, theta, h, q = state
    alpha = theta - gamma
    m = aircraft.mass

    T = thrust_force(controls.throttle, aircraft)
    L = lift_force(V, alpha, aircraft, rho=rho)
    D = drag_force(V, alpha, aircraft, rho=rho)

    dV = (T * np.cos(alpha) - D - m * G * np.sin(gamma)) / m

    # Guard against division by ~0 airspeed (not physically meaningful
    # below stall/minimum-control speeds, but keeps the integrator safe).
    V_safe = max(V, 1e-3)
    dgamma = (L + T * np.sin(alpha) - m * G * np.cos(gamma)) / (m * V_safe)

    dh = V * np.sin(gamma)

    dtheta = q

    # Simplified short-period pitch-rate response:
    #   Iyy * dq/dt = M_elevator*delta_e - M_q*q - M_alpha*alpha
    # This is a linear surrogate for the pitching-moment equation, not
    # a full aerodynamic moment model. It gives the elevator authority
    # to change q (and hence theta and alpha), with damping in q and a
    # weak alpha-restoring term, which is enough to produce plausible
    # pitch dynamics for this stage of the project.
    M = (
        aircraft.elevator_effectiveness * controls.elevator
        - aircraft.pitch_damping * q
        - aircraft.alpha_stiffness * alpha
    )
    dq = M / aircraft.Iyy

    return np.array([dV, dgamma, dtheta, dh, dq])
