"""Phase 3 tests: Item 30 - the stall-margin rule is the AoA rule on a shifted, inverted
scale (PROTOCOL.md section 6). Synthetic data and one tracked metadata file only; the
real-data decision count is a G7 step and is NOT performed here.
"""

import json
import os
import sys

import numpy as np
import pytest
from sklearn.metrics import average_precision_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ml.baselines import StallMarginThresholdRule
from phase3 import A_PEAK_RAD, rules


def test_peak_angle_constant_matches_the_tracked_generation_config():
    with open(os.path.join(ROOT, "data", "metadata", "generation_config_v3.json")) as f:
        cfg = json.load(f)
    assert A_PEAK_RAD == cfg["resolved_stall_boundary"]["alpha_at_cl_peak_rad"]


def test_margin_is_peak_minus_alpha_with_the_documented_sign():
    assert rules.stall_margin(np.array([A_PEAK_RAD]))[0] == 0.0
    assert rules.stall_margin(np.array([0.0]))[0] == A_PEAK_RAD
    assert rules.stall_margin(np.array([0.3]))[0] < 0   # past the boundary the signed margin is negative


def test_equivalent_threshold_and_agreement_away_from_the_threshold():
    rng = np.random.default_rng(0)
    alpha = rng.uniform(-0.4, 0.4, 20000)
    tau = 0.21723935451615506
    rep = rules.equivalence_report(alpha, tau)
    assert rep["n_rows"] == 20000 and rep["n_rows_exactly_at_threshold"] == 0
    assert rep["n_disagree"] == 0
    margin = rules.stall_margin(alpha)
    tau_m = rules.equivalent_margin_threshold(tau)
    assert tau_m == A_PEAK_RAD - tau
    assert np.array_equal(rules.margin_rule_predict(margin, tau_m), (alpha > tau).astype(int))


def test_the_two_rules_differ_only_exactly_at_the_threshold_because_the_operators_differ():
    tau = 0.2
    alpha = np.array([np.nextafter(tau, 0.0), tau, np.nextafter(tau, 1.0)])
    rep = rules.equivalence_report(alpha, tau)
    assert rep["n_rows_exactly_at_threshold"] == 1
    assert rep["n_disagree"] == 1 and rep["n_disagree_exactly_at_threshold"] == 1 and rep["n_disagree_elsewhere"] == 0
    aoa = (alpha > tau).astype(int)
    margin_pred = rules.margin_rule_predict(rules.stall_margin(alpha), rules.equivalent_margin_threshold(tau))
    assert aoa.tolist() == [0, 0, 1]
    assert margin_pred[1] == 1  # margin <= tau_m is non-strict, alpha > tau is strict


def test_margin_rule_wrapper_matches_the_existing_class():
    rng = np.random.default_rng(1)
    margin = rng.uniform(-0.2, 0.5, 3000)
    existing = StallMarginThresholdRule()
    existing.threshold_rad = 0.09
    assert np.array_equal(rules.margin_rule_predict(margin, 0.09), existing.predict(margin))
    with pytest.raises(rules.NonFiniteInputError):
        rules.margin_rule_predict(np.array([0.1, np.nan]), 0.09)


def test_threshold_free_metrics_of_alpha_and_negative_margin_agree():
    rng = np.random.default_rng(2)
    alpha = rng.uniform(-0.1, 0.4, 6000)
    y = ((alpha + 0.05 * rng.standard_normal(6000)) > 0.2).astype(int)
    pr_alpha = average_precision_score(y, alpha)
    pr_margin = average_precision_score(y, -rules.stall_margin(alpha))
    assert pr_alpha == pytest.approx(pr_margin, abs=1e-12)  # strictly monotone map; rounding-level ties are measured, not assumed away


def test_equivalence_report_refuses_invalid_alpha():
    with pytest.raises(rules.NonFiniteInputError):
        rules.equivalence_report(np.array([0.1, np.nan]), 0.2)
    with pytest.raises(rules.UnitError):
        rules.equivalence_report(np.array([15.0]), 0.2)
