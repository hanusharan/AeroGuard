"""Item 43: trajectories for one aircraft configuration (PROTOCOL.md sections 1.3-1.5).

The physics is the frozen engine (``equations_of_motion``, ``rk4_step``). Two
things are re-implemented here because the originals hard-code sea-level density:

* ``trim_level_flight_rho`` -- the same residual and bisection as
  ``scripts/simulate.trim_level_flight`` with ``rho`` passed through;
* ``simulate_trajectory_rho`` -- the same loop as
  ``aeroguard_dataset.trajectory_sim.simulate_trajectory`` with ``rho`` passed to
  ``equations_of_motion``.

Both are tested to agree exactly with the originals at rho = 1.225
(tests/test_phase4_sim.py). Everything else (labels, features, events, control
samplers) is imported unchanged.
"""

from typing import Callable, Dict, List

import numpy as np
import pandas as pd

import aeroguard_dataset.paths  # noqa: F401  (sys.path bootstrap for scripts/)
from aeroguard.aerodynamics import G, drag_force, lift_force, thrust_force
from aeroguard.dynamics import Controls, equations_of_motion
from aeroguard.integrator import rk4_step
from aeroguard_dataset.config import NORMAL_CONTROL_CONFIG, STALL_CONTROL_CONFIG, GenerationConfig
from aeroguard_dataset.control_profiles import ControlProfile, Pulse, build_control_profile
from aeroguard_dataset.control_profiles_candidate_d_v3 import TOTAL_DURATION_CAP_S, build_candidate_d_v3_profile
from aeroguard_dataset.events import StallBoundary, resolve_stall_boundary
from aeroguard_dataset.features import compute_features_for_trajectory
from aeroguard_dataset.labeling import compute_future_stall_label
from aeroguard_dataset.trajectory_sim import (
    TERMINATION_COMPLETED, TERMINATION_GAMMA_EXCEEDED, TERMINATION_GROUND_CONTACT, TERMINATION_INVALID_CONTROL,
    TERMINATION_LOW_AIRSPEED, TERMINATION_NAN_INF, TrajectoryResult,
)
from simulate import TRIM_ALPHA_LOWER_BOUND_DEG, _bisect_root  # noqa: E402  (unchanged helpers)

from .configs import BASE, make_aircraft

V0_MULT_LO, V0_MULT_HI = 30.0 / 26.140289984056395, 75.0 / 26.140289984056395  # v0.3 range over v0.3 V_stall
REGIME_COUNTS = {"normal": 80, "stall": 60, "gradual_approach_v3": 160}
SPLIT_FRACTIONS = (0.70, 0.15, 0.15)
GEN = GenerationConfig()  # dt, duration, envelope fractions, horizon -- v0.3 values


# --------------------------------------------------------------------------------------------- trim and envelope
def trim_level_flight_rho(aircraft, V0: float, rho: float):
    def residual(alpha):
        L = lift_force(V0, alpha, aircraft, rho=rho)
        D = drag_force(V0, alpha, aircraft, rho=rho)
        return L + D * np.tan(alpha) - aircraft.mass * G

    alpha_trim = _bisect_root(residual, -np.radians(TRIM_ALPHA_LOWER_BOUND_DEG), aircraft.alpha_stall)
    D_trim = drag_force(V0, alpha_trim, aircraft, rho=rho)
    throttle_raw = D_trim / (aircraft.thrust_max * np.cos(alpha_trim))
    throttle_trim = min(max(throttle_raw, 0.0), 1.0)
    elevator_trim = aircraft.alpha_stiffness * alpha_trim / aircraft.elevator_effectiveness
    return alpha_trim, throttle_trim, elevator_trim, throttle_raw


def stall_speed_rho(aircraft, cl_max: float, rho: float) -> float:
    return float(np.sqrt(2.0 * aircraft.mass * G / (rho * aircraft.wing_area * cl_max)))


