"""Exploratory non-fitting comparison with provisional NASA NACA 2412 curves.

The digitized data are approximate hand-read points from a scanned graph, not
author-supplied numerical observations. Use this for diagnostics only. The
prediction path deliberately calls AeroGuard's canonical lift implementation
so this comparison cannot silently drift from the simulator equation.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from aeroguard.aircraft import Aircraft
from aeroguard.aerodynamics import lift_coefficient

DATA = ROOT / "experiments/physical_validation/data/nasa_cr197497_figure6a_digitized_approx.csv"
OUT = ROOT / "experiments/physical_validation/data/nasa_cr197497_figure6a_preliminary_comparison.json"
DEFAULT_AIRCRAFT = Aircraft()


def aero_guard_cl(alpha_deg):
    """Canonical AeroGuard default lift equation; no parameters are fitted."""
    alpha = np.radians(np.asarray(alpha_deg, dtype=float))
    return np.asarray(lift_coefficient(alpha, DEFAULT_AIRCRAFT), dtype=float)


def main():
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
        "model": "Unmodified canonical AeroGuard generic default lift law via aeroguard.aerodynamics.lift_coefficient; Aircraft() defaults; no fitting.",
        "fitting": "None. The model was not fitted or calibrated to these data.",
        "interpretation": "Exploratory model-form diagnostic only. Generic AeroGuard aircraft parameters are not identified as a NACA 2412 finite wing. Section/aircraft equivalence is not established.",
        "series": results,
    }
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
