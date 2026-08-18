"""Controlled physics-validation stage for the AeroGuard longitudinal model.

This script does NOT modify or extend the core physics engine
(aeroguard/aircraft.py, aerodynamics.py, dynamics.py, integrator.py).
It only imports and exercises those modules under controlled,
independent conditions to characterize the model's valid operating
behavior before any large-scale trajectory generation is attempted.

Sections:
    1. Pre-stall lift curve linearity        (alpha ~ 0-15 deg)
    2. Post-stall lift curve monotonicity     (alpha ~ 15-30 deg)
    3. Theoretical stall speed vs simulation
    4. Mass sensitivity of stall speed
    5. Wing-area sensitivity of stall speed
    6. Throttle sensitivity of thrust / dV/dt
    7. Controlled (small) elevator perturbation response (from corrected trim)
    8. Low-speed / high-flight-path-angle validity envelope (documented, not fixed)
    9. Zero-perturbation trim-hold check (corrected trim_level_flight())

Each section prints a table and a pass/fail check to stdout, and most
sections also save a plot to outputs/validation/.

Run with:
    python scripts/validate_physics.py
"""

import os
import sys

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aeroguard.aerodynamics import (
    G,
    RHO_SEA_LEVEL,
    drag_force,
    lift_coefficient,
    lift_force,
    thrust_force,
)
from aeroguard.aircraft import Aircraft
from aeroguard.dynamics import Controls, equations_of_motion
from aeroguard.integrator import integrate
from simulate import trim_level_flight

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs", "validation")
os.makedirs(OUT_DIR, exist_ok=True)

CHECKS = []  # (name, passed: bool, detail: str)


def check(name, condition, detail=""):
    CHECKS.append((name, bool(condition), detail))
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


def section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# ---------------------------------------------------------------------------
# 1. Pre-stall lift curve linearity
# ---------------------------------------------------------------------------

def section_1_prestall_linearity(aircraft, V_ref=45.0):
    section("1. PRE-STALL LIFT CURVE (alpha ~ 0-15 deg)")
    print(f"Reference airspeed for context (does not affect CL(alpha) itself): {V_ref} m/s")

    alphas_deg = np.linspace(0.0, 15.0, 61)
    alphas_rad = np.radians(alphas_deg)
    cl = np.array([lift_coefficient(a, aircraft) for a in alphas_rad])
    cl_pure_linear = aircraft.CL0 + aircraft.CL_alpha * alphas_rad
    rel_dev_pct = 100.0 * (cl - cl_pure_linear) / cl_pure_linear
    L = np.array([lift_force(V_ref, a, aircraft) for a in alphas_rad])

    print(f"{'alpha(deg)':>10} {'CL(model)':>10} {'CL(pure linear)':>16} {'rel dev %':>10} {'L(N) @ V_ref':>13}")
    for i in range(0, len(alphas_deg), 5):
        print(f"{alphas_deg[i]:10.1f} {cl[i]:10.4f} {cl_pure_linear[i]:16.4f} {rel_dev_pct[i]:10.3f} {L[i]:13.1f}")

    max_dev = np.max(np.abs(rel_dev_pct))
    check(
        "CL(alpha) stays within 8% of the pure-linear formula over 0-15 deg",
        max_dev < 8.0,
        f"max |rel dev| = {max_dev:.2f}% (at alpha={alphas_deg[np.argmax(np.abs(rel_dev_pct))]:.1f} deg)",
    )
    check("CL is monotonically increasing over 0-15 deg", np.all(np.diff(cl) > 0))

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].plot(alphas_deg, cl, label="CL(alpha), model", linewidth=2)
    axes[0].plot(alphas_deg, cl_pure_linear, "--", label="pure linear CL0 + CL_alpha*alpha", linewidth=1.5)
    axes[0].set_xlabel("angle of attack alpha [deg]")
    axes[0].set_ylabel("CL")
    axes[0].set_title("Pre-stall CL(alpha): model vs pure linear")
    axes[0].legend()
    axes[0].grid(True)

    axes[1].plot(alphas_deg, rel_dev_pct, color="darkorange")
    axes[1].axhline(0, color="k", linewidth=0.8)
    axes[1].set_xlabel("angle of attack alpha [deg]")
    axes[1].set_ylabel("relative deviation from pure linear [%]")
    axes[1].set_title("Departure from linearity (grows approaching stall)")
    axes[1].grid(True)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "01_prestall_linearity.png"), dpi=150)
    plt.close(fig)
    print(f"Saved outputs/validation/01_prestall_linearity.png")


