"""Items 48-49: JSBSim feasibility checks and cross-simulator trajectories (PROTOCOL.md sections 10-11).

JSBSim is a 6-DOF simulator. To keep the experiment longitudinal, a minimal lateral
hold (aileron on bank angle and roll rate, rudder on sideslip) keeps the wings
near level; it never touches the elevator or throttle. Elevator inputs reuse the
AeroGuard pulse samplers; their summed magnitude (rad, nose-up positive in
AeroGuard) is mapped to JSBSim's normalised elevator command by one gain
(negative command = nose up in JSBSim). Throttle is held at trim.

The stall boundary is the alpha at the maximum of the model's own tabulated
wing-body lift coefficient (no hysteresis column), the same "past the CL(alpha)
peak" definition as AeroGuard. Labels and derived features use the unchanged
AeroGuard functions.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

import aeroguard_dataset.paths  # noqa: F401
from aeroguard_dataset.events import StallBoundary
from aeroguard_dataset.trajectory_sim import (
    TERMINATION_COMPLETED, TERMINATION_GAMMA_EXCEEDED, TERMINATION_GROUND_CONTACT, TERMINATION_LOW_AIRSPEED,
    TERMINATION_NAN_INF, TrajectoryResult,
)

from .sim import V0_MULT_LO, V0_MULT_HI, REGIME_COUNTS, build_profile, frame_from_result, split_assignment

FT, KT = 0.3048, 0.514444
G = 9.80665
TERMINATION_BANK_EXCEEDED = "validity_envelope_bank_exceeded"
CANDIDATES = ("c172p", "c172x", "pa28", "c182", "c310")
BANK_MAX_DEG = 30.0
DT = 0.01
DURATION_S = 20.0
ALT_RANGE_M = (500.0, 2000.0)
LATERAL_GAINS = {"k_phi": 4.0, "k_p": 1.0, "k_beta": 3.0}


def jsbsim_root() -> Path:
    import jsbsim
    return Path(jsbsim.get_default_root_dir())


def new_fdm(model: str):
    import jsbsim
    fdm = jsbsim.FGFDMExec(str(jsbsim_root()))
    fdm.set_debug_level(0)
    fdm.load_model(model)
    fdm.set_dt(DT)
    return fdm


# ----------------------------------------------------------------------------------------------- F1: lift table
def lift_table(model: str) -> Optional[Dict[str, np.ndarray]]:
    """The alpha-indexed wing-body lift table of a model (first column = no stall hysteresis), or None."""
    root = ET.parse(jsbsim_root() / "aircraft" / model / f"{model}.xml").getroot()
    for fn in root.iter("function"):
        name = fn.get("name", "")
        if not re.search(r"aero/coefficient/(CLwbh|CLalpha|CLo)$", name):
            continue
        for tab in fn.iter("table"):
            ivs = [iv.text.strip() for iv in tab.findall("independentVar")]
            if not ivs or ivs[0] != "aero/alpha-rad":
                continue
            rows = [r.split() for r in tab.find("tableData").text.strip().splitlines() if r.strip()]
            if len(ivs) == 2:   # first line is the column header (hysteresis values)
                rows = rows[1:]
            data = np.array([[float(x) for x in r] for r in rows])
            return {"function": name, "alpha": data[:, 0], "cl": data[:, 1], "two_d": len(ivs) == 2}
    return None


def f1_lift_peak(model: str) -> Dict[str, object]:
    t = lift_table(model)
    if t is None:
        return {"pass": False, "reason": "no alpha-indexed lift table"}
    i = int(np.argmax(t["cl"]))
    interior = 0 < i < len(t["cl"]) - 1
    return {"pass": bool(interior), "function": t["function"], "alpha_peak_rad": float(t["alpha"][i]),
            "cl_max_table": float(t["cl"][i]), "alpha_range_rad": [float(t["alpha"][0]), float(t["alpha"][-1])],
            "reason": "peak strictly inside the table" if interior else "maximum at a table edge (no post-stall data)"}


# ----------------------------------------------------------------------------------------------- trim and run
def init_trim(fdm, v_kts: float, h_m: float) -> Dict[str, float]:
    fdm["ic/h-sl-ft"] = h_m / FT
    fdm["ic/vt-kts"] = v_kts
    fdm["ic/gamma-deg"] = 0.0
    fdm["ic/psi-true-deg"] = 0.0
    fdm["ic/phi-deg"] = 0.0
    fdm.run_ic()
    fdm["propulsion/set-running"] = -1
    fdm["fcs/mixture-cmd-norm"] = 1.0
    fdm["fcs/throttle-cmd-norm"] = 0.6
    fdm["fcs/elevator-cmd-norm"] = 0.0
    fdm.run()
    fdm["simulation/do_simple_trim"] = 1   # raises if the trim does not converge
    return {"alpha": fdm["aero/alpha-rad"], "throttle": fdm["fcs/throttle-cmd-norm"], "pitch_trim": fdm["fcs/pitch-trim-cmd-norm"]}


def try_trim(fdm, v_kts, h_m) -> Optional[Dict[str, float]]:
    try:
        tr = init_trim(fdm, v_kts, h_m)
    except Exception:  # JSBSim raises TrimFailureException
        return None
    return tr if tr["throttle"] <= 1.0 + 1e-9 else None


def stall_speed(fdm, alpha_peak: float, h_m: float) -> float:
    """1 g stall speed from the table CLmax, the model's weight, wing area and density at h_m (after an IC at h_m)."""
    cl = lift_table_cached(fdm.get_model_name())
    clmax = float(np.max(cl["cl"]))
    fdm["ic/h-sl-ft"] = h_m / FT; fdm["ic/vt-kts"] = 80.0; fdm.run_ic()
    w = fdm["inertia/weight-lbs"] * 4.4482216
    rho = fdm["atmosphere/rho-slugs_ft3"] * 515.378818
    s = fdm["metrics/Sw-sqft"] * FT ** 2
    return float(np.sqrt(2 * w / (rho * s * clmax)))


