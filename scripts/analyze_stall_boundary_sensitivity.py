"""Deterministic curve-level sensitivity analysis; does not touch frozen artifacts."""
from __future__ import annotations
import csv, json, math, sys
from dataclasses import asdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from aeroguard.aircraft import Aircraft
from aeroguard.aerodynamics import lift_coefficient
OUT=ROOT/"outputs"/"stall_boundary_sensitivity_20261111"; OUT.mkdir(parents=True,exist_ok=True)
RANGES={"alpha_stall":(math.radians(14),math.radians(18)),"stall_transition_rate":(15.,35.),"post_stall_decay_rate":(2.,4.5),"CL0":(.15,.30),"CL_alpha":(4.5,5.8)}
BASE=Aircraft(); DEG=np.linspace(0.,40.,400001); RAD=np.radians(DEG)
def metrics(params):
 ac=Aircraft(**params); cl=np.asarray([lift_coefficient(float(a),ac) for a in RAD]); i=int(np.argmax(cl)); peak=float(DEG[i]); peakcl=float(cl[i])
 if 0<i<len(cl)-1:
  y0,y1,y2=cl[i-1],cl[i],cl[i+1]; den=y0-2*y1+y2
  if den!=0:
   off=.5*(y0-y2)/den; peak+=float(off*(DEG[1]-DEG[0])); peakcl=float(y1-.25*(y0-y2)*off)
 return {"alpha_peak_deg":peak,"cl_max":peakcl,"alpha_anchor_deg":math.degrees(ac.alpha_stall),"peak_minus_anchor_deg":peak-math.degrees(ac.alpha_stall),"post_peak_monotone_to_40deg":bool(np.all(np.diff(cl[i:])<1e-12)),"cl_30deg":float(lift_coefficient(math.radians(30),ac))}
p0=asdict(BASE); base=metrics(p0); rows=[]
for name,(lo,hi) in RANGES.items():
 for v in np.linspace(lo,hi,9):
  p=dict(p0); p[name]=float(v); m=metrics(p); rows.append({"parameter":name,"parameter_value":float(v),"parameter_low":lo,"parameter_high":hi,**m,"delta_alpha_peak_deg_from_baseline":m["alpha_peak_deg"]-base["alpha_peak_deg"],"delta_cl_max_from_baseline":m["cl_max"]-base["cl_max"]})