# ---------------------------------------------------------------------------
# 2. Post-stall lift curve monotonicity
# ---------------------------------------------------------------------------

def section_2_poststall_monotonic(aircraft):
    section("2. POST-STALL LIFT CURVE (alpha ~ 15-30 deg)")

    alphas_deg = np.linspace(15.0, 30.0, 61)
    alphas_rad = np.radians(alphas_deg)
    cl = np.array([lift_coefficient(a, aircraft) for a in alphas_rad])

    print(f"{'alpha(deg)':>10} {'CL(model)':>10}")
    for i in range(0, len(alphas_deg), 5):
        print(f"{alphas_deg[i]:10.1f} {cl[i]:10.4f}")

    # The true peak sits essentially AT alpha_stall (~16.07 deg, confirmed
    # in the prior post-stall-correction stage: CL_post(alpha_stall) is
    # constructed to exactly equal CL_linear(alpha_stall)). A sweep
    # starting at 15 deg is therefore still on the rising side of the
    # single peak for its first ~1 deg -- that is expected pre-peak
    # behaviour, not a rebound. The requirement we actually care about
    # (no rebound / monotonic decay) is checked from the peak onward.
    peak_idx = np.argmax(cl)
    peak_alpha_deg = alphas_deg[peak_idx]
    print(f"Peak CL = {cl[peak_idx]:.4f} at alpha = {peak_alpha_deg:.2f} deg (~= alpha_stall = {np.degrees(aircraft.alpha_stall):.2f} deg)")

    diffs_from_peak = np.diff(cl[peak_idx:])
    check(
        f"CL decreases monotonically from its peak (alpha={peak_alpha_deg:.1f} deg) out to 30 deg",
        np.all(diffs_from_peak < 0),
        f"max step past peak = {diffs_from_peak.max():.5f} (should be < 0)",
    )
    check(
        "No rebound: CL at 30 deg is lower than CL at 20 deg",
        cl[-1] < cl[np.argmin(np.abs(alphas_deg - 20.0))],
    )

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(alphas_deg, cl, linewidth=2)
    ax.axvline(np.degrees(aircraft.alpha_stall), color="r", linestyle="--", linewidth=1, label="alpha_stall")
    ax.plot(peak_alpha_deg, cl[peak_idx], "ko", markersize=6, label=f"peak ({peak_alpha_deg:.1f} deg)")
    ax.set_xlabel("angle of attack alpha [deg]")
    ax.set_ylabel("CL")
    ax.set_title("Post-stall CL(alpha): monotonic decay from the peak, no rebound")
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "02_poststall_monotonic.png"), dpi=150)
    plt.close(fig)
    print(f"Saved outputs/validation/02_poststall_monotonic.png")


# ---------------------------------------------------------------------------
# 3. Stall speed: theoretical vs simulated
# ---------------------------------------------------------------------------

def cl_max_of(aircraft, search_range_deg=(0.0, 40.0), n=2000):
    """Numerically find CLmax by direct sampling (does not assume where
    the peak is — treats the model as a black box)."""
    alphas = np.radians(np.linspace(*search_range_deg, n))
    cls = np.array([lift_coefficient(a, aircraft) for a in alphas])
    idx = np.argmax(cls)
    return cls[idx], alphas[idx]


def stall_speed(aircraft, cl_max, rho=RHO_SEA_LEVEL):
    """V_stall = sqrt(2*m*g / (rho*S*CLmax)) — the classic 1g level-flight
    stall-speed formula, using this model's own CLmax."""
    return np.sqrt(2.0 * aircraft.mass * G / (rho * aircraft.wing_area * cl_max))


