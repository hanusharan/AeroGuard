"""Exploratory non-fitting comparison with provisional NASA NACA 2412 curves.

The digitized data are approximate hand-read points from a scanned graph, not
author-supplied numerical observations. Use this for diagnostics only.
"""
import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "experiments/physical_validation/data/nasa_cr197497_figure6a_digitized_approx.csv"
OUT = ROOT / "experiments/physical_validation/data/nasa_cr197497_figure6a_preliminary_comparison.json"


def aero_guard_cl(alpha_deg):
    """Current AeroGuard default lift equation, with no parameters fitted."""
    alpha = np.radians(np.asarray(alpha_deg, dtype=float))
    alpha_stall, rate, decay = 0.2793, 25.0, 3.0
    cl0, cl_alpha = 0.2, 5.5
    numerator = 1.0 + np.exp(-rate * (alpha - alpha_stall)) + np.exp(rate * (alpha + alpha_stall))
    denominator = (1.0 + np.exp(-rate * (alpha - alpha_stall))) * (1.0 + np.exp(rate * (alpha + alpha_stall)))
    sigma = numerator / denominator
    cl_linear = cl0 + cl_alpha * alpha
    cl_anchor = cl0 + cl_alpha * alpha_stall
    cl_post = np.sign(alpha) * cl_anchor * np.exp(-decay * np.maximum(np.abs(alpha) - alpha_stall, 0.0))
    return (1.0 - sigma) * cl_linear + sigma * cl_post


with DATA.open(newline="") as handle:
    all_rows = list(csv.DictReader(handle))
if not all_rows:
    raise RuntimeError("No digitized data rows found")

results = {}
for series in sorted({row["series"] for row in all_rows}):
    rows = [row for row in all_rows if row["series"] == series]
    alpha = np.array([float(row["alpha_deg"]) for row in rows])
    observed = np.array([float(row["cl_section"]) for row in rows])
    order = np.argsort(alpha)
    alpha, observed = alpha[order], observed[order]
    predicted = aero_guard_cl(alpha)
    residual = predicted - observed
    peak_index = int(np.argmax(observed))
    results[series] = {
        "n_points": int(len(rows)),
        "reynolds_number": int(rows[0]["reynolds_number"]),
        "alpha_min_deg": float(alpha.min()),
        "alpha_max_deg": float(alpha.max()),
        "visual_digitized_peak_cl": float(observed[peak_index]),
        "visual_digitized_peak_alpha_deg": float(alpha[peak_index]),
        "default_aeroguard_cl_at_digitized_peak_alpha": float(aero_guard_cl([alpha[peak_index]])[0]),
        "indicative_mae_cl": float(np.mean(np.abs(residual))),
        "indicative_rmse_cl": float(np.sqrt(np.mean(residual ** 2))),
        "evidence_status": "approx_visual_only_not_authoritative",
    }

summary = {
    "source": "Seetharam, Rodgers & Wentz, NASA-CR-197497 / AR77-3, Figure 6(a), report page 21",
    "source_url": "https://ntrs.nasa.gov/api/citations/19950002355/downloads/19950002355.pdf",
    "digitization": "Approximate hand-read estimates from scanned curves; not raw wind-tunnel points and not an author-provided numerical table. Second independent digitization pending.",
    "model": "Unmodified AeroGuard generic default lift law: CL0=0.2, CL_alpha=5.5 rad^-1, alpha_stall=0.2793 rad, blend rate=25, post-stall decay=3 rad^-1.",
    "fitting": "None. The model was not fitted or calibrated to these data.",
    "interpretation": "Exploratory model-form diagnostic only. Generic AeroGuard aircraft parameters are not identified as a NACA 2412 finite wing. Section/aircraft equivalence is not established.",
    "series": results,
}
OUT.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
