"""Single-trajectory simulation with validity-envelope enforcement.

Reuses the existing, unmodified physics engine directly:
    aeroguard.dynamics.equations_of_motion   -- the equations of motion
    aeroguard.integrator.rk4_step             -- the RK4 stepper

This module adds NOTHING to the physics itself. It only:
  1. steps rk4_step in a loop (instead of the batch aeroguard.integrator.integrate,
     which cannot check state validity mid-run),
  2. records telemetry at every step,
  3. checks the documented validity envelope (Section 8: minimum
     airspeed, maximum |gamma|, and ground contact / altitude <= 0) and
     stops the simulation -- WITHOUT clipping the state -- the moment
     it is exceeded, recording why.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np

from aeroguard.aerodynamics import thrust_force
from aeroguard.aircraft import Aircraft
from aeroguard.dynamics import Controls, equations_of_motion
from aeroguard.integrator import rk4_step

# Termination reasons (Section 15 / 18).
TERMINATION_COMPLETED = "completed_normally"
TERMINATION_LOW_AIRSPEED = "validity_envelope_low_airspeed"
TERMINATION_GAMMA_EXCEEDED = "validity_envelope_gamma_exceeded"
TERMINATION_GROUND_CONTACT = "ground_contact"
TERMINATION_NAN_INF = "numerical_instability_nan_inf"
TERMINATION_INVALID_CONTROL = "invalid_control_values"

VALIDITY_ENVELOPE_TERMINATIONS = frozenset({TERMINATION_LOW_AIRSPEED, TERMINATION_GAMMA_EXCEEDED, TERMINATION_GROUND_CONTACT})


@dataclass
class TrajectoryResult:
    trajectory_id: str
    t: np.ndarray
    V: np.ndarray
    alpha: np.ndarray
    theta: np.ndarray
    gamma: np.ndarray
    altitude: np.ndarray
    pitch_rate: np.ndarray
    vertical_speed: np.ndarray
    thrust: np.ndarray
    elevator: np.ndarray
    throttle: np.ndarray
    termination_reason: str
    validity_envelope_exceeded: bool = field(init=False)

    def __post_init__(self):
        self.validity_envelope_exceeded = self.termination_reason in VALIDITY_ENVELOPE_TERMINATIONS


def simulate_trajectory(
    trajectory_id: str,
    aircraft: Aircraft,
    control_profile: Callable[[float], Controls],
    V0: float,
    gamma0: float,
    alpha0: float,
    h0: float,
    q0: float,
    duration_s: float,
    dt: float,
    v_floor: float,
    gamma_max_rad: float,
) -> TrajectoryResult:
    """Simulate one trajectory from an initial state, stepping RK4 at
    fixed dt, stopping early (without clipping) if the state leaves the
    documented validity envelope or becomes non-finite.
    """
    theta0 = alpha0 + gamma0
    state = np.array([V0, gamma0, theta0, h0, q0], dtype=float)

    n_steps = int(round(duration_s / dt))

    ts, Vs, alphas, thetas, gammas, hs, qs = [], [], [], [], [], [], []
    vspeeds, thrusts, elevs, throttles = [], [], [], []

    def rhs(tt, ss):
        return equations_of_motion(tt, ss, control_profile(tt), aircraft)

    termination_reason = TERMINATION_COMPLETED

    for i in range(n_steps + 1):
        t = i * dt

        if not np.all(np.isfinite(state)):
            termination_reason = TERMINATION_NAN_INF
            break

        V, gamma, theta, h, q = state

        # Ground-contact check: added after two v0.2 trajectories were
        # found (by audit, not by design) descending to negative
        # altitude while staying inside the V/gamma envelope the whole
        # time (a sustained sub-gamma-cap dive with enough duration to
        # descend past a moderate starting altitude). h is not fed back
        # into the physics in this simplified model (rho is constant),
        # so the equations stay numerically well-defined below h=0 --
        # this is a validity-envelope condition, not a physics fix.
        #
        # Unlike the V-floor/gamma-cap checks below (soft "model
        # validity" thresholds, where recording the boundary-crossing
        # sample itself is informative), h<=0 is a hard physical
        # impossibility -- the aircraft cannot fly below the ground. So
        # this check runs BEFORE recording telemetry: the trajectory's
        # last recorded row is always the last physically valid
        # (h>0) sample, never a negative-altitude one. Nothing is
        # clipped -- the state that would have gone negative is simply
        # never added to the output arrays, and simulation stops there.
        if h <= 0:
            termination_reason = TERMINATION_GROUND_CONTACT
            break

        alpha = theta - gamma

        controls = control_profile(t)
        if not (np.isfinite(controls.elevator) and np.isfinite(controls.throttle)):
            termination_reason = TERMINATION_INVALID_CONTROL
            break

        thrust = thrust_force(controls.throttle, aircraft)
        vertical_speed = V * np.sin(gamma)

        ts.append(t)
        Vs.append(V)
        alphas.append(alpha)
        thetas.append(theta)
        gammas.append(gamma)
        hs.append(h)
        qs.append(q)
        vspeeds.append(vertical_speed)
        thrusts.append(thrust)
        elevs.append(controls.elevator)
        throttles.append(controls.throttle)

        if V < v_floor:
            termination_reason = TERMINATION_LOW_AIRSPEED
            break
        if abs(gamma) > gamma_max_rad:
            termination_reason = TERMINATION_GAMMA_EXCEEDED
            break

        if i == n_steps:
            termination_reason = TERMINATION_COMPLETED
            break

        state = rk4_step(rhs, t, state, dt)

    return TrajectoryResult(
        trajectory_id=trajectory_id,
        t=np.array(ts),
        V=np.array(Vs),
        alpha=np.array(alphas),
        theta=np.array(thetas),
        gamma=np.array(gammas),
        altitude=np.array(hs),
        pitch_rate=np.array(qs),
        vertical_speed=np.array(vspeeds),
        thrust=np.array(thrusts),
        elevator=np.array(elevs),
        throttle=np.array(throttles),
        termination_reason=termination_reason,
    )