def section_3_stall_speed(aircraft):
    section("3. STALL-SPEED BEHAVIOR")

    cl_max, alpha_at_cl_max = cl_max_of(aircraft)
    V_stall = stall_speed(aircraft, cl_max)
    print(f"CLmax (numerically found) = {cl_max:.4f} at alpha = {np.degrees(alpha_at_cl_max):.2f} deg")
    print(f"Theoretical 1g level-flight stall speed: V_stall = sqrt(2*m*g / (rho*S*CLmax)) = {V_stall:.2f} m/s")

    check(
        "CLmax occurs at (or very near) alpha_stall",
        abs(np.degrees(alpha_at_cl_max) - np.degrees(aircraft.alpha_stall)) < 0.5,
    )

    # Algebraic cross-check: sweep candidate airspeeds and see whether the
    # CL required for level flight (L=W) at that speed is achievable
    # (<= CLmax). This directly demonstrates why V_stall is a hard floor
    # for *level* flight in this model.
    print("\nRequired CL for level flight (L=W) at various airspeeds vs CLmax:")
    print(f"{'V (m/s)':>10} {'V/V_stall':>10} {'CL required':>13} {'achievable?':>12}")
    speeds = V_stall * np.array([0.7, 0.8, 0.9, 0.95, 1.0, 1.05, 1.1, 1.2, 1.4])
    achievable_flags = []
    for V in speeds:
        cl_req = 2.0 * aircraft.mass * G / (RHO_SEA_LEVEL * aircraft.wing_area * V ** 2)
        achievable = cl_req <= cl_max
        achievable_flags.append(achievable)
        print(f"{V:10.2f} {V / V_stall:10.3f} {cl_req:13.4f} {'yes' if achievable else 'NO':>12}")

    # Below V_stall should be unachievable, at/above should be achievable
    below = np.array(speeds) < V_stall * 0.999
    at_or_above = ~below
    check(
        "Level flight is unachievable below V_stall (CL required exceeds CLmax)",
        not any(np.array(achievable_flags)[below]),
    )
    check(
        "Level flight is achievable at/above V_stall",
        all(np.array(achievable_flags)[at_or_above]),
    )

    # Dynamic cross-check: trim exactly AT V_stall using alpha=alpha at CLmax,
    # gamma=0, and confirm dV/dt, dgamma/dt are both ~0 (a valid trim point).
    # Then repeat 5% below V_stall at the *same* best-possible alpha (CLmax)
    # and confirm the aircraft cannot hold altitude even with maximum lift.
    def trim_check(V, alpha, label):
        D = drag_force(V, alpha, aircraft)
        throttle = min(max(D / (aircraft.thrust_max * np.cos(alpha)), 0.0), 1.0)
        state = np.array([V, 0.0, alpha, 1000.0, 0.0])  # gamma=0, theta=alpha
        controls = Controls(throttle=throttle, elevator=0.0)
        d_state = equations_of_motion(0.0, state, controls, aircraft)
        print(
            f"  {label}: V={V:.2f} m/s, alpha={np.degrees(alpha):.2f} deg, "
            f"throttle={throttle:.3f} -> dV/dt={d_state[0]:.4f} m/s^2, dgamma/dt={np.degrees(d_state[1]):.4f} deg/s"
        )
        return d_state

    print("\nDynamic trim check at CLmax angle of attack:")
    d_at = trim_check(V_stall, alpha_at_cl_max, "At V_stall     ")
    d_below = trim_check(V_stall * 0.95, alpha_at_cl_max, "5% below V_stall")

    # Note on tolerance: throttle here is only solved for dV/dt=0
    # (T*cos(alpha)=D); alpha is pinned to alpha_at_cl_max rather than
    # also being solved for dgamma/dt=0 exactly. At alpha~16 deg, thrust's
    # vertical component T*sin(alpha) is not negligible, so a small
    # residual dgamma/dt is expected even at a "valid" trim -- the point
    # of this check is that it is small (a fraction of a deg/s) and, most
    # importantly, of the opposite sign from the below-V_stall case.
    check(
        "At V_stall with alpha=alpha(CLmax), dgamma/dt residual is small (partial trim, alpha not re-solved)",
        abs(d_at[1]) < 0.02,
        f"dgamma/dt = {np.degrees(d_at[1]):.4f} deg/s (vs {np.degrees(d_below[1]):.4f} deg/s just below V_stall)",
    )
    check(
        "5% below V_stall, even at the BEST possible alpha (CLmax), dgamma/dt < 0 (cannot hold altitude)",
        d_below[1] < 0,
        f"dgamma/dt = {np.degrees(d_below[1]):.4f} deg/s",
    )

    print(
        "\nNote: V_stall as computed here is a *level-flight* (1g) figure. "
        "In the demo trajectory validated previously, airspeed dipped to "
        "~13.6 m/s during a steep zoom climb (flight-path angle up to ~52 deg) "
        "-- well below this V_stall. That is expected and not a contradiction: "
        "during a steep climb the lift needed is ~m*g*cos(gamma), which is much "
        "less than m*g, so the aircraft can (temporarily) fly slower than the "
        "1g stall speed while pitched steeply upward."
    )

    return V_stall, cl_max


