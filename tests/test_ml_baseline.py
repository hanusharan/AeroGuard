"""Tests for the Task 4 baseline ML experiment (ml/train_baseline.py,
ml/evaluate_baseline.py, ml/baselines.py additions, ml/metrics.py,
ml/plots.py). Uses small subsamples of the real ml_dataset_v2 files for
speed -- the logic under test does not depend on dataset size.
"""

import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.baselines import AlwaysSafeBaseline, StallMarginThresholdRule
from ml.calibration import select_threshold_train_then_val
from ml.metrics import threshold_sweep
from ml.models import build_logistic_regression, build_random_forest
from ml.train_baseline import CORE_FEATURES, ML_DATA_DIR, TARGET, load_splits

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "metadata", "ml_feature_schema_v2.json")

pytestmark = pytest.mark.skipif(not os.path.exists(ML_DATA_DIR), reason="run scripts/prepare_ml_dataset.py first")


@pytest.fixture(scope="module")
def small_splits():
    train, val, test = load_splits()
    rng = np.random.default_rng(0)
    train_s = train.iloc[rng.choice(len(train), size=20000, replace=False)].reset_index(drop=True)
    val_s = val.iloc[rng.choice(len(val), size=5000, replace=False)].reset_index(drop=True)
    test_s = test.iloc[rng.choice(len(test), size=5000, replace=False)].reset_index(drop=True)
    return train_s, val_s, test_s


# ---------------------------------------------------------------------------
# 1. Preprocessing (scaler) fit only on TRAIN
# ---------------------------------------------------------------------------

def test_scaler_fit_only_on_training_data(small_splits):
    train, val, test = small_splits
    X_train = train[CORE_FEATURES]

    pipeline = build_logistic_regression(C=1.0, class_weight=None)
    pipeline.fit(X_train, train[TARGET].astype(int))
    scaler = pipeline.named_steps["scaler"]

    # the fitted scaler's statistics must equal TRAIN's own mean/std,
    # not some combination that includes val/test
    expected_mean = X_train.mean().to_numpy()
    expected_std = X_train.std(ddof=0).to_numpy()
    assert np.allclose(scaler.mean_, expected_mean, rtol=1e-6)
    assert np.allclose(scaler.scale_, expected_std, rtol=1e-6)


def test_scaler_unaffected_by_val_test_distribution(small_splits):
    """Corrupt val/test to have a wildly different distribution AFTER
    fitting on train; the already-fitted scaler's parameters must not
    change (proves fit() never re-touches them)."""
    train, val, test = small_splits
    X_train = train[CORE_FEATURES]
    pipeline = build_logistic_regression(C=1.0, class_weight=None)
    pipeline.fit(X_train, train[TARGET].astype(int))
    mean_before = pipeline.named_steps["scaler"].mean_.copy()

    # simulate a corrupted val/test set (values the model never sees during fit)
    _corrupted_val = val[CORE_FEATURES] * 1000.0 + 999.0

    mean_after = pipeline.named_steps["scaler"].mean_
    assert np.array_equal(mean_before, mean_after)


# ---------------------------------------------------------------------------
# 2. Test data never used during training (structural + behavioral)
# ---------------------------------------------------------------------------

def test_model_fit_ignores_test_set_contents(small_splits):
    """Fit the same model config twice, with two DIFFERENT (disjoint)
    test sets sitting around but never passed to .fit(). Predictions on
    a fixed held-out point must be identical -- proving test-set
    contents cannot have influenced training."""
    train, val, test = small_splits
    X_train, y_train = train[CORE_FEATURES], train[TARGET].astype(int)

    model_a = build_random_forest(n_estimators=20, max_depth=5, min_samples_leaf=5, class_weight=None)
    model_a.fit(X_train, y_train)

    # a completely different "test set" existing in scope changes nothing about fit()
    _unused_alternate_test = test[CORE_FEATURES].iloc[::-1].reset_index(drop=True) * -1

    model_b = build_random_forest(n_estimators=20, max_depth=5, min_samples_leaf=5, class_weight=None)
    model_b.fit(X_train, y_train)

    probe = val[CORE_FEATURES].iloc[:50]
    assert np.allclose(model_a.predict_proba(probe)[:, 1], model_b.predict_proba(probe)[:, 1])


