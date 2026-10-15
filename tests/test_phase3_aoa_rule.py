"""Phase 3 tests: the AoA baseline wrappers (Item 28; PROTOCOL.md sections 5.2-5.5).

Synthetic data only. These tests establish implementation behaviour (operator, fail-closed
input handling, units, label timing, absence of any test-set argument). They cannot validate an
aerodynamic assumption.
"""

import ast
import inspect
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aeroguard_dataset.labeling import compute_future_stall_label
from ml.baselines import AoAThresholdRule
from ml.calibration import top_k_thresholds_by_train_f1
from phase3 import DT, HORIZON_STEPS, rules

TAU = 0.21723935451615506  # the stored credibility-v1.1 threshold, used here only as a convenient number


def _fixed_rule(threshold):
    rule = AoAThresholdRule()
    rule.threshold_rad = threshold
    return rule


def test_strict_operator_below_at_and_above_the_threshold():
    alpha = np.array([np.nextafter(TAU, 0.0), TAU, np.nextafter(TAU, 1.0)])
    assert rules.predict_signed(_fixed_rule(TAU), alpha).tolist() == [0, 0, 1]


def test_prediction_equals_a_manual_strict_comparison_on_random_data():
    rng = np.random.default_rng(0)
    alpha = rng.uniform(-0.5, 0.5, 5000)
    assert np.array_equal(rules.predict_signed(_fixed_rule(0.1), alpha), (alpha > 0.1).astype(int))
    assert rules.predict_signed(_fixed_rule(0.1), alpha).dtype.kind == "i"


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_non_finite_alpha_is_refused_never_predicted_safe(bad):
    alpha = np.array([0.1, bad, 0.3])
    with pytest.raises(rules.NonFiniteInputError):
        rules.predict_signed(_fixed_rule(0.2), alpha)
    with pytest.raises(rules.NonFiniteInputError):
        rules.score_signed(alpha)
    with pytest.raises(rules.NonFiniteInputError):
        rules.predict_two_sided(_fixed_rule(0.2), alpha)
    y = np.array([0, 1, 0])
    ok = np.array([0.1, 0.2, 0.3])
    with pytest.raises(rules.NonFiniteInputError):
        rules.fit_signed_aoa(alpha, y, ok, y)
    with pytest.raises(rules.NonFiniteInputError):
        rules.fit_signed_aoa(ok, y, alpha, y)


def test_invalid_labels_and_shapes_are_refused():
    ok = np.linspace(0, 0.3, 50)
    y = (ok > 0.15).astype(int)
    with pytest.raises(rules.InvalidInputError):
        rules.fit_signed_aoa(ok, np.where(y == 1, 2, 0), ok, y)  # not 0/1
    with pytest.raises(rules.NonFiniteInputError):
        rules.fit_signed_aoa(ok, np.where(np.arange(50) == 3, np.nan, y), ok, y)
    with pytest.raises(rules.InvalidInputError):
        rules.fit_signed_aoa(ok, y[:-1], ok, y)
    with pytest.raises(rules.InvalidInputError):
        rules.fit_signed_aoa(ok, np.zeros(50, dtype=int), ok, y)  # one class only
    with pytest.raises(rules.InvalidInputError):
        rules.fit_signed_aoa(ok.reshape(5, 10), y, ok, y)


def test_units_are_radians_and_degree_scale_input_is_refused():
    assert np.degrees(TAU) == pytest.approx(12.4469, abs=1e-4)
    assert np.radians(12.4469) == pytest.approx(TAU, abs=1e-6)
    with pytest.raises(rules.UnitError):
        rules.predict_signed(_fixed_rule(TAU), np.array([12.4469, 15.0]))  # degrees would be silently "above threshold"
    rules.predict_signed(_fixed_rule(TAU), np.array([-3.0, 3.0]))  # +/- pi is the physical bound