# ---------------------------------------------------------------------------
# 4. Mass sensitivity
# ---------------------------------------------------------------------------

def section_4_mass_sensitivity(base_aircraft, cl_max):
    section("4. MASS SENSITIVITY")

    masses = np.array([800.0, 1000.0, 1200.0, 1400.0, 1600.0, 1800.0])
    required_lift = masses * G
    v_stalls = np.array([
        stall_speed(Aircraft(mass=m, wing_area=base_aircraft.wing_area), cl_max) for m in masses
    ])

    print(f"{'mass (kg)':>10} {'required L=W (N)':>18} {'V_stall (m/s)':>14}")
    for m, L, Vs in zip(masses, required_lift, v_stalls):
        print(f"{m:10.1f} {L:18.1f} {Vs:14.2f}")

    check("Required lift (=weight) increases monotonically with mass", np.all(np.diff(required_lift) > 0))
    check("Stall speed increases monotonically with mass", np.all(np.diff(v_stalls) > 0))

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].plot(masses, required_lift, "o-")
    axes[0].set_xlabel("mass [kg]")
    axes[0].set_ylabel("required lift for level flight [N]")
    axes[0].set_title("Required lift vs mass")
    axes[0].grid(True)

    axes[1].plot(masses, v_stalls, "o-", color="darkred")
    axes[1].set_xlabel("mass [kg]")
    axes[1].set_ylabel("stall speed [m/s]")
    axes[1].set_title("Stall speed vs mass")
    axes[1].grid(True)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "04_mass_sensitivity.png"), dpi=150)
    plt.close(fig)
    print("Saved outputs/validation/04_mass_sensitivity.png")


# ---------------------------------------------------------------------------
# 5. Wing-area sensitivity
# ---------------------------------------------------------------------------

def section_5_wing_area_sensitivity(base_aircraft, cl_max):
    section("5. WING-AREA SENSITIVITY")

    areas = np.array([10.0, 13.0, 16.2, 20.0, 25.0, 30.0])
    v_stalls = np.array([
        stall_speed(Aircraft(mass=base_aircraft.mass, wing_area=s), cl_max) for s in areas
    ])

    print(f"{'wing area (m^2)':>16} {'V_stall (m/s)':>14}")
    for s, Vs in zip(areas, v_stalls):
        print(f"{s:16.1f} {Vs:14.2f}")

    check("Stall speed decreases monotonically as wing area increases", np.all(np.diff(v_stalls) < 0))

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(areas, v_stalls, "o-", color="green")
    ax.set_xlabel("wing area S [m^2]")
    ax.set_ylabel("stall speed [m/s]")
    ax.set_title("Stall speed vs wing area (mass, CLmax fixed)")
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "05_wing_area_sensitivity.png"), dpi=150)
    plt.close(fig)
    print("Saved outputs/validation/05_wing_area_sensitivity.png")


# ---------------------------------------------------------------------------
# 6. Throttle sensitivity
# ---------------------------------------------------------------------------

