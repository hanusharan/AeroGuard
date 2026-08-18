"""Run one example trajectory and plot the results.

This script is a demonstration / sanity-check for the physics engine.
It is NOT a validated flight simulation of any real aircraft.

Scenario:
    1. Aircraft starts in a trimmed level-flight condition: trim angle
       of attack and throttle are found by numerically solving the
       actual (nonlinear) force-balance equations, and trim elevator
       deflection is solved from the pitch-moment equation. See
       trim_level_flight() for the exact equations solved.
    2. A pitch-up elevator step is applied for a few seconds, driving
       angle of attack up toward and past the stall region, then the
       elevator is released.
    3. The resulting trajectory is integrated with fixed-step RK4 and
       plotted.

Run with:
    python scripts/simulate.py
"""

import os
import sys

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aeroguard.aerodynamics import G, RHO_SEA_LEVEL, drag_force, lift_coefficient, lift_force
from aeroguard.aircraft import Aircraft
from aeroguard.dynamics import Controls, equations_of_motion
from aeroguard.integrator import integrate

TRIM_ALPHA_LOWER_BOUND_DEG = 20.0  # generous lower bound for the bracket search


def _level_flight_residual(alpha: float, V0: float, aircraft: Aircraft) -> float:
    """Residual of the level-flight (gamma=0) force balance, in alpha alone.

    At gamma=0, dV/dt=0 requires T*cos(alpha) = D(alpha)  =>  T = D(alpha)/cos(alpha).
    Substituting into dgamma/dt=0 (L(alpha) + T*sin(alpha) = m*g) gives:
        L(alpha) + D(alpha)*tan(alpha) - m*g = 0
    This is an exact combination of both equations (not an L=W assumption)
    -- the thrust vector's vertical component T*sin(alpha) is folded in via
    the D*tan(alpha) term, using the ACTUAL nonlinear lift_force/drag_force
    (which in turn call the actual lift_coefficient(alpha, aircraft), not a
    linear approximation).
    """
    L = lift_force(V0, alpha, aircraft, rho=RHO_SEA_LEVEL)
    D = drag_force(V0, alpha, aircraft, rho=RHO_SEA_LEVEL)
    return L + D * np.tan(alpha) - aircraft.mass * G


def _bisect_root(f, lo: float, hi: float, tol: float = 1e-12, max_iter: int = 200) -> float:
    """Deterministic bisection root finder on [lo, hi].

    Requires f(lo) and f(hi) to have opposite signs. No randomness, no
    external dependency -- same result every call for the same inputs.
    """
    f_lo, f_hi = f(lo), f(hi)
    if f_lo == 0.0:
        return lo
    if f_hi == 0.0:
        return hi
    if np.sign(f_lo) == np.sign(f_hi):
        raise ValueError(
            f"trim bracket [{np.degrees(lo):.2f}, {np.degrees(hi):.2f}] deg does not "
            f"straddle a root (f_lo={f_lo:.4g}, f_hi={f_hi:.4g})"
        )

    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        f_mid = f(mid)
        if f_mid == 0.0 or (hi - lo) < tol:
            return mid
        if np.sign(f_mid) == np.sign(f_lo):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def trim_level_flight(aircraft: Aircraft, V0: float):
    """Numerically-exact trim alpha, throttle, and elevator for steady,
    level (gamma=0, q=0) flight, solved against the actual implemented
    nonlinear aerodynamic model (lift_force/drag_force -> lift_coefficient),
    not a linear approximation of it.

    Solves the three equilibrium conditions:
      1 & 2. dV/dt=0 and dgamma/dt=0, combined algebraically (see
             _level_flight_residual) into a single equation in alpha,
             solved by deterministic bisection -- NOT by assuming L=W;
             the thrust vector's vertical component T*sin(alpha) is
             included via that substitution.
      3.     The pitch-moment equation for elevator deflection (dq/dt=0).
             From dynamics.py:
                 Iyy*dq/dt = elevator_effectiveness*delta_e
                             - pitch_damping*q - alpha_stiffness*alpha
             At the trim point q=0, so dq/dt=0 requires:
                 delta_e_trim = alpha_stiffness*alpha_trim / elevator_effectiveness
             (this part is already exact/closed-form -- no root-finding
             needed here, since it's linear in delta_e.)

    IMPORTANT -- why the search bracket is capped at alpha_stall, not just
    "wide enough": _level_flight_residual(alpha) is NOT monotonic once CL
    turns over past stall. Because CL(alpha) rises to a single peak at
    alpha_stall and then decays (the corrected, non-rebounding post-stall
    model), the residual typically has TWO roots for any V0 not far above
    the stall speed:
      * a "front side" root at alpha < alpha_stall -- the efficient,
        lower-drag trim (what we want): as alpha increases toward this
        root, CL is still climbing, so more lift is gained per unit of
        extra drag.
      * a "back side of the power curve" root at alpha > alpha_stall --
        a real, textbook flight-dynamics phenomenon (also called the
        "region of reversed command"): past the CL peak, extra alpha
        buys little/no extra lift but a lot of extra induced drag, so
        holding the same airspeed there requires MORE thrust, not less.
        This is a valid equilibrium in principle, but not the trim we
        want for a benign initial condition.
    A wide, blindly-centered bracket can straddle BOTH roots (so its
    endpoints share a sign and bisection correctly refuses to guess) or,
    worse, converge to the undesired back-side root. The fix is not a
    tolerance hack: since the corrected CL(alpha) has a single peak
    exactly at alpha_stall (see aerodynamics.lift_coefficient), every
    front-side root is guaranteed to lie strictly below alpha_stall, and
    capping the bracket's upper edge there provably excludes the back-side
    root. The lower edge is a generous, physically-motivated bound (real
    trims for this aircraft, CL0 > 0, don't need negative alpha).

    If the bracket does not straddle a root at all (V0 at or below the
    stall speed -- no level-flight trim exists), _bisect_root raises a
    clear ValueError rather than silently returning a wrong answer.

    Throttle is then recovered from T = D(alpha_trim)/cos(alpha_trim) and
    clamped to [0, 1] by the existing thrust model; if that clamp is
    active (V0 requires more thrust than thrust_max can provide), the
    returned state is no longer an exact trim -- the same caveat applied
    to the previous (linear) version of this helper.
    """
    lo = -np.radians(TRIM_ALPHA_LOWER_BOUND_DEG)
    hi = aircraft.alpha_stall

    def residual(alpha):
        return _level_flight_residual(alpha, V0, aircraft)

    alpha_trim = _bisect_root(residual, lo, hi)

    D_trim = drag_force(V0, alpha_trim, aircraft, rho=RHO_SEA_LEVEL)
    throttle_trim = D_trim / (aircraft.thrust_max * np.cos(alpha_trim))
    throttle_trim = min(max(throttle_trim, 0.0), 1.0)

    elevator_trim = aircraft.alpha_stiffness * alpha_trim / aircraft.elevator_effectiveness

    return alpha_trim, throttle_trim, elevator_trim