def test_future_event_label_timing_is_exclusive_of_the_current_sample():
    n, k = 2000, 1000  # k < n - 500, so the label of row k itself is available
    only_k = np.zeros(n, dtype=bool)
    only_k[k] = True
    label, avail = compute_future_stall_label(only_k, DT, 5.0)
    assert label[k - HORIZON_STEPS:k].tolist() == [1.0] * HORIZON_STEPS   # rows k-500 ... k-1
    assert label[k - HORIZON_STEPS - 1] == 0.0                              # one row earlier: still outside the window
    assert label[k] == 0.0                                                   # the unsafe sample does not label its own row
    assert avail[:n - HORIZON_STEPS].all() and not avail[n - HORIZON_STEPS:].any()


def _no_test_like(names):
    return [n for n in names if "test" in n.lower()]


@pytest.mark.parametrize("fn", [rules.fit_signed_aoa, rules.fit_two_sided_aoa, AoAThresholdRule.fit])
def test_fit_functions_accept_no_test_like_argument_and_no_catch_all(fn):
    params = inspect.signature(fn).parameters
    assert not _no_test_like(params)
    assert all(p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD) for p in params.values())


def test_fit_sources_never_mention_a_test_split():
    for fn in (rules.fit_signed_aoa, rules.fit_two_sided_aoa, rules._fit_on):
        tree = ast.parse(inspect.getsource(fn).lstrip())
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.arg for n in ast.walk(tree) if isinstance(n, ast.arg)}
        assert not _no_test_like(names)


def test_selected_threshold_is_driven_by_validation_not_by_anything_else():
    rng = np.random.default_rng(3)
    a_tr = rng.uniform(-0.1, 0.35, 4000)
    y_tr = ((a_tr + 0.03 * rng.standard_normal(4000)) > 0.2).astype(int)
    candidates = top_k_thresholds_by_train_f1(y_tr, a_tr, 10)
    assert len(set(candidates)) == 10
    a_va = rng.uniform(-0.1, 0.35, 4000)
    # validation labels that make candidate j the best one -> the fit must pick candidate j
    picked = []
    for j in (0, 9):
        y_va = (a_va > candidates[j]).astype(int)
        picked.append(rules.fit_signed_aoa(a_tr, y_tr, a_va, y_va).threshold_rad)
    assert picked == [float(candidates[0]), float(candidates[9])]
    assert picked[0] != picked[1]
    again = rules.fit_signed_aoa(a_tr, y_tr, a_va, (a_va > candidates[0]).astype(int)).threshold_rad
    assert again == picked[0]  # deterministic


def test_two_sided_variant_scores_the_magnitude_and_flags_large_negative_alpha():
    rng = np.random.default_rng(5)
    mag = rng.uniform(0, 0.35, 4000)
    sign = rng.choice([-1.0, 1.0], 4000)
    alpha = mag * sign
    y = (mag > 0.2).astype(int)
    two = rules.fit_two_sided_aoa(alpha, y, alpha, y)
    signed = rules.fit_signed_aoa(alpha, y, alpha, y)
    assert two.threshold_rad == pytest.approx(0.2, abs=0.01)
    probe = np.array([-0.3, 0.3])
    assert rules.predict_two_sided(two, probe).tolist() == [1, 1]
    assert rules.predict_signed(signed, probe)[0] == 0   # the signed rule cannot flag a large negative alpha
    assert np.array_equal(rules.score_two_sided(probe), np.abs(probe))
    assert np.array_equal(rules.score_signed(probe), probe)


def test_rule_summary_records_operator_threshold_and_all_candidates():
    rng = np.random.default_rng(1)
    a = rng.uniform(-0.1, 0.35, 3000)
    y = (a > 0.2).astype(int)
    s = rules.rule_summary(rules.fit_signed_aoa(a, y, a, y))
    assert s["operator"] == "strict >" and s["threshold_deg"] == pytest.approx(np.degrees(s["threshold_rad"]))
    assert len(s["calibration_info"]["candidate_thresholds_rad"]) == 10 and len(s["calibration_info"]["candidate_val_f1"]) == 10
    with pytest.raises(rules.InvalidInputError):
        rules.rule_summary(AoAThresholdRule())  # unfitted