def section_6_throttle_sensitivity(aircraft):
    section("6. THROTTLE SENSITIVITY")

    # Controlled flight condition: fixed V, alpha, gamma, q (a representative
    # cruise-like point, not a full trim solve -- we only care about how T
    # and dV/dt respond to throttle at an otherwise-frozen state).
    V, alpha, gamma, q = 45.0, np.radians(4.0), 0.0, 0.0
    state = np.array([V, gamma, alpha + gamma, 1000.0, q])

    throttles = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    thrusts = np.array([thrust_force(th, aircraft) for th in throttles])
    dV_list = []
    for th in throttles:
        controls = Controls(throttle=th, elevator=0.0)
        d_state = equations_of_motion(0.0, state, controls, aircraft)
        dV_list.append(d_state[0])
    dV_list = np.array(dV_list)

    print(f"Fixed condition: V={V} m/s, alpha={np.degrees(alpha):.1f} deg, gamma=0, q=0")
    print(f"{'throttle':>10} {'thrust (N)':>12} {'dV/dt (m/s^2)':>14}")
    for th, T, dV in zip(throttles, thrusts, dV_list):
        print(f"{th:10.2f} {T:12.1f} {dV:14.4f}")

    check("Thrust increases monotonically with throttle", np.all(np.diff(thrusts) > 0))
    check("dV/dt increases monotonically with throttle", np.all(np.diff(dV_list) > 0))

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].plot(throttles, thrusts, "o-")
    axes[0].set_xlabel("throttle [0-1]")
    axes[0].set_ylabel("thrust [N]")
    axes[0].set_title("Thrust vs throttle")
    axes[0].grid(True)

    axes[1].plot(throttles, dV_list, "o-", color="purple")
    axes[1].axhline(0, color="k", linewidth=0.8)
    axes[1].set_xlabel("throttle [0-1]")
    axes[1].set_ylabel("dV/dt [m/s^2]")
    axes[1].set_title("dV/dt vs throttle (fixed flight condition)")
    axes[1].grid(True)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "06_throttle_sensitivity.png"), dpi=150)
    plt.close(fig)
    print("Saved outputs/validation/06_throttle_sensitivity.png")


# ---------------------------------------------------------------------------
# 7. Controlled (small) elevator perturbation
# ---------------------------------------------------------------------------

def section_7_small_elevator_response(aircraft):
    section("7. CONTROLLED ELEVATOR TEST (small perturbation, from corrected trim)")

    V0 = 45.0
    alpha_trim, throttle_trim, elevator_trim = trim_level_flight(aircraft, V0)

    state0 = np.array([V0, 0.0, alpha_trim, 1000.0, 0.0])

    SMALL_ELEVATOR = 0.02  # rad (~1.1 deg) -- vs the 0.15 rad demo-script step, ON TOP of elevator_trim
    print(f"Trim: alpha={np.degrees(alpha_trim):.2f} deg, throttle={throttle_trim:.3f}, elevator_trim={np.degrees(elevator_trim):.2f} deg")
    print(f"Elevator perturbation: +{SMALL_ELEVATOR} rad ({np.degrees(SMALL_ELEVATOR):.2f} deg) on top of trim, held from t=2s to t=5s")
    print("(compare to the original demo's 0.15 rad / 8.6 deg step; also see section 9 for the zero-perturbation baseline)")

    def controls_at(t):
        elevator = elevator_trim + (SMALL_ELEVATOR if 2.0 <= t < 5.0 else 0.0)
        return Controls(throttle=throttle_trim, elevator=elevator)

    def rhs(t, state):
        return equations_of_motion(t, state, controls_at(t), aircraft)

    dt = 0.01
    t, y = integrate(rhs, state0, (0.0, 20.0), dt)
    V, gamma, theta, h, q = y[:, 0], y[:, 1], y[:, 2], y[:, 3], y[:, 4]
    alpha = theta - gamma

    print(f"\n{'t':>6} {'alpha(deg)':>10} {'theta(deg)':>10} {'q(deg/s)':>10} {'V(m/s)':>8} {'h(m)':>9}")
    for tt in np.arange(0, 20.01, 2.0):
        idx = int(round(tt / dt))
        print(
            f"{t[idx]:6.1f} {np.degrees(alpha[idx]):10.3f} {np.degrees(theta[idx]):10.3f} "
            f"{np.degrees(q[idx]):10.3f} {V[idx]:8.2f} {h[idx]:9.2f}"
        )

    max_alpha_dev_deg = np.degrees(np.max(np.abs(alpha - alpha_trim)))
    max_q_deg = np.degrees(np.max(np.abs(q)))
    no_nan = np.all(np.isfinite(y))

    check("Small elevator input stays well clear of stall", max_alpha_dev_deg < 5.0, f"max |alpha - alpha_trim| = {max_alpha_dev_deg:.2f} deg")
    check("Pitch rate stays small and bounded (smooth response)", max_q_deg < 10.0, f"max |q| = {max_q_deg:.2f} deg/s")
    check("No NaN/Inf anywhere in the response (numerically well-behaved)", no_nan)

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    axes = axes.flatten()
    labels_data = [
        ("alpha [deg]", np.degrees(alpha)),
        ("theta [deg]", np.degrees(theta)),
        ("q [deg/s]", np.degrees(q)),
        ("V [m/s]", V),
        ("h [m]", h),
    ]
    for ax, (label, data) in zip(axes, labels_data):
        ax.plot(t, data)
        ax.set_xlabel("time [s]")
        ax.set_ylabel(label)
        ax.set_title(f"{label} vs time")
        ax.grid(True)
    axes[-1].axis("off")

    fig.suptitle(f"Small elevator perturbation (trim + {SMALL_ELEVATOR} rad, t=2-5s): smoothness check")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "07_small_elevator_response.png"), dpi=150)
    plt.close(fig)
    print("Saved outputs/validation/07_small_elevator_response.png")