def config_envelope(cfg: dict) -> dict:
    """Aircraft, stall boundary, V_stall, validity envelope, V0 range and control scale for a configuration."""
    ac = make_aircraft(cfg)
    rho = float(cfg["rho"])
    boundary = resolve_stall_boundary(ac)
    v_stall = stall_speed_rho(ac, boundary.cl_max, rho)
    v0_lo, v0_hi = V0_MULT_LO * v_stall, V0_MULT_HI * v_stall
    v0_hi_cap, capped = v0_hi, False
    if trim_level_flight_rho(ac, v0_hi, rho)[3] > 1.0:  # lower the top speed to the fastest trim with throttle <= 1
        lo, hi = v0_lo, v0_hi
        if trim_level_flight_rho(ac, lo, rho)[3] > 1.0:
            raise ValueError(f"{cfg['config_id']}: no trim with throttle <= 1 even at the lowest V0")
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if trim_level_flight_rho(ac, mid, rho)[3] <= 1.0 else (lo, mid)
        v0_hi_cap, capped = lo, True
    base_boundary = resolve_stall_boundary(BASE)
    scale = ((ac.alpha_stiffness / ac.elevator_effectiveness) / (BASE.alpha_stiffness / BASE.elevator_effectiveness)
             * (boundary.alpha_at_cl_peak / base_boundary.alpha_at_cl_peak))
    return {"aircraft": ac, "rho": rho, "boundary": boundary, "v_stall": v_stall,
            "v_floor": GEN.validity_v_floor_fraction_of_vstall * v_stall,
            "gamma_max_rad": float(np.radians(GEN.validity_gamma_max_deg)),
            "v0_lo": v0_lo, "v0_hi": v0_hi_cap, "v0_hi_uncapped": v0_hi, "v0_capped": capped,
            "elevator_scale": float(scale)}


# --------------------------------------------------------------------------------------------- simulation
def simulate_trajectory_rho(trajectory_id: str, aircraft, control_profile: Callable[[float], Controls], V0: float,
                            gamma0: float, alpha0: float, h0: float, q0: float, duration_s: float, dt: float,
                            v_floor: float, gamma_max_rad: float, rho: float) -> TrajectoryResult:
    """Line-for-line copy of trajectory_sim.simulate_trajectory with rho passed to the equations of motion."""
    theta0 = alpha0 + gamma0
    state = np.array([V0, gamma0, theta0, h0, q0], dtype=float)
    n_steps = int(round(duration_s / dt))
    rec = {k: [] for k in ("t", "V", "alpha", "theta", "gamma", "h", "q", "vs", "thrust", "elev", "thr")}

    def rhs(tt, ss):
        return equations_of_motion(tt, ss, control_profile(tt), aircraft, rho=rho)

    termination_reason = TERMINATION_COMPLETED
    for i in range(n_steps + 1):
        t = i * dt
        if not np.all(np.isfinite(state)):
            termination_reason = TERMINATION_NAN_INF
            break
        V, gamma, theta, h, q = state
        if h <= 0:
            termination_reason = TERMINATION_GROUND_CONTACT
            break
        alpha = theta - gamma
        controls = control_profile(t)
        if not (np.isfinite(controls.elevator) and np.isfinite(controls.throttle)):
            termination_reason = TERMINATION_INVALID_CONTROL
            break
        for k, v in zip(rec, (t, V, alpha, theta, gamma, h, q, V * np.sin(gamma), thrust_force(controls.throttle, aircraft),
                              controls.elevator, controls.throttle)):
            rec[k].append(v)
        if V < v_floor:
            termination_reason = TERMINATION_LOW_AIRSPEED
            break
        if abs(gamma) > gamma_max_rad:
            termination_reason = TERMINATION_GAMMA_EXCEEDED
            break
        if i == n_steps:
            break
        state = rk4_step(rhs, t, state, dt)

    a = {k: np.array(v) for k, v in rec.items()}
    return TrajectoryResult(trajectory_id=trajectory_id, t=a["t"], V=a["V"], alpha=a["alpha"], theta=a["theta"],
                            gamma=a["gamma"], altitude=a["h"], pitch_rate=a["q"], vertical_speed=a["vs"],
                            thrust=a["thrust"], elevator=a["elev"], throttle=a["thr"],
                            termination_reason=termination_reason)


def scale_profile(profile: ControlProfile, s: float) -> ControlProfile:
    """Pilot-equivalent scaling (PROTOCOL.md 1.4): elevator pulse magnitudes x s; timing and throttle unchanged."""
    pulses = [Pulse(start=p.start, rise=p.rise, hold=p.hold, fall=p.fall, magnitude=p.magnitude * s)
              for p in profile.elevator_pulses]
    return ControlProfile(elevator_trim=profile.elevator_trim, throttle_trim=profile.throttle_trim,
                          elevator_pulses=pulses, throttle_pulses=list(profile.throttle_pulses))


def build_profile(regime: str, rng, alpha_trim, throttle_trim, elevator_trim, duration_s) -> ControlProfile:
    if regime == "gradual_approach_v3":
        return build_candidate_d_v3_profile(rng, alpha_trim, throttle_trim, elevator_trim, duration_s,
                                            cap_s=TOTAL_DURATION_CAP_S)
    if regime == "normal":
        return build_control_profile(rng, NORMAL_CONTROL_CONFIG, alpha_trim, throttle_trim, elevator_trim, duration_s)
    if regime == "stall":
        return build_control_profile(rng, STALL_CONTROL_CONFIG, alpha_trim, throttle_trim, elevator_trim, duration_s)
    raise ValueError(regime)


