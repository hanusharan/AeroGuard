"""Clean-checkout reproduction test for the archived stall-boundary sensitivity summaries."""
import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "stall_boundary_sensitivity_20261111"


def test_stall_boundary_sensitivity_reproduces_archived_summaries():
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "analyze_stall_boundary_sensitivity.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr

    actual = json.loads((OUT / "summary_recomputed.json").read_text())
    archived_factorial = json.loads((OUT / "shape_parameter_factorial_summary.json").read_text())
    archived_oat = list(csv.DictReader((OUT / "one_factor_at_a_time_summary.csv").open()))

    assert abs(actual["baseline"]["alpha_peak_deg"] - 16.06907) < 5e-5
    assert abs(actual["baseline"]["cl_max"] - 1.736234) < 5e-6
    assert abs(actual["baseline"]["alpha_anchor_deg"] - 16.00271) < 5e-5
    assert len(archived_oat) == 5

    for row in archived_oat:
        result = actual["oat"][row["parameter"]]
        comparisons = (
            ("peak_angle_min", "alpha_peak_deg_min"),
            ("peak_angle_max", "alpha_peak_deg_max"),
            ("cl_max_min", "cl_max_min"),
            ("cl_max_max", "cl_max_max"),
        )
        for result_key, archived_key in comparisons:
            assert abs(result[result_key] - float(row[archived_key])) < 5e-5
        assert result["monotonic_all"] is (row["all_monotone"].lower() == "true")

    factorial = actual["factorial"]
    assert factorial["n_cases"] == archived_factorial["n_cases"] == 343
    for key in ("alpha_peak_deg_min", "alpha_peak_deg_max", "cl_max_min", "cl_max_max"):
        assert abs(factorial[key] - archived_factorial[key]) < 5e-5
    assert factorial["monotonic_all"] is True
    assert archived_factorial["monotonic_post_peak_all"] is True
