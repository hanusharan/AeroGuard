"""Item 50: compare AeroGuard v0.3 aerodynamics with the reference values in
experiments/phase4/published_reference.json over the protocol's fixed range (PROTOCOL.md section 12).

usage: python scripts/phase4_item50.py <out_json>
"""
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import aeroguard_dataset.paths  # noqa: E402,F401
from aeroguard.aerodynamics import lift_coefficient  # noqa: E402
from aeroguard.aircraft import Aircraft  # noqa: E402
from phase4.jsbsim_sim import lift_table  # noqa: E402
from validate_physics import cl_max_of  # noqa: E402

ac = Aircraft()
clmax, a_pk = cl_max_of(ac)
G, RHO, KT, LB = 9.80665, 1.225, 0.514444, 0.453592
BANDS = {"slope": 0.15, "clmax": 0.10, "alpha_peak_deg": 2.0, "stall_speed": 0.10}

# Q1 slope over alpha 0-12 deg (both curves linear there), least squares
al = np.radians(np.linspace(0, 12, 25))
ag_cl = np.array([lift_coefficient(a, ac) for a in al])
t = lift_table("c172p")
js_cl = np.interp(al, t["alpha"], t["cl"])
ag_slope, js_slope = np.polyfit(al, ag_cl, 1)[0], np.polyfit(al, js_cl, 1)[0]
# Q3 stall speed at the C172R weight, sea level, wing area 16.2 m^2
m = 2450 * LB
vs_ag = np.sqrt(2 * m * G / (RHO * ac.wing_area * clmax))
vs_ref = 51 * KT  # KCAS ~ EAS at low altitude, so compared at sea-level density
cl_implied = 2 * m * G / (RHO * vs_ref ** 2 * ac.wing_area)

def cmp(name, ag, ref, kind, level):
    d = (ag - ref) if kind == "abs" else (ag - ref) / ref
    band = BANDS[name.split("|")[0]]
    verdict = ("within band" if abs(d) <= band else "outside band") if level != "U" else "not judged (U)"
    return {"quantity": name, "aeroguard": float(ag), "reference": float(ref), "difference": float(d),
            "difference_kind": "absolute" if kind == "abs" else "relative", "band": band, "reference_level": level, "result": verdict}

out = {"note": "References are J (JSBSim model file, not experimental) or S (secondary). No P-level (primary, checked) reference "
               "was available, so no result here is agreement or disagreement with experimental evidence.",
       "comparisons": [
           cmp("slope|c172p_CLwbh_0-12deg", ag_slope, js_slope, "rel", "J"),
           cmp("clmax|c172p_CLwbh", clmax, t["cl"].max(), "rel", "J"),
           cmp("alpha_peak_deg|c172p_CLwbh", np.degrees(a_pk), np.degrees(t["alpha"][np.argmax(t["cl"])]), "abs", "J"),
           cmp("clmax|implied_by_C172R_51KCAS_2450lb", clmax, cl_implied, "rel", "S"),
           cmp("stall_speed|C172R_51KCAS_2450lb", vs_ag, vs_ref, "rel", "S")],
       "aeroguard_stall_speed_at_1111kg_m_s": float(vs_ag), "reference_stall_speed_m_s": float(vs_ref),
       "caveats": ["The POH figure is a whole-aircraft, trimmed, power-off value; AeroGuard CLmax is a wing-body model value.",
                   "KCAS is treated as equivalent airspeed at sea level.",
                   "The c172p table is itself a community approximation, not measured data."]}
json.dump(out, open(sys.argv[1], "w"), indent=1)
for c in out["comparisons"]:
    print(c)
print(out["aeroguard_stall_speed_at_1111kg_m_s"])