with (OUT/"one_factor_at_a_time.csv").open("w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
levels={"alpha_stall":np.linspace(*RANGES["alpha_stall"],7),"stall_transition_rate":np.linspace(*RANGES["stall_transition_rate"],7),"post_stall_decay_rate":np.linspace(*RANGES["post_stall_decay_rate"],7)}; fact=[]
for a in levels["alpha_stall"]:
 for t in levels["stall_transition_rate"]:
  for d in levels["post_stall_decay_rate"]:
   p=dict(p0); p.update(alpha_stall=float(a),stall_transition_rate=float(t),post_stall_decay_rate=float(d)); fact.append({"alpha_stall_deg":math.degrees(float(a)),"stall_transition_rate":float(t),"post_stall_decay_rate":float(d),**metrics(p)})
with (OUT/"shape_parameter_factorial_7x7x7.csv").open("w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(fact[0])); w.writeheader(); w.writerows(fact)
summary={"analysis":"deterministic lift-curve peak sensitivity; OAT plus 7x7x7 shape-parameter factorial","status":"new analysis; not a rerun of Phase 4 and not real-aircraft validation","baseline_parameters":p0,"baseline":base,"parameter_ranges":{k:[float(v[0]),float(v[1])] for k,v in RANGES.items()},"one_factor_at_a_time":{},"shape_factorial":{"n_cases":len(fact),"alpha_peak_deg_min":min(x["alpha_peak_deg"] for x in fact),"alpha_peak_deg_max":max(x["alpha_peak_deg"] for x in fact),"cl_max_min":min(x["cl_max"] for x in fact),"cl_max_max":max(x["cl_max"] for x in fact),"peak_monotone_all":all(x["post_peak_monotone_to_40deg"] for x in fact)},"grid":{"range_deg":[0,40],"spacing_deg":.0001},"limitations":["Ranges are declared in experiments/phase4/PARAMETER_RANGES.md; engineering/model bands, not confidence intervals.","OAT holds all other parameters at v0.3 defaults; does not capture interactions.","Factorial varies alpha_stall, blend rate and post-stall decay only; CL0 and CL_alpha are fixed.","No trajectories were re-simulated, no labels changed, and no ML model evaluated.","No primary experimental lift-curve data or aircraft-specific validation used."]}
for name in RANGES:
 s=[x for x in rows if x["parameter"]==name]; summary["one_factor_at_a_time"][name]={"alpha_peak_deg_min":min(x["alpha_peak_deg"] for x in s),"alpha_peak_deg_max":max(x["alpha_peak_deg"] for x in s),"cl_max_min":min(x["cl_max"] for x in s),"cl_max_max":max(x["cl_max"] for x in s),"peak_monotone_all":all(x["post_peak_monotone_to_40deg"] for x in s)}
(OUT/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
lines=["# Stall-boundary sensitivity analysis — 2026-11-11","","**Status:** New deterministic curve-level analysis. Not real-aircraft validation, not a rerun of Phase 4, and not a change to frozen results.","","## Method","","- Exact Aircraft defaults and lift_coefficient implementation from repository.","- Sweep 0°–40° at 0.0001° spacing with local parabolic interpolation around the peak.","- OAT: nine evenly spaced values across each Phase 4 declared range; remaining parameters at v0.3 defaults.","- Interaction check: 7×7×7 factorial over alpha_stall, stall_transition_rate and post_stall_decay_rate (343 cases); CL0 and CL_alpha fixed.","- Ranges from experiments/phase4/PARAMETER_RANGES.md; modelling bands, not statistical confidence intervals.","","## Baseline",f"- Peak angle: **{base[chr(97)+chr(108)+chr(112)+chr(104)+chr(97)+chr(95)+chr(112)+chr(101)+chr(97)+chr(107)+chr(95)+chr(100)+chr(101)+chr(103)]:.5f}°**",f"- CLmax: **{base[chr(99)+chr(108)+chr(95)+chr(109)+chr(97)+chr(120)]:.6f}**",f"- Configured alpha_stall anchor: **{base[chr(97)+chr(108)+chr(112)+chr(104)+chr(97)+chr(95)+chr(97)+chr(110)+chr(99)+chr(104)+chr(111)+chr(114)+chr(95)+chr(100)+chr(101)+chr(103)]:.5f}°**","","## OAT results","","| Parameter | Range | Peak angle range | CLmax range | Monotonic post-peak in every sample? |","|---|---:|---:|---:|---|"]
for name,(lo,hi) in RANGES.items():
 s=summary["one_factor_at_a_time"][name]; rg=(f"{math.degrees(lo):.1f}–{math.degrees(hi):.1f}°" if name=="alpha_stall" else f"{lo:g}–{hi:g}"); lines.append(f"| {name} | {rg} | {s[chr(97)+chr(108)+chr(112)+chr(104)+chr(97)+chr(95)+chr(112)+chr(101)+chr(97)+chr(107)+chr(95)+chr(100)+chr(101)+chr(103)+chr(95)+chr(109)+chr(105)+chr(110)]:.4f}–{s[chr(97)+chr(108)+chr(112)+chr(104)+chr(97)+chr(95)+chr(112)+chr(101)+chr(97)+chr(107)+chr(95)+chr(100)+chr(101)+chr(103)+chr(95)+chr(109)+chr(97)+chr(120)]:.4f}° | {s[chr(99)+chr(108)+chr(95)+chr(109)+chr(97)+chr(120)+chr(95)+chr(109)+chr(105)+chr(110)]:.5f}–{s[chr(99)+chr(108)+chr(95)+chr(109)+chr(97)+chr(120)+chr(95)+chr(109)+chr(97)+chr(120)]:.5f} | {s[chr(112)+chr(101)+chr(97)+chr(107)+chr(95)+chr(109)+chr(111)+chr(110)+chr(111)+chr(116)+chr(111)+chr(110)+chr(101)+chr(95)+chr(97)+chr(108)+chr(108)]} |")
lines += ["","## Shape-parameter interaction check",f"- Cases: {len(fact)}",f"- Peak-angle range: {summary[chr(115)+chr(104)+chr(97)+chr(112)+chr(101)+chr(95)+chr(102)+chr(97)+chr(99)+chr(116)+chr(111)+chr(114)+chr(105)+chr(97)+chr(108)][chr(97)+chr(108)+chr(112)+chr(104)+chr(97)+chr(95)+chr(112)+chr(101)+chr(97)+chr(107)+chr(95)+chr(100)+chr(101)+chr(103)+chr(95)+chr(109)+chr(105)+chr(110)]:.5f}° to {summary[chr(115)+chr(104)+chr(97)+chr(112)+chr(101)+chr(95)+chr(102)+chr(97)+chr(99)+chr(116)+chr(111)+chr(114)+chr(105)+chr(97)+chr(108)][chr(97)+chr(108)+chr(112)+chr(104)+chr(97)+chr(95)+chr(112)+chr(101)+chr(97)+chr(107)+chr(95)+chr(100)+chr(101)+chr(103)+chr(95)+chr(109)+chr(97)+chr(120)]:.5f}°","", "This measures the mathematical lift curve only. It does not establish empirical correctness of these ranges, validate 16.07° as a real-aircraft stall angle, or show robustness of event-level ML results. No trajectories or frozen models were touched.","","A stronger physical justification needs primary aerodynamic data for a named configuration (with Reynolds/Mach and configuration conditions), followed by fit/comparison of candidate curves.","","## Files","- one_factor_at_a_time.csv — 45 OAT settings.","- shape_parameter_factorial_7x7x7.csv — 343 interaction cases.","- summary.json — machine-readable results.","- scripts/analyze_stall_boundary_sensitivity.py — reproducible script."]
(OUT/"REPORT.md").write_text("\n".join(lines)+"\n")