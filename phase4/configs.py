"""Item 43: parameter ranges and the fixed configuration set (PROTOCOL.md section 1).

Pure, data-free. A configuration is a dict of the 15 varied parameters in physical
units plus bookkeeping fields. ``make_aircraft`` turns it into an unmodified
``aeroguard.aircraft.Aircraft``; ``rho`` is kept separately because the frozen
engine takes density as an argument of the equations of motion.
"""

from dataclasses import replace
import warnings
from typing import Dict, List

import numpy as np

from aeroguard.aircraft import Aircraft

BASE = Aircraft()
BASE_RHO = 1.225

# name -> (lo, hi, kind). kind "abs": range in physical units; "rel": multiplier of the v0.3 value.
# alpha_stall is given in degrees here and converted to radians in make_aircraft.
RANGES: Dict[str, tuple] = {
    "mass": (900.0, 1400.0, "abs"),
    "wing_area": (14.5, 17.5, "abs"),
    "CL_alpha": (4.5, 5.8, "abs"),
    "alpha_stall_deg": (14.0, 18.0, "abs"),
    "CL0": (0.15, 0.30, "abs"),
    "CD0": (0.025, 0.036, "abs"),
    "k": (0.040, 0.060, "abs"),
    "thrust_max": (2200.0, 3200.0, "abs"),
    "Iyy": (1000.0, 1900.0, "abs"),
    "elevator_effectiveness": (0.75, 1.25, "rel"),
    "pitch_damping": (0.75, 1.25, "rel"),
    "alpha_stiffness": (0.75, 1.25, "rel"),
    "stall_transition_rate": (15.0, 35.0, "abs"),
    "post_stall_decay_rate": (2.0, 4.5, "abs"),
    "rho": (0.905, 1.225, "abs"),
}
PARAMS: List[str] = list(RANGES)
D = len(PARAMS)
CORE_LO, CORE_HI = 0.2, 0.8

SOBOL_SEEDS = {"TRAIN": 20261020, "IDH": 20261021, "OOD": 20261022}
PARTITION_SEEDS = {"P1": 20261031, "P2": 20261032}

OOD_GROUPS = {
    "O01": {"mass": 0.98, "rho": 0.02, "wing_area": 0.02},
    "O02": {"mass": 0.02, "wing_area": 0.98, "rho": 0.98},
    "O03": {"alpha_stall_deg": 0.02, "stall_transition_rate": 0.98, "post_stall_decay_rate": 0.98},
    "O04": {"alpha_stall_deg": 0.98, "stall_transition_rate": 0.02, "post_stall_decay_rate": 0.02},
    "O05": {"Iyy": 0.98, "pitch_damping": 0.02, "elevator_effectiveness": 0.02},
    "O06": "all",
}
OOD_STORIES = {
    "O01": "heavy, high density altitude, small wing",
    "O02": "light, large wing, sea level",
    "O03": "early, sharp stall",
    "O04": "late, soft stall",
    "O05": "sluggish pitch",
    "O06": "everything unfamiliar",
}


def base_value(name: str) -> float:
    if name == "rho":
        return BASE_RHO
    if name == "alpha_stall_deg":
        return float(np.degrees(BASE.alpha_stall))
    return float(getattr(BASE, name))


def u_to_value(name: str, u: float) -> float:
    lo, hi, kind = RANGES[name]
    v = lo + float(u) * (hi - lo)
    return v * base_value(name) if kind == "rel" else v


def value_to_u(name: str, v: float) -> float:
    lo, hi, kind = RANGES[name]
    if kind == "rel":
        v = v / base_value(name)
    return (float(v) - lo) / (hi - lo)


def sobol_core(seed: int, n: int) -> np.ndarray:
    """First n points of a scrambled Sobol sequence in d = 15, mapped into the core box."""
    from scipy.stats import qmc
    with warnings.catch_warnings():  # n is not a power of 2 by design (12, 4, 6 points)
        warnings.simplefilter("ignore", UserWarning)
        pts = qmc.Sobol(d=D, scramble=True, seed=seed).random(n)
    return CORE_LO + pts * (CORE_HI - CORE_LO)