_LT = {}


def lift_table_cached(model):
    if model not in _LT:
        _LT[model] = lift_table(model)
    return _LT[model]


def run_trajectory(fdm, tid: str, elevator_fn, throttle: float, boundary: StallBoundary, v_floor: float) -> TrajectoryResult:
    """Run from the current (trimmed) state for DURATION_S with the elevator command elevator_fn(t) (normalised)."""
    gmax = np.radians(45.0); bmax = np.radians(BANK_MAX_DEG)
    rec = {k: [] for k in ("t", "V", "alpha", "theta", "gamma", "h", "q", "vs", "elev", "thr")}
    reason = TERMINATION_COMPLETED
    n = int(round(DURATION_S / DT))
    for i in range(n + 1):
        t = i * DT
        V = fdm["velocities/vt-fps"] * FT
        alpha = fdm["aero/alpha-rad"]; theta = fdm["attitude/theta-rad"]; gamma = fdm["flight-path/gamma-rad"]
        h = fdm["position/h-agl-ft"] * FT; q = fdm["velocities/q-rad_sec"]; phi = fdm["attitude/phi-rad"]
        if not np.all(np.isfinite([V, alpha, theta, gamma, h, q])):
            reason = TERMINATION_NAN_INF; break
        if h <= 0:
            reason = TERMINATION_GROUND_CONTACT; break
        cmd = float(np.clip(elevator_fn(t), -1.0, 1.0))
        for k, v in zip(rec, (t, V, alpha, theta, gamma, h, q, -fdm["velocities/v-down-fps"] * FT,
                              -fdm["fcs/elevator-pos-rad"], throttle)):
            rec[k].append(v)
        if V < v_floor:
            reason = TERMINATION_LOW_AIRSPEED; break
        if abs(gamma) > gmax:
            reason = TERMINATION_GAMMA_EXCEEDED; break
        if abs(phi) > bmax:
            reason = TERMINATION_BANK_EXCEEDED; break
        if i == n:
            break
        fdm["fcs/elevator-cmd-norm"] = cmd
        fdm["fcs/throttle-cmd-norm"] = throttle
        p = fdm["velocities/p-rad_sec"]; beta = fdm["aero/beta-rad"]
        fdm["fcs/aileron-cmd-norm"] = float(np.clip(-(LATERAL_GAINS["k_phi"] * phi + LATERAL_GAINS["k_p"] * p), -1, 1))
        fdm["fcs/rudder-cmd-norm"] = float(np.clip(LATERAL_GAINS["k_beta"] * beta, -1, 1))
        fdm.run()
    a = {k: np.array(v) for k, v in rec.items()}
    return TrajectoryResult(trajectory_id=tid, t=a["t"], V=a["V"], alpha=a["alpha"], theta=a["theta"], gamma=a["gamma"],
                            altitude=a["h"], pitch_rate=a["q"], vertical_speed=a["vs"], thrust=np.full(len(a["t"]), np.nan),
                            elevator=a["elev"], throttle=a["thr"], termination_reason=reason)


