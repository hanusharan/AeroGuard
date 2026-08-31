"""Dump reference values from the REAL Python physics engine.

Used to verify that dashboard/src/lib/physics.ts is a faithful port and not a
lookalike. Writes dashboard/parity/reference.json; compare against the
TypeScript engine with `node parity/check.mjs` (see parity/README.md).
"""

import dataclasses
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from aeroguard.aerodynamics import lift_coefficient, drag_coefficient  # noqa: E402
from aeroguard.aircraft import Aircraft  # noqa: E402
from aeroguard.dynamics import Controls, equations_of_motion  # noqa: E402
from aeroguard.integrator import rk4_step  # noqa: E402
from aeroguard_dataset.control_profiles import Pulse  # noqa: E402
from aeroguard_dataset.events import resolve_stall_boundary  # noqa: E402
from simulate import trim_level_flight  # noqa: E402
from validate_physics import cl_max_of, stall_speed  # noqa: E402

# Airframes: the stock generic aircraft, plus two perturbed ones so the port is
# exercised away from the defaults (heavier/smaller wing, and a different
# stall-curve shape).
AIRFRAMES = {
    "default": Aircraft(),
    "heavy_small_wing": dataclasses.replace(
        Aircraft(), mass=1850.0, wing_area=12.4, thrust_max=3300.0
    ),
    "soft_stall": dataclasses.replace(
        Aircraft(), CL0=0.35, CL_alpha=4.9, alpha_stall=np.radians(13.5),
        stall_transition_rate=14.0, post_stall_decay_rate=2.1, mass=980.0, wing_area=19.0,
    ),
}

SCENARIOS = {
    "default": dict(v0=45.0, pull=dict(start=2.0, rise=4.0, hold=2.0, fall=2.0, magnitude=0.11)),
    "heavy_small_wing": dict(v0=62.0, pull=dict(start=1.5, rise=2.5, hold=3.0, fall=1.5, magnitude=0.16)),
    "soft_stall": dict(v0=38.0, pull=dict(start=3.0, rise=5.0, hold=1.0, fall=2.5, magnitude=0.09)),
}

DT = 0.01
DURATION = 20.0
# Sample the trajectory at these times rather than dumping 2001 rows.
PROBE_TIMES = [0.0, 1.0, 2.5, 4.0, 5.5, 7.0, 8.5, 10.0, 13.0, 16.0, 19.0]


def run(name):
    ac = AIRFRAMES[name]
    sc = SCENARIOS[name]
    out = {}

    # --- static aero curves -------------------------------------------------
    alphas_deg = [-6.0, -2.0, 0.0, 3.0, 7.5, 11.0, 14.0, 15.9, 16.0, 16.5, 18.0, 22.0, 30.0, 45.0]
    out["cl"] = [float(lift_coefficient(np.radians(a), ac)) for a in alphas_deg]
    out["cd"] = [
        float(drag_coefficient(lift_coefficient(np.radians(a), ac), ac)) for a in alphas_deg
    ]
    out["alphas_deg"] = alphas_deg

    cl_max, alpha_at_peak = cl_max_of(ac)
    out["cl_max"] = float(cl_max)
    out["alpha_at_cl_peak_deg"] = float(np.degrees(alpha_at_peak))
    out["v_stall"] = float(stall_speed(ac, cl_max))

    boundary = resolve_stall_boundary(ac)
    out["boundary_alpha_deg"] = float(np.degrees(boundary.alpha_at_cl_peak))

    # --- trim ---------------------------------------------------------------
    alpha_trim, throttle_trim, elevator_trim = trim_level_flight(ac, sc["v0"])
    out["trim"] = {
        "alpha_deg": float(np.degrees(alpha_trim)),
        "throttle": float(throttle_trim),
        "elevator_deg": float(np.degrees(elevator_trim)),
    }

    # --- full RK4 trajectory ------------------------------------------------
    pulse = Pulse(**sc["pull"])

    def controls_at(t):
        return Controls(throttle=throttle_trim, elevator=elevator_trim + pulse.value_at(t))

    def rhs(t, y):
        return equations_of_motion(t, y, controls_at(t), ac)

    state = np.array([sc["v0"], 0.0, alpha_trim, 1000.0, 0.0])
    n_steps = int(round(DURATION / DT))

    probe_idx = {int(round(t / DT)): t for t in PROBE_TIMES}
    traj = []
    for i in range(n_steps + 1):
        t = i * DT
        if i in probe_idx:
            V, gamma, theta, h, q = state
            traj.append({
                "t": t,
                "V": float(V),
                "alpha_deg": float(np.degrees(theta - gamma)),
                "gamma_deg": float(np.degrees(gamma)),
                "theta_deg": float(np.degrees(theta)),
                "h": float(h),
                "q_deg": float(np.degrees(q)),
                "elevator_deg": float(np.degrees(elevator_trim + pulse.value_at(t))),
                "cl": float(lift_coefficient(theta - gamma, ac)),
            })
        if i < n_steps:
            state = rk4_step(rhs, t, state, DT)
    out["trajectory"] = traj

    # --- pulse shape --------------------------------------------------------
    out["pulse"] = [float(pulse.value_at(t)) for t in np.arange(0.0, 14.0, 0.5)]

    out["aircraft"] = dataclasses.asdict(ac)
    out["scenario"] = sc
    return out


def main():
    ref = {name: run(name) for name in AIRFRAMES}
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reference.json")
    with open(dest, "w") as f:
        json.dump(ref, f, indent=1)
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