def _config(cid: str, cset: str, u: np.ndarray, story: str = "") -> dict:
    cfg = {"config_id": cid, "set": cset, "story": story}
    for name, ui in zip(PARAMS, u):
        cfg[name] = u_to_value(name, ui)
        cfg[f"u_{name}"] = float(ui)
    return cfg


def baseline_config() -> dict:
    u = np.array([value_to_u(p, base_value(p)) for p in PARAMS])
    cfg = _config("C00", "C00", u, "v0.3 aircraft at sea-level density")
    for p in PARAMS:  # exact v0.3 values, not a round trip through u
        cfg[p] = base_value(p)
    return cfg


def ood_u(core_u: np.ndarray, cid: str) -> np.ndarray:
    u = core_u.copy()
    grp = OOD_GROUPS[cid]
    if grp == "all":
        s = (core_u - CORE_LO) / (CORE_HI - CORE_LO)
        u = np.where(core_u < 0.5, 0.1 * s, 0.9 + 0.1 * s)
    else:
        for name, val in grp.items():
            u[PARAMS.index(name)] = val
    return u


def design() -> List[dict]:
    """The fixed configuration set of PROTOCOL.md section 1.2 (23 configurations)."""
    out = [baseline_config()]
    for i, u in enumerate(sobol_core(SOBOL_SEEDS["TRAIN"], 12)):
        out.append(_config(f"T{i + 1:02d}", "TRAIN", u))
    for i, u in enumerate(sobol_core(SOBOL_SEEDS["IDH"], 4)):
        out.append(_config(f"H{i + 1:02d}", "IDH", u))
    for i, u in enumerate(sobol_core(SOBOL_SEEDS["OOD"], 6)):
        cid = f"O{i + 1:02d}"
        out.append(_config(cid, "OOD", ood_u(u, cid), OOD_STORIES[cid]))
    return out


def u_matrix(cfgs: List[dict]) -> np.ndarray:
    return np.array([[c[f"u_{p}"] for p in PARAMS] for c in cfgs])


def unfamiliarity(cfgs: List[dict], train_ids: List[str]) -> Dict[str, dict]:
    """d_OOD (min Euclidean distance in u-space to a TRAIN configuration) and the
    number of parameters outside the TRAIN configurations' per-parameter range."""
    tr = [c for c in cfgs if c["config_id"] in train_ids]
    U_tr = u_matrix(tr)
    lo, hi = U_tr.min(axis=0), U_tr.max(axis=0)
    out = {}
    for c in cfgs:
        u = u_matrix([c])[0]
        d = float(np.min(np.linalg.norm(U_tr - u, axis=1)))
        n_out = int(np.sum((u < lo - 1e-12) | (u > hi + 1e-12)))
        out[c["config_id"]] = {"d_ood": d, "n_params_outside_train_range": n_out}
    return out


def partition(cfgs: List[dict], name: str) -> Dict[str, List[str]]:
    """Training / ID-holdout assignment. P0 is the designed partition; P1/P2
    re-partition the 16 core-box configurations 12/4 by a seeded permutation."""
    core = [c["config_id"] for c in cfgs if c["set"] in ("TRAIN", "IDH")]
    if name == "P0":
        train = [c["config_id"] for c in cfgs if c["set"] == "TRAIN"]
        idh = [c["config_id"] for c in cfgs if c["set"] == "IDH"]
    else:
        perm = np.random.default_rng(PARTITION_SEEDS[name]).permutation(len(core))
        train = sorted(core[i] for i in perm[:12])
        idh = sorted(core[i] for i in perm[12:])
    ood = [c["config_id"] for c in cfgs if c["set"] == "OOD"]
    return {"TRAIN": train, "IDH": idh, "OOD": ood, "C00": ["C00"]}


def make_aircraft(cfg: dict) -> Aircraft:
    kw = {p: cfg[p] for p in PARAMS if p not in ("rho", "alpha_stall_deg")}
    kw["alpha_stall"] = float(np.radians(cfg["alpha_stall_deg"]))
    return replace(BASE, **kw)


def wing_loading(cfg: dict) -> float:
    return cfg["mass"] * 9.81 / cfg["wing_area"]