def make_control_law(throttle_trim: float, elevator_trim: float = 0.0):
    """Constant trim throttle and trim elevator, with a pitch-up elevator
    step (added on top of the trim elevator) from t=2s to t=5s."""

    def controls_at(t: float) -> Controls:
        elevator = elevator_trim + (0.15 if 2.0 <= t < 5.0 else 0.0)
        return Controls(throttle=throttle_trim, elevator=elevator)

    return controls_at


def run_simulation():
    aircraft = Aircraft()

    V0 = 45.0  # m/s
    alpha_trim, throttle_trim, elevator_trim = trim_level_flight(aircraft, V0)

    gamma0 = 0.0
    theta0 = alpha_trim + gamma0
    h0 = 1000.0
    q0 = 0.0
    state0 = np.array([V0, gamma0, theta0, h0, q0])

    controls_law = make_control_law(throttle_trim, elevator_trim)

    def rhs(t, state):
        return equations_of_motion(t, state, controls_law(t), aircraft)

    dt = 0.01
    t_span = (0.0, 20.0)
    t, y = integrate(rhs, state0, t_span, dt)

    V = y[:, 0]
    gamma = y[:, 1]
    theta = y[:, 2]
    h = y[:, 3]
    alpha = theta - gamma
    CL = np.array([lift_coefficient(a, aircraft) for a in alpha])

    return t, V, alpha, h, CL, alpha_trim, throttle_trim, elevator_trim


def plot_results(t, V, alpha, h, CL):
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))

    axes[0, 0].plot(t, V)
    axes[0, 0].set_xlabel("time [s]")
    axes[0, 0].set_ylabel("airspeed V [m/s]")
    axes[0, 0].set_title("Airspeed vs time")
    axes[0, 0].grid(True)

    axes[0, 1].plot(t, np.degrees(alpha))
    axes[0, 1].axhline(16.0, color="r", linestyle="--", linewidth=1, label="~stall AoA")
    axes[0, 1].set_xlabel("time [s]")
    axes[0, 1].set_ylabel("angle of attack alpha [deg]")
    axes[0, 1].set_title("Angle of attack vs time")
    axes[0, 1].legend()
    axes[0, 1].grid(True)

    axes[1, 0].plot(t, h)
    axes[1, 0].set_xlabel("time [s]")
    axes[1, 0].set_ylabel("altitude h [m]")
    axes[1, 0].set_title("Altitude vs time")
    axes[1, 0].grid(True)

    order = np.argsort(alpha)
    axes[1, 1].plot(np.degrees(alpha[order]), CL[order])
    axes[1, 1].axvline(16.0, color="r", linestyle="--", linewidth=1, label="~stall AoA")
    axes[1, 1].set_xlabel("angle of attack alpha [deg]")
    axes[1, 1].set_ylabel("lift coefficient CL")
    axes[1, 1].set_title("CL vs alpha (emergent stall behaviour)")
    axes[1, 1].legend()
    axes[1, 1].grid(True)

    fig.suptitle("AeroGuard: example 2D longitudinal trajectory (not a validated aircraft model)")
    fig.tight_layout()
    return fig


def main():
    t, V, alpha, h, CL, alpha_trim, throttle_trim, elevator_trim = run_simulation()

    print(f"Trim angle of attack: {np.degrees(alpha_trim):.2f} deg")
    print(f"Trim throttle: {throttle_trim:.3f}")
    print(f"Trim elevator: {elevator_trim:.4f} rad ({np.degrees(elevator_trim):.2f} deg)")
    print(f"Max angle of attack reached: {np.degrees(np.max(alpha)):.2f} deg")
    print(f"Final airspeed: {V[-1]:.2f} m/s, final altitude: {h[-1]:.2f} m")

    fig = plot_results(t, V, alpha, h, CL)

    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "trajectory.png")
    fig.savefig(out_path, dpi=150)
    print(f"Saved plot to {out_path}")

    if os.environ.get("AEROGUARD_SHOW_PLOT", "0") == "1":
        plt.show()


if __name__ == "__main__":
    main()