# P4-D2: physically derived elevator mapping (replaces the tuned single gain of PROTOCOL.md 11).
# AeroGuard static AoA response per rad of elevator: elevator_effectiveness / alpha_stiffness = 3.2.
# c172p static response: |Cmde / Cmalpha| = 1.122 / 1.8 (aero/coefficient/Cmde, Cmalpha; propwash factor ignored).
# c172p elevator travel: -28 deg (cmd -1, nose up) to +23 deg (cmd +1, nose down), zero-centred scaling.
AG_ALPHA_PER_ELEV = BASE_ALPHA_PER_ELEV = 3.2e4 / 1.0e4
C172P_ALPHA_PER_ELEV = 1.122 / 1.8
UP_TRAVEL_RAD, DOWN_TRAVEL_RAD = np.radians(28.0), np.radians(23.0)


def ag_to_jsbsim_cmd(ag_elev_rad: float) -> float:
    """AeroGuard elevator increment (rad, nose-up positive) -> c172p normalised command with the same static AoA change."""
    d_rad = ag_elev_rad * AG_ALPHA_PER_ELEV / C172P_ALPHA_PER_ELEV   # equivalent c172p deflection magnitude, nose-up positive
    cmd = -d_rad / UP_TRAVEL_RAD if d_rad >= 0 else -d_rad / DOWN_TRAVEL_RAD
    return float(np.clip(cmd, -1.0, 1.0))


def elevator_command(profile, gain: float = 1.0):
    """gain is kept only for the earlier pilot record; the P4-D2 mapping uses gain = 1."""
    return lambda t: ag_to_jsbsim_cmd(gain * sum(p.value_at(t) for p in profile.elevator_pulses))


# ----------------------------------------------------------------------------------------------- datasets
def max_trim_speed_kts(fdm, h_m: float, lo_kts: float, hi_kts: float) -> float:
    if try_trim(fdm, hi_kts, h_m) is not None:
        return hi_kts
    for _ in range(25):
        mid = 0.5 * (lo_kts + hi_kts)
        lo_kts, hi_kts = (mid, hi_kts) if try_trim(fdm, mid, h_m) is not None else (lo_kts, mid)
    return lo_kts


def generate(model: str, data_seed: int, gain: float, counts: Dict[str, int] = None, with_splits: bool = True):
    """JSBSim trajectories with AeroGuard regimes. Returns (frames, metadata, envelope)."""
    counts = counts or REGIME_COUNTS
    fdm = new_fdm(model)
    f1 = f1_lift_peak(model)
    boundary = StallBoundary(alpha_at_cl_peak=f1["alpha_peak_rad"], cl_max=f1["cl_max_table"])
    h_mid = float(np.mean(ALT_RANGE_M))
    vs = stall_speed(fdm, boundary.alpha_at_cl_peak, h_mid)
    v_lo, v_hi = V0_MULT_LO * vs, V0_MULT_HI * vs
    v_hi_cap = min(max_trim_speed_kts(fdm, h, v_lo / KT, v_hi / KT) for h in ALT_RANGE_M) * KT  # P4-D1: cap at every altitude
    rng = np.random.default_rng(np.random.SeedSequence([data_seed, 999]))
    modes = np.array([m for m, n in counts.items() for _ in range(n)]); rng.shuffle(modes)
    splits = split_assignment(len(modes), rng) if with_splits else ["test"] * len(modes)
    frames, meta = [], []
    for i, (regime, split) in enumerate(zip(modes.tolist(), splits)):
        tid = f"J_{model}_{i:04d}"
        V0 = float(rng.uniform(v_lo, v_hi_cap)); h0 = float(rng.uniform(*ALT_RANGE_M))
        prof = build_profile(regime, rng, 0.0, 0.0, 0.0, DURATION_S)
        fdm = new_fdm(model)  # fresh instance per trajectory: a reused instance can fail later trims (harness bug, P4-D3)
        tr = try_trim(fdm, V0 / KT, h0)
        if tr is None:
            meta.append({"trajectory_id": tid, "generation_mode": regime, "split": split, "initial_airspeed": V0,
                         "termination_reason": "trim_failed", "n_steps": 0, "whether_stall_occurred": False})
            continue
        res = run_trajectory(fdm, tid, elevator_command(prof, gain), tr["throttle"], boundary, 0.5 * vs)
        fr = frame_from_result(res, boundary, DT, 5.0)
        frames.append(fr)
        u = fr["is_unsafe"].to_numpy()
        meta.append({"trajectory_id": tid, "generation_mode": regime, "split": split, "initial_airspeed": V0,
                     "v0_over_vstall": V0 / vs, "initial_altitude": h0, "trim_alpha": tr["alpha"], "trim_throttle": tr["throttle"],
                     "maximum_alpha": float(res.alpha.max()) if len(res.alpha) else np.nan,
                     "whether_stall_occurred": bool(u.any()), "termination_reason": res.termination_reason,
                     "n_steps": len(res.t)})
    env = {"model": model, "alpha_at_cl_peak": boundary.alpha_at_cl_peak, "cl_max_table": boundary.cl_max,
           "v_stall_m_s_at_mid_altitude": vs, "v0_lo": v_lo, "v0_hi_uncapped": v_hi, "v0_hi": v_hi_cap, "gain": gain,
           "lateral_gains": LATERAL_GAINS, "bank_max_deg": BANK_MAX_DEG}
    return frames, pd.DataFrame(meta), env


