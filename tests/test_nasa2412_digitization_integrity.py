"""Integrity checks for the provisional NASA Figure 6(a) graph readings.

These tests validate file structure and code provenance only. They do not
establish that the hand-read coordinates accurately represent the source plot.
"""
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aeroguard.aircraft import Aircraft
from aeroguard.aerodynamics import lift_coefficient
from experiments.physical_validation.compare_nasa2412_figure6a import aero_guard_cl

DATA = ROOT / "experiments/physical_validation/data/nasa_cr197497_figure6a_digitized_approx.csv"

EXPECTED = {
    "WSU_clean": (13, 2_200_000),
    "WSU_grit": (13, 2_200_000),
    "Ref9_clean": (12, 3_100_000),
    "NACA_grit_Ref9": (10, 5_700_000),
}


def load_rows():
    with DATA.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_provisional_digitization_has_expected_series_and_conditions():
    rows = load_rows()
    assert len(rows) == 48
    assert {row["series"] for row in rows} == set(EXPECTED)

    for name, (expected_count, expected_re) in EXPECTED.items():
        series = [row for row in rows if row["series"] == name]
        assert len(series) == expected_count
        assert {int(row["reynolds_number"]) for row in series} == {expected_re}
        assert {float(row["mach"]) for row in series} == {0.13}
        assert {row["digitization_status"] for row in series} == {"approx_digitized_from_scan"}
        assert len({float(row["alpha_deg"]) for row in series}) == expected_count
        alpha = [float(row["alpha_deg"]) for row in series]
        assert alpha == sorted(alpha)
        assert all(np.isfinite(float(row["cl_section"])) for row in series)
        assert all(float(row["estimated_uncertainty_alpha_deg"]) > 0 for row in series)
        assert all(float(row["estimated_uncertainty_cl"]) > 0 for row in series)


def test_comparison_prediction_is_the_canonical_default_simulator_lift_curve():
    alpha_deg = np.linspace(-8.0, 20.0, 281)
    expected = lift_coefficient(np.radians(alpha_deg), Aircraft())
    actual = aero_guard_cl(alpha_deg)
    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-14)