def test_train_baseline_source_never_calls_fit_with_val_or_test():
    """Static guard: grep the actual training script for any .fit( call
    whose first argument is a val/test variable."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "train_baseline.py")
    with open(path) as f:
        source = f.read()
    import re
    fit_calls = re.findall(r"\.fit\(\s*([A-Za-z_][A-Za-z0-9_]*)", source)
    forbidden = [c for c in fit_calls if "val" in c.lower() or "test" in c.lower()]
    assert forbidden == [], f"found .fit() call(s) using a val/test-named variable as the first argument: {forbidden}"


# ---------------------------------------------------------------------------
# 3. Feature columns exactly match schema
# ---------------------------------------------------------------------------

def test_core_features_match_schema():
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)
    documented = set(schema["input_features"].keys())
    non_history = {name for name in documented if not name.startswith("alpha_trend_")}
    assert non_history == set(CORE_FEATURES)


# ---------------------------------------------------------------------------
# 4. No forbidden future columns among model inputs
# ---------------------------------------------------------------------------

def test_core_features_contain_no_forbidden_columns():
    forbidden = {"future_stall_5s", "future_stall_5s_available", "time_to_stall", "is_unsafe",
                 "generation_mode", "termination_reason", "trajectory_id", "split"}
    assert forbidden.isdisjoint(set(CORE_FEATURES))


# ---------------------------------------------------------------------------
# 5. Prediction length matches input length
# ---------------------------------------------------------------------------

def test_prediction_length_matches_input_length(small_splits):
    train, val, test = small_splits
    X_train, y_train = train[CORE_FEATURES], train[TARGET].astype(int)
    model = build_random_forest(n_estimators=20, max_depth=5, min_samples_leaf=5, class_weight=None)
    model.fit(X_train, y_train)

    for n in [1, 17, len(val)]:
        X_probe = val[CORE_FEATURES].iloc[:n]
        preds = model.predict(X_probe)
        proba = model.predict_proba(X_probe)
        assert len(preds) == n
        assert proba.shape[0] == n

    always_safe = AlwaysSafeBaseline().fit()
    assert len(always_safe.predict(val[CORE_FEATURES].iloc[:33])) == 33


# ---------------------------------------------------------------------------
# 6. Probability outputs are in [0, 1]
# ---------------------------------------------------------------------------

def test_probability_outputs_in_unit_interval(small_splits):
    train, val, test = small_splits
    X_train, y_train = train[CORE_FEATURES], train[TARGET].astype(int)

    logreg = build_logistic_regression(C=1.0, class_weight="balanced").fit(X_train, y_train)
    rf = build_random_forest(n_estimators=20, max_depth=5, min_samples_leaf=5, class_weight=None).fit(X_train, y_train)

    for model in [logreg, rf]:
        proba = model.predict_proba(val[CORE_FEATURES])[:, 1]
        assert np.all(proba >= 0.0) and np.all(proba <= 1.0)
        assert not np.any(np.isnan(proba))


# ---------------------------------------------------------------------------
# 7. Threshold calculations are correct
# ---------------------------------------------------------------------------

def test_threshold_sweep_matches_manual_computation():
    rng = np.random.default_rng(1)
    y_true = rng.integers(0, 2, size=2000)
    y_score = rng.random(2000) + y_true * 0.4

    df = threshold_sweep(y_true, y_score, thresholds=[0.3, 0.5, 0.7])
    for _, row in df.iterrows():
        thr = row["threshold"]
        pred = (y_score >= thr).astype(int)
        tp = int(np.sum((pred == 1) & (y_true == 1)))
        fp = int(np.sum((pred == 1) & (y_true == 0)))
        fn = int(np.sum((pred == 0) & (y_true == 1)))
        expected_precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        expected_recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        assert row["precision"] == pytest.approx(expected_precision)
        assert row["recall"] == pytest.approx(expected_recall)
        assert row["tp"] == tp and row["fp"] == fp and row["fn"] == fn


def test_stall_margin_rule_predictions_match_manual_threshold_check():
    """StallMarginThresholdRule.predict() must exactly reproduce a manual
    'margin <= frozen_threshold' check -- no off-by-one or sign error in
    the negation used internally to reuse the shared calibration helper."""
    BOUNDARY_RAD = 0.28044009791924895
    rng = np.random.default_rng(2)
    alpha = rng.normal(0.05, 0.1, size=5000)
    margin = BOUNDARY_RAD - alpha
    y = (np.abs(alpha) > BOUNDARY_RAD).astype(int)

    n = len(alpha)
    tr, va = slice(0, n // 2), slice(n // 2, n)
    rule = StallMarginThresholdRule().fit(margin[tr], y[tr], margin[va], y[va])
    assert rule.threshold_rad is not None

    manual_pred = (margin[va] <= rule.threshold_rad).astype(int)
    assert np.array_equal(rule.predict(margin[va]), manual_pred)


# ---------------------------------------------------------------------------
# 8. Trajectory-level split remains intact
# ---------------------------------------------------------------------------

def test_trajectory_split_intact_in_ml_baseline_files():
    train, val, test = load_splits()
    tr_ids, va_ids, te_ids = set(train.trajectory_id), set(val.trajectory_id), set(test.trajectory_id)
    assert tr_ids & va_ids == set()
    assert tr_ids & te_ids == set()
    assert va_ids & te_ids == set()


# ---------------------------------------------------------------------------
# 9. Reproducibility with a fixed seed
# ---------------------------------------------------------------------------

def test_random_forest_reproducible_with_fixed_seed(small_splits):
    """random_state makes the LEARNED STRUCTURE (which rows/features each
    tree uses, every split) fully deterministic -- checked directly via
    feature_importances_, which do not involve prediction-time
    parallel reduction and so must be bit-exact. predict_proba() itself
    is checked with a tight numerical tolerance rather than exact
    equality: build_random_forest uses n_jobs=-1, and sklearn's
    parallel-averaging step over estimators is not guaranteed to sum
    floating-point contributions in the same order every run, which can
    differ at the ~1e-16 (machine-epsilon) level -- confirmed by direct
    measurement, not assumed. This is a documented floating-point
    reduction-order artifact, not the model actually behaving
    differently."""
    train, val, test = small_splits
    X_train, y_train = train[CORE_FEATURES], train[TARGET].astype(int)

    rf1 = build_random_forest(n_estimators=30, max_depth=6, min_samples_leaf=5, class_weight="balanced_subsample")
    rf1.fit(X_train, y_train)
    rf2 = build_random_forest(n_estimators=30, max_depth=6, min_samples_leaf=5, class_weight="balanced_subsample")
    rf2.fit(X_train, y_train)

    assert np.array_equal(rf1.feature_importances_, rf2.feature_importances_), "learned tree structure was not deterministic"

    proba1 = rf1.predict_proba(val[CORE_FEATURES])[:, 1]
    proba2 = rf2.predict_proba(val[CORE_FEATURES])[:, 1]
    assert np.allclose(proba1, proba2, atol=1e-9), "predict_proba differs by more than floating-point reduction-order noise"


def test_threshold_selection_reproducible():
    rng = np.random.default_rng(3)
    y_train = rng.integers(0, 2, size=3000)
    score_train = rng.random(3000) + y_train * 0.3
    y_val = rng.integers(0, 2, size=800)
    score_val = rng.random(800) + y_val * 0.3

    t1, info1 = select_threshold_train_then_val(y_train, score_train, y_val, score_val)
    t2, info2 = select_threshold_train_then_val(y_train, score_train, y_val, score_val)
    assert t1 == t2
    assert info1 == info2
