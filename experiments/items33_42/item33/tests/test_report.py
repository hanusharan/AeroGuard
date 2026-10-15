"""The report is generated only from a machine-readable bundle and keeps the analysis families apart
(PROTOCOL.md sections 9.5, 10, 13). Synthetic numbers only; nothing here is a research result."""

import copy

import numpy as np
import pytest

from item33 import bootstrap as bs, conditions as cond, report, summary

SEEDS = (11, 12, 13)


def bundle(dry_run=True):
    rng = np.random.default_rng(0)
    traj = np.concatenate([[f"t{i}"] * 50 for i in range(12)])
    y = (rng.random(len(traj)) < 0.3).astype(int)
    scores = {bs.method_key(c, s): y * a + rng.random(len(traj)) for c, a in (("C0", 0.9), ("C1", 0.5)) for s in SEEDS}
    pt = bs.point_estimates(y, scores)
    reps = bs.bootstrap_replicates(traj, y, scores, B=40, seed=1)
    summ = bs.contrast_summary("C0", "C1", SEEDS, pt, reps, bonferroni=True)
    d = [summ["per_seed"][s]["point"] for s in SEEDS]
    b = summ["bootstrap_seed_mean"]; adj = summ["bootstrap_seed_mean_bonferroni"]
    contrasts = [
        {"register_id": "D1", "status": "primary", "summary": summ, "statement": summary.evidence_statement("primary", b["ci_lo"], b["ci_hi"], d, adj["ci_lo"], adj["ci_hi"])},
        {"register_id": "X-a", "status": "exploratory", "summary": summ, "statement": summary.evidence_statement("exploratory", b["ci_lo"], b["ci_hi"], d)},
    ]
    return {
        "run_id": "run_synthetic", "protocol_sha256": "a" * 64, "dry_run": dry_run,
        "population": {"n_rows": len(y), "n_trajectories": 12, "n_positive": int(y.sum()), "n_negative": int(len(y) - y.sum()), "population_id": "pid"},
        "conditions": cond.build_manifest(), "contrasts": contrasts,
        "seed_panels": {"C0": summary.seed_panel({s: pt[f"{bs.method_key('C0', s)}|pr_auc"] for s in SEEDS})},
        "failures": [], "historical": {"E0 stored frozen-model PR-AUC": 0.123456789},
        "regime_sensitivity": {"D1": {"ci_lo": 0.0, "ci_hi": 0.2, "primary_ci_lo": 0.01, "primary_ci_hi": 0.19, "agrees_on_zero_inclusion": True}},
        "reproduction": None, "matched_operating_point": None,
        "masking": [{"label": "M-A-MS1", "pr_auc": 0.5, "delta_vs_unmasked": -0.1}],
    }


def test_the_report_renders_every_number_from_the_bundle():
    b = bundle()
    text = report.render_report(b)
    assert format(b["contrasts"][0]["summary"]["bootstrap_seed_mean"]["point"], ".10g") in text
    assert "0.123456789" in text                                      # historical figure printed exactly as supplied
    assert b["protocol_sha256"] in text and "run_synthetic" in text


def test_a_dry_run_is_labelled_and_a_real_run_is_not():
    assert "DRY RUN ON SYNTHETIC DATA" in report.render_report(bundle(True))
    assert "DRY RUN" not in report.render_report(bundle(False))


def test_the_report_states_the_exposure_and_simulation_limitations():
    text = report.render_report(bundle())
    for phrase in ("regenerated copy", "original v0.3 dataset is absent", "not blind", "not independent replication", "real aircraft",
                   "no meaningful-effect margin", "Five training seeds", "exchangeable"):
        assert phrase.lower() in text.lower()


def test_masking_is_a_separate_section_with_its_own_disclaimer():
    text = report.render_report(bundle())
    i_retrained = text.index("Retrained feature ablation")
    i_masking = text.index("Frozen-model input masking")
    assert i_retrained < i_masking
    assert "analysis family: frozen_model_masking" in text and "does not measure the same quantity" in text
    retrained_part = text[i_retrained:i_masking]
    assert "M-A-MS1" not in retrained_part                              # masking results never appear among retrained results


def test_seed_variability_and_bootstrap_interval_are_reported_on_separate_lines():
    text = report.render_report(bundle())
    assert "Seed variability (descriptive, not an interval)" in text and "Trajectory-bootstrap interval for the seed mean" in text
    assert "never combined into one interval" in text


def test_exploratory_comparisons_are_never_called_demonstrated():
    text = report.render_report(bundle())
    block = text[text.index("### X-a"):]
    block = block[: block.index("**Statement:**") + 200]
    assert "demonstrated" not in block.split("**Statement:**")[1].split("\n")[0]


def test_a_missing_entry_stops_the_report_instead_of_inventing_a_value():
    b = bundle()
    for key in report.REQUIRED_KEYS:
        broken = copy.deepcopy(b); del broken[key]
        with pytest.raises(report.ReportError):
            report.render_report(broken)
    broken = copy.deepcopy(b); del broken["contrasts"][0]["summary"]["bootstrap_seed_mean"]
    with pytest.raises(report.ReportError):
        report.render_report(broken)


def test_a_statement_with_banned_wording_cannot_enter_the_report():
    b = bundle(); b["contrasts"][0]["statement"]["text"] = "This confirmed effect is validated."
    with pytest.raises(ValueError):
        report.render_report(b)


def test_undefined_values_are_printed_as_undefined_never_as_zero():
    assert report.num(None) == "undefined" and report.num(0.0) == "0"
    assert report.num(True) == "True" and report.num(3) == "3"