# ----------------------------------------------------------------------------------------------- feasibility
def feasibility(model: str, n_probe: int = 6) -> Dict[str, object]:
    out = {"model": model, "F1": f1_lift_peak(model)}
    if not out["F1"]["pass"]:
        out["suitable"] = False
        return out
    fdm = new_fdm(model)
    a_pk = out["F1"]["alpha_peak_rad"]
    vs = stall_speed(fdm, a_pk, 1250.0)
    speeds = np.linspace(1.3, 2.0, n_probe) * vs
    ok = [try_trim(fdm, v / KT, 1250.0) is not None for v in speeds]
    out["F2"] = {"pass": bool(all(ok)), "v_stall_m_s": vs, "probe_speeds_m_s": speeds.tolist(), "trim_ok": ok}
    # F3: a 6 s ramp to full nose-up command from trim at 1.6 V_stall, lateral hold on.
    f3 = {"pass": False}
    if try_trim(fdm, 1.6 * vs / KT, 1250.0) is not None:
        res = run_trajectory(fdm, "probe", lambda t: -min(max((t - 1.0) / 6.0, 0.0), 1.0),
                             fdm["fcs/throttle-cmd-norm"], StallBoundary(a_pk, out["F1"]["cl_max_table"]), 0.5 * vs)
        crossed = bool(np.any(np.abs(res.alpha) > a_pk))
        f3 = {"pass": crossed and res.termination_reason != TERMINATION_NAN_INF, "max_alpha_rad": float(res.alpha.max()),
              "termination_reason": res.termination_reason, "crossed": crossed,
              "max_abs_bank_deg_before_end": None, "n_steps": len(res.t)}
    out["F3"] = f3
    props = ("velocities/vt-fps", "aero/alpha-rad", "attitude/theta-rad", "flight-path/gamma-rad", "position/h-agl-ft",
             "velocities/q-rad_sec", "fcs/elevator-pos-rad", "attitude/phi-rad", "aero/beta-rad")
    have = []
    for p in props:
        try:
            fdm[p]; have.append(p)
        except Exception:
            pass
    out["F4"] = {"pass": len(have) == len(props), "properties": have,
                 "mapping": {"V": "velocities/vt-fps x 0.3048 (true airspeed, no wind)", "alpha": "aero/alpha-rad",
                             "theta": "attitude/theta-rad", "gamma": "flight-path/gamma-rad",
                             "altitude": "position/h-agl-ft x 0.3048", "pitch_rate": "velocities/q-rad_sec (body axis)",
                             "elevator": "-fcs/elevator-pos-rad (sign flipped: AeroGuard positive = nose up); not a model input",
                             "throttle": "fcs/throttle-cmd-norm; not a model input"}}
    out["suitable"] = all(out[k]["pass"] for k in ("F1", "F2", "F3", "F4"))
    return out
