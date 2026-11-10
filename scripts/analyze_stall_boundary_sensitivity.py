"""Reproduce AeroGuard static lift-curve peak sensitivity; frozen data untouched."""
import csv, json, math, sys
from dataclasses import asdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from aeroguard.aircraft import Aircraft
from aeroguard.aerodynamics import lift_coefficient
OUT=ROOT/"outputs"/"stall_boundary_sensitivity_20261111"
OUT.mkdir(parents=True,exist_ok=True)
RANGES={"alpha_stall":(math.radians(14),math.radians(18)),"stall_transition_rate":(15.,35.),"post_stall_decay_rate":(2.,4.5),"CL0":(.15,.30),"CL_alpha":(4.5,5.8)}
BASE=Aircraft()
DEG=np.linspace(0.,40.,400001)
RAD=np.radians(DEG)
def curve_peak(parameters):
    aircraft=Aircraft(**parameters)
    # lift_coefficient uses NumPy operations and accepts an AoA vector.
    cl=np.asarray(lift_coefficient(RAD,aircraft),dtype=np.float64)
    if cl.shape != RAD.shape or not np.all(np.isfinite(cl)):
        raise RuntimeError("Lift curve has invalid shape or non-finite values")
    i=int(np.argmax(cl)); angle=float(DEG[i]); peak=float(cl[i])
    if 0<i<len(cl)-1:
        y0,y1,y2=cl[i-1:i+2]; den=y0-2*y1+y2
        if den:
            offset=.5*(y0-y2)/den
            angle+=float(offset*(DEG[1]-DEG[0]))
            peak=float(y1-.25*(y0-y2)*offset)
    return {"alpha_peak_deg":angle,"cl_max":peak,"alpha_anchor_deg":math.degrees(aircraft.alpha_stall),"post_peak_monotone_to_40deg":bool(np.all(np.diff(cl[i:])<1e-12))}
defaults=asdict(BASE); baseline=curve_peak(defaults); rows=[]
for name,(low,high) in RANGES.items():
    for value in np.linspace(low,high,9):
        p=dict(defaults); p[name]=float(value); m=curve_peak(p)
        rows.append({"parameter":name,"parameter_value":float(value),**m,"delta_alpha_peak_deg":m["alpha_peak_deg"]-baseline["alpha_peak_deg"],"delta_cl_max":m["cl_max"]-baseline["cl_max"]})
with (OUT/"one_factor_at_a_time_full.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
shape=[]
for anchor in np.linspace(*RANGES["alpha_stall"],7):
    for rate in np.linspace(*RANGES["stall_transition_rate"],7):
        for decay in np.linspace(*RANGES["post_stall_decay_rate"],7):
            p=dict(defaults); p.update(alpha_stall=float(anchor),stall_transition_rate=float(rate),post_stall_decay_rate=float(decay))
            shape.append({"alpha_stall_deg":math.degrees(float(anchor)),"stall_transition_rate":float(rate),"post_stall_decay_rate":float(decay),**curve_peak(p)})
with (OUT/"shape_parameter_factorial_full.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(shape[0])); w.writeheader(); w.writerows(shape)
summary={"analysis":"static lift-curve peak sensitivity; OAT and 7x7x7 factorial","status":"new mathematical-model analysis, not aircraft validation","baseline":baseline,"parameter_ranges":{k:[float(v[0]),float(v[1])] for k,v in RANGES.items()},"oat":{},"factorial":{"n_cases":len(shape),"alpha_peak_deg_min":min(x["alpha_peak_deg"] for x in shape),"alpha_peak_deg_max":max(x["alpha_peak_deg"] for x in shape),"cl_max_min":min(x["cl_max"] for x in shape),"cl_max_max":max(x["cl_max"] for x in shape),"monotonic_all":all(x["post_peak_monotone_to_40deg"] for x in shape)},"limitations":["Ranges inherited from Phase 4 modelling ranges, not confidence intervals.","OAT varies one parameter at a time; factorial covers only three shape parameters.","No trajectories, labels, models, paper, DOI or frozen results are changed.","No experimental aircraft data are used."]}
for name in RANGES:
    sub=[x for x in rows if x["parameter"]==name]
    summary["oat"][name]={"peak_angle_min":min(x["alpha_peak_deg"] for x in sub),"peak_angle_max":max(x["alpha_peak_deg"] for x in sub),"cl_max_min":min(x["cl_max"] for x in sub),"cl_max_max":max(x["cl_max"] for x in sub),"monotonic_all":all(x["post_peak_monotone_to_40deg"] for x in sub)}
(OUT/"summary_recomputed.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary,indent=2))