# ---------------------------------------------------------------------------
# 8. Low-speed / high-angle validity envelope (documentation only)
# ---------------------------------------------------------------------------

def section_8_validity_envelope(aircraft, V_stall):
    section("8. LOW-SPEED / HIGH-FLIGHT-PATH-ANGLE VALIDITY ENVELOPE (documentation only)")

    print(
        "This section characterizes where the model's own equations become\n"
        "numerically or physically questionable. Nothing is changed here.\n"
    )

    # (a) Numerical sensitivity of dgamma/dt as V -> 0. dgamma/dt has V in
    # the denominator, guarded by V_safe = max(V, 1e-3) in dynamics.py. We
    # show how sensitive dgamma/dt is to airspeed at otherwise-fixed lift,
    # holding alpha at alpha_stall and gamma=0.
    alpha = aircraft.alpha_stall
    speeds = np.array([30, 20, 15, 10, 7, 5, 3, 2, 1, 0.5, 0.1])
    print(f"{'V (m/s)':>8} {'V / V_stall':>12} {'|dgamma/dt| (deg/s)':>20}")
    dgamma_list = []
    for V in speeds:
        state = np.array([V, 0.0, alpha, 1000.0, 0.0])
        controls = Controls(throttle=1.0, elevator=0.0)
        d_state = equations_of_motion(0.0, state, controls, aircraft)
        dgamma_deg = np.degrees(d_state[1])
        dgamma_list.append(dgamma_deg)
        print(f"{V:8.2f} {V / V_stall:12.3f} {abs(dgamma_deg):20.2f}")

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(speeds, np.abs(dgamma_list), "o-", color="crimson")
    ax.axvline(V_stall, color="k", linestyle="--", linewidth=1, label=f"V_stall = {V_stall:.1f} m/s")
    ax.set_xlabel("airspeed V [m/s]")
    ax.set_ylabel("|dgamma/dt| [deg/s]")
    ax.set_title("Growth of |dgamma/dt| as airspeed -> 0\n(1/V term in the flight-path-angle equation)")
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "08_low_speed_sensitivity.png"), dpi=150)
    plt.close(fig)
    print("Saved outputs/validation/08_low_speed_sensitivity.png")

    print(
        "\nObservations and recommended envelope (NOT enforced anywhere yet):\n"
        "\n"
        "  1. Low-airspeed singularity: m*V*dgamma/dt = L + T*sin(alpha) - m*g*cos(gamma)\n"
        "     divides by V. dynamics.py guards this with V_safe = max(V, 1e-3), which\n"
        "     prevents a divide-by-zero crash but does NOT prevent dgamma/dt from\n"
        "     becoming numerically huge as V shrinks toward that floor -- the table\n"
        f"     above shows |dgamma/dt| growing sharply below roughly V < {0.3*V_stall:.1f} m/s\n"
        f"     (~30% of V_stall = {V_stall:.1f} m/s). Below this, gamma can change by many\n"
        "     degrees per integrator step, and RK4 accuracy at the current fixed\n"
        "     dt=0.01s is no longer trustworthy there.\n"
        "\n"
        "  2. The physical concept of 'airspeed' and 'flight-path angle' for a point-\n"
        "     mass model becomes ill-defined well before V actually reaches zero --\n"
        "     a real aircraft at very low airspeed (near or below stall speed) is in\n"
        "     an actual stall/departure, where roll, yaw, and unsteady/rotational\n"
        "     aerodynamics dominate. This 2D longitudinal, quasi-steady model has no\n"
        "     representation of that regime at all -- it will keep integrating a\n"
        "     smooth CL(alpha) curve through angles and speeds where a real aircraft\n"
        "     would be tumbling.\n"
        "\n"
        "  3. Extreme flight-path angles: the previously-validated demo trajectory\n"
        "     reached gamma ~= 52 deg (zoom climb) with V dropping to 13.6 m/s\n"
        f"     ({13.6/V_stall*100:.0f}% of V_stall) at the top. That point sits inside the\n"
        "     region flagged above. The equations of motion remain mathematically\n"
        "     well-defined there (no NaN/Inf was observed), but the aerodynamic\n"
        "     coefficients (CL(alpha), the drag polar) were never intended to\n"
        "     represent near-hover, high-pitch, low-dynamic-pressure flight, so\n"
        "     results in that corner of the state space should be treated as\n"
        "     qualitative at best.\n"
        "\n"
        "  4. Suggested (documented, not enforced) validity envelope for this\n"
        f"     simplified model: V >~ {0.5*V_stall:.0f}-{0.7*V_stall:.0f} m/s (roughly 0.5-0.7 * V_stall)\n"
        "     and |gamma| <~ 45 deg. Trajectories that leave this envelope (as the\n"
        "     original demo's zoom-climb did) are still numerically well-behaved,\n"
        "     but their physical realism should not be trusted, and any future\n"
        "     ML/boundary-recovery work should treat this as a labeled 'model\n"
        "     validity' region distinct from the aerodynamic stall boundary itself."
    )