def frame_from_result(result: TrajectoryResult, boundary: StallBoundary, dt: float, horizon_s: float) -> pd.DataFrame:
    feats = compute_features_for_trajectory(result, boundary, dt)
    labels, avail = compute_future_stall_label(feats["is_unsafe"], dt, horizon_s)
    return pd.DataFrame({
        "trajectory_id": result.trajectory_id, "time": result.t, "V": result.V, "alpha": result.alpha,
        "theta": result.theta, "gamma": result.gamma, "altitude": result.altitude, "pitch_rate": result.pitch_rate,
        "vertical_speed": result.vertical_speed, "thrust": result.thrust, "elevator": result.elevator,
        "throttle": result.throttle, "dV_dt": feats["dV_dt"], "dalpha_dt": feats["dalpha_dt"],
        "stall_margin": feats["stall_margin"], "is_unsafe": feats["is_unsafe"],
        "future_stall_5s": labels, "future_stall_5s_available": avail,
    })


def regime_list(rng: np.random.Generator) -> List[str]:
    modes = np.array([m for m, n in REGIME_COUNTS.items() for _ in range(n)])
    rng.shuffle(modes)
    return modes.tolist()


def split_assignment(n: int, rng: np.random.Generator) -> List[str]:
    perm = rng.permutation(n)
    n_tr = int(round(SPLIT_FRACTIONS[0] * n)); n_va = int(round(SPLIT_FRACTIONS[1] * n))
    out = np.empty(n, dtype=object)
    out[perm[:n_tr]] = "train"; out[perm[n_tr:n_tr + n_va]] = "val"; out[perm[n_tr + n_va:]] = "test"
    return out.tolist()


def generate_config(cfg: dict, config_index: int, data_seed: int, n_override: Dict[str, int] = None):
    """All trajectories of one configuration. Returns (frames, metadata DataFrame, envelope summary).

    RNG: SeedSequence([data_seed, config_index]) -> one generator used, in order, for the regime shuffle,
    the split assignment, then each trajectory's V0, h0 and control profile (the v0.3 draw order)."""
    env = config_envelope(cfg)
    rng = np.random.default_rng(np.random.SeedSequence([data_seed, config_index]))
    counts = n_override or REGIME_COUNTS
    modes = np.array([m for m, n in counts.items() for _ in range(n)]); rng.shuffle(modes)
    splits = split_assignment(len(modes), rng)
    frames, meta = [], []
    for i, (regime, split) in enumerate(zip(modes.tolist(), splits)):
        tid = f"{cfg['config_id']}_{i:04d}"
        V0 = float(rng.uniform(env["v0_lo"], env["v0_hi"]))
        h0 = float(rng.uniform(GEN.altitude_min, GEN.altitude_max))
        a_tr, thr_tr, el_tr, _ = trim_level_flight_rho(env["aircraft"], V0, env["rho"])
        prof = scale_profile(build_profile(regime, rng, a_tr, thr_tr, el_tr, GEN.duration_s), env["elevator_scale"])
        res = simulate_trajectory_rho(tid, env["aircraft"], prof, V0, 0.0, a_tr, h0, 0.0, GEN.duration_s, GEN.dt,
                                      env["v_floor"], env["gamma_max_rad"], env["rho"])
        fr = frame_from_result(res, env["boundary"], GEN.dt, GEN.labeling_horizon_s)
        frames.append(fr)
        unsafe = fr["is_unsafe"].to_numpy()
        meta.append({"trajectory_id": tid, "config_id": cfg["config_id"], "generation_mode": regime, "split": split,
                     "initial_airspeed": V0, "v0_over_vstall": V0 / env["v_stall"], "initial_altitude": h0,
                     "trim_alpha": a_tr, "trim_throttle": thr_tr, "trim_elevator": el_tr,
                     "maximum_alpha": float(res.alpha.max()) if len(res.alpha) else np.nan,
                     "whether_stall_occurred": bool(unsafe.any()),
                     "time_of_first_stall": float(res.t[np.argmax(unsafe)]) if unsafe.any() else np.nan,
                     "termination_reason": res.termination_reason, "n_steps": len(res.t)})
    summary = {k: v for k, v in env.items() if k not in ("aircraft", "boundary")}
    summary.update({"alpha_at_cl_peak": env["boundary"].alpha_at_cl_peak, "cl_max": env["boundary"].cl_max})
    return frames, pd.DataFrame(meta), summary
