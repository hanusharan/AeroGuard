"""Regression checks for the offline evidence audit; no generated data needed."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "evidence_audit", ROOT / "experiments/evidence_audit/audit.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def test_identification_bounds():
    result = audit.bounds(67, 57, 54)
    assert result["unknown_first_crossings"] == 10
    assert result["conditional_recall"] == pytest.approx(54 / 57)
    assert result["lower_bound"] == pytest.approx(54 / 67)
    assert result["upper_bound"] == pytest.approx(64 / 67)
    assert audit.bounds(0, 0, 0)["lower_bound"] is None
    assert audit.bounds(4, 0, 0)["upper_bound"] == 1
    with pytest.raises(ValueError):
        audit.bounds(4, 2, 3)


def test_frozen_metadata_reconciliation():
    result = audit.audit(ROOT)
    groups = result["groups"]
    assert sum(g["trajectories"] for g in groups.values()) == 3150
    assert sum(g["rows"] for g in groups.values()) == 5340865
    assert sum(g["usable_rows"] for k, g in groups.items()
               if k.startswith("test/")) == 538034
    assert groups["test/stall"]["excluded_end"] == 8
    assert groups["test/gradual_approach_v3"]["excluded_end"] == 2
    b = result["test_first_event_identification_bounds"]
    assert b["all"]["warned_evaluated_first_crossings"] == 54
    assert b["stall"]["evaluated_first_crossings"] == 17
    assert b["gradual_approach_v3"]["evaluated_first_crossings"] == 40


def test_frozen_input_mutation_rejected(tmp_path):
    path = next(iter(audit.INPUTS))
    target = tmp_path / path
    target.parent.mkdir(parents=True)
    target.write_bytes(b"modified")
    with pytest.raises(ValueError, match="Frozen input mismatch"):
        audit.read_verified(tmp_path, path)


def test_first_event_coverage_reconciles_archived_leads():
    coverage = audit.audit(ROOT)["first_event_coverage"]
    overall = coverage["all"]
    assert overall["median_credited_lead_warned_s"] == pytest.approx(3.15)
    assert overall["coverage_at_least_2s"]["warned_evaluated_first_crossings"] == 30
    assert overall["coverage_at_least_4s"]["warned_evaluated_first_crossings"] == 25
    assert overall["coverage_at_least_2s"]["lower_bound"] == pytest.approx(30 / 67)
    assert overall["coverage_at_least_4s"]["upper_bound"] == pytest.approx(35 / 67)
    assert coverage["stall"]["coverage_at_least_2s"]["conditional_recall"] == 0
    assert coverage["stall"]["median_credited_lead_warned_s"] == pytest.approx(0.66)


@pytest.mark.parametrize("source,mirror", [
    ("README.md", "dashboard/public/docs/AEROGUARD_README.md"),
    ("PROVENANCE.md", "dashboard/public/docs/PROVENANCE.md"),
    ("outputs/final/AEROGUARD_FINAL_RESEARCH_REPORT.md",
     "dashboard/public/docs/AEROGUARD_FINAL_RESEARCH_REPORT.md"),
    ("paper/AeroGuard_Research_Paper.pdf",
     "dashboard/public/paper/AeroGuard_Research_Paper.pdf"),
    ("paper/AeroGuard_Research_Paper.html",
     "dashboard/public/paper/AeroGuard_Research_Paper.html"),
    *[(f"paper/figures/{name}", f"dashboard/public/paper/figures/{name}")
      for name in ("fig1_pipeline.png", "fig2_precursor.png",
                   "fig3_temporal_ml.png", "fig4_generalization.png")],
])
def test_public_research_artifact_mirrors(source, mirror):
    assert (ROOT / source).read_bytes() == (ROOT / mirror).read_bytes()