# ---------------------------------------------------------------------------
# 9. Zero-perturbation trim-hold check
# ---------------------------------------------------------------------------

def section_9_zero_perturbation_trim_hold(aircraft):
    section("9. ZERO-PERTURBATION TRIM-HOLD CHECK (corrected trim_level_flight())")

    print(
        "trim_level_flight() now solves force balance (dV/dt~=0, dgamma/dt~=0)\n"
        "AND the pitch-moment balance (dq/dt~=0) numerically against the actual\n"
        "nonlinear aerodynamic model (bisection on the real lift_coefficient()),\n"
        "not a linear approximation of it. With throttle and elevator held at\n"
        "their trim values and NO further input at all, the aircraft should stay\n"
        "at its initial state for the whole window, limited only by RK4/floating-\n"
        "point numerical error (the bisection itself converges to ~1e-12 rad).\n"
    )

    V0 = 45.0
    alpha_trim, throttle_trim, elevator_trim = trim_level_flight(aircraft, V0)
    state0 = np.array([V0, 0.0, alpha_trim, 1000.0, 0.0])

    d0 = equations_of_motion(0.0, state0, Controls(throttle=throttle_trim, elevator=elevator_trim), aircraft)
    print(f"Trim: alpha={np.degrees(alpha_trim):.4f} deg, throttle={throttle_trim:.4f}, elevator={np.degrees(elevator_trim):.4f} deg")
    print(
        f"Initial derivatives: dV/dt={d0[0]:.6f} m/s^2, dgamma/dt={np.degrees(d0[1]):.6f} deg/s, "
        f"dq/dt={np.degrees(d0[4]):.8f} deg/s^2"
    )

    def rhs(t, state):
        return equations_of_motion(t, state, Controls(throttle=throttle_trim, elevator=elevator_trim), aircraft)

    dt = 0.01
    t, y = integrate(rhs, state0, (0.0, 20.0), dt)
    V, gamma, theta, h, q = y[:, 0], y[:, 1], y[:, 2], y[:, 3], y[:, 4]
    alpha = theta - gamma

    print(f"\n{'t':>6} {'V(m/s)':>9} {'alpha(deg)':>11} {'gamma(deg)':>11} {'h(m)':>10}")
    for tt in [0, 5, 10, 15, 20]:
        idx = int(round(tt / dt))
        print(f"{t[idx]:6.1f} {V[idx]:9.4f} {np.degrees(alpha[idx]):11.4f} {np.degrees(gamma[idx]):11.4f} {h[idx]:10.3f}")

    max_dV = np.max(np.abs(V - V0))
    max_dalpha_deg = np.degrees(np.max(np.abs(alpha - alpha_trim)))
    max_dgamma_deg = np.degrees(np.max(np.abs(gamma)))
    max_dh = np.max(np.abs(h - 1000.0))

    print(f"\nMax drift over 20s: |dV|={max_dV:.4f} m/s, |dalpha|={max_dalpha_deg:.4f} deg, |dgamma|={max_dgamma_deg:.4f} deg, |dh|={max_dh:.4f} m")

    check("dV/dt at trim is ~0", abs(d0[0]) < 1e-6)
    check("dgamma/dt at trim is ~0 (deg/s)", np.degrees(abs(d0[1])) < 1.0)
    check("dq/dt at trim is exactly 0", abs(d0[4]) < 1e-9)
    check("Airspeed stays within 2 m/s of V0 over 20s of zero input", max_dV < 2.0, f"max |dV| = {max_dV:.3f} m/s")
    check("Alpha stays within 1 deg of trim over 20s of zero input", max_dalpha_deg < 1.0, f"max |dalpha| = {max_dalpha_deg:.3f} deg")
    check("Gamma stays within 1 deg of level over 20s of zero input", max_dgamma_deg < 1.0, f"max |dgamma| = {max_dgamma_deg:.3f} deg")
    check("Altitude stays within 10 m of h0 over 20s of zero input", max_dh < 10.0, f"max |dh| = {max_dh:.3f} m")

    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    axes[0, 0].plot(t, V)
    axes[0, 0].set_xlabel("time [s]"); axes[0, 0].set_ylabel("V [m/s]"); axes[0, 0].set_title("Airspeed (zero input)"); axes[0, 0].grid(True)
    axes[0, 1].plot(t, np.degrees(alpha))
    axes[0, 1].set_xlabel("time [s]"); axes[0, 1].set_ylabel("alpha [deg]"); axes[0, 1].set_title("Angle of attack (zero input)"); axes[0, 1].grid(True)
    axes[1, 0].plot(t, np.degrees(gamma))
    axes[1, 0].set_xlabel("time [s]"); axes[1, 0].set_ylabel("gamma [deg]"); axes[1, 0].set_title("Flight-path angle (zero input)"); axes[1, 0].grid(True)
    axes[1, 1].plot(t, h)
    axes[1, 1].set_xlabel("time [s]"); axes[1, 1].set_ylabel("h [m]"); axes[1, 1].set_title("Altitude (zero input)"); axes[1, 1].grid(True)
    fig.suptitle("Zero-perturbation trim-hold check: corrected trim_level_flight()")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "09_zero_perturbation_trim_hold.png"), dpi=150)
    plt.close(fig)
    print("Saved outputs/validation/09_zero_perturbation_trim_hold.png")


def main():
    aircraft = Aircraft()

    section_1_prestall_linearity(aircraft)
    section_2_poststall_monotonic(aircraft)
    V_stall, cl_max = section_3_stall_speed(aircraft)
    section_4_mass_sensitivity(aircraft, cl_max)
    section_5_wing_area_sensitivity(aircraft, cl_max)
    section_6_throttle_sensitivity(aircraft)
    section_7_small_elevator_response(aircraft)
    section_8_validity_envelope(aircraft, V_stall)
    section_9_zero_perturbation_trim_hold(aircraft)

    section("SUMMARY")
    n_pass = sum(1 for _, ok, _ in CHECKS if ok)
    n_total = len(CHECKS)
    for name, ok, detail in CHECKS:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n{n_pass}/{n_total} checks passed.")
    if n_pass < n_total:
        sys.exit(1)


if __name__ == "__main__":
    main()
