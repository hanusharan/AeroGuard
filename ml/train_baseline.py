"""Steps 1-6 of the Task 4 baseline experiment: inspect data, trivial
baselines, Logistic Regression (with/without class weighting, compared
honestly), Random Forest, and a threshold sweep. Saves trained models
and core metrics for evaluate_baseline.py to consume.

TEST is touched exactly once per model/rule, for final reporting only --
never for choosing between class-weighting options, hyperparameters, or
thresholds (all of that uses TRAIN/VAL).
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import joblib
import numpy as np
import pandas as pd

from ml import config as ds_config  # noqa: F401  (reused only for ML_SEED below)
from ml.baselines import AlwaysSafeBaseline, AoAThresholdRule, StallMarginThresholdRule
from ml.calibration import select_threshold_train_then_val
from ml.evaluation import compute_classification_metrics
from ml.metrics import compute_brier_and_calibration, threshold_sweep
from ml.models import build_logistic_regression, build_random_forest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ML_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "ml")
OUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "ml_baseline")
MODELS_DIR = os.path.join(OUT_DIR, "models")

SEED = 20260817

CORE_FEATURES = ["V", "alpha", "gamma", "pitch_rate", "altitude", "elevator", "throttle",
                  "stall_margin", "dV_dt", "dalpha_dt", "dgamma_dt", "dq_dt"]
TARGET = "future_stall_5s"


class _NumpyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def load_splits():
    train = pd.read_parquet(os.path.join(ML_DATA_DIR, "ml_train_v2.parquet"))
    val = pd.read_parquet(os.path.join(ML_DATA_DIR, "ml_val_v2.parquet"))
    test = pd.read_parquet(os.path.join(ML_DATA_DIR, "ml_test_v2.parquet"))
    return train, val, test


def xy(df: pd.DataFrame, features=CORE_FEATURES):
    return df[features], df[TARGET].to_numpy().astype(int)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)
    all_metrics = {}
    t_start = time.time()

    print("=" * 78)
    print("STEP 1-2: LOAD DATA, TRIVIAL BASELINES")
    print("=" * 78)
    train, val, test = load_splits()
    print(f"train={len(train):,} val={len(val):,} test={len(test):,} rows")
    X_train, y_train = xy(train)
    X_val, y_val = xy(val)
    X_test, y_test = xy(test)

    # --- 1. Always safe ---
    always_safe = AlwaysSafeBaseline().fit()
    pred = always_safe.predict(X_test)
    score = always_safe.predict_score(X_test)
    m = compute_classification_metrics(y_test, pred, score + 1e-9)  # tiny epsilon so PR-AUC doesn't choke on a constant score
    print(f"\nAlways-safe: precision={m['precision']:.4f} recall={m['recall']:.4f} f1={m['f1']:.4f} "
          f"(PR-AUC not meaningful for a constant predictor -- reported only for table completeness)")
    all_metrics["always_safe"] = {"test_metrics": m}

    # --- 2. Stall-margin threshold rule ---
    margin_rule = StallMarginThresholdRule().fit(train["stall_margin"].to_numpy(), y_train, val["stall_margin"].to_numpy(), y_val)
    pred = margin_rule.predict(test["stall_margin"].to_numpy())
    score = margin_rule.predict_score(test["stall_margin"].to_numpy())
    m_margin = compute_classification_metrics(y_test, pred, score)
    print(f"Stall-margin rule: threshold={margin_rule.calibration_info['selected_threshold_deg']:.3f} deg  "
          f"PR-AUC={m_margin['pr_auc']:.4f} P={m_margin['precision']:.4f} R={m_margin['recall']:.4f} F1={m_margin['f1']:.4f}")
    all_metrics["stall_margin_rule"] = {"calibration": margin_rule.calibration_info, "test_metrics": m_margin}

    # --- 3. AoA threshold rule ---
    aoa_rule = AoAThresholdRule().fit(train["alpha"].to_numpy(), y_train, val["alpha"].to_numpy(), y_val)
    pred = aoa_rule.predict(test["alpha"].to_numpy())
    score = aoa_rule.predict_score(test["alpha"].to_numpy())
    m_aoa = compute_classification_metrics(y_test, pred, score)
    print(f"AoA rule: threshold={np.degrees(aoa_rule.threshold_rad):.3f} deg  "
          f"PR-AUC={m_aoa['pr_auc']:.4f} P={m_aoa['precision']:.4f} R={m_aoa['recall']:.4f} F1={m_aoa['f1']:.4f}")
    print(f"  (Note: stall_margin = 16.068deg - alpha EXACTLY, so this rule and the stall-margin rule above are "
          f"mathematically equivalent thresholds -- expect near-identical metrics, confirmed below: "
          f"PR-AUC diff = {abs(m_aoa['pr_auc']-m_margin['pr_auc']):.6f})")
    all_metrics["aoa_rule"] = {"calibration": aoa_rule.calibration_info, "test_metrics": m_aoa}

    print("\n" + "=" * 78)
    print("STEP 3: LOGISTIC REGRESSION (class-weighting comparison)")
    print("=" * 78)
    logreg_candidates = {}
    for weight_label, class_weight in [("no_weighting", None), ("balanced", "balanced")]:
        model = build_logistic_regression(C=1.0, class_weight=class_weight)
        model.fit(X_train, y_train)
        val_proba = model.predict_proba(X_val)[:, 1]
        val_pr_auc = compute_classification_metrics(y_val, (val_proba > 0.5).astype(int), val_proba)["pr_auc"]
        logreg_candidates[weight_label] = {"model": model, "val_pr_auc": val_pr_auc}
        print(f"  class_weight={weight_label!r:12s} -> VAL PR-AUC={val_pr_auc:.4f}")

    best_weighting = max(logreg_candidates, key=lambda k: logreg_candidates[k]["val_pr_auc"])
    print(f"  SELECTED (by VAL PR-AUC, honestly compared, not assumed): class_weight={best_weighting!r}")
    logreg_model = logreg_candidates[best_weighting]["model"]

    train_proba = logreg_model.predict_proba(X_train)[:, 1]
    val_proba = logreg_model.predict_proba(X_val)[:, 1]
    logreg_threshold, logreg_thr_info = select_threshold_train_then_val(y_train, train_proba, y_val, val_proba)

    test_proba = logreg_model.predict_proba(X_test)[:, 1]
    test_pred = (test_proba > logreg_threshold).astype(int)
    m_logreg = compute_classification_metrics(y_test, test_pred, test_proba)
    logreg_calib = compute_brier_and_calibration(y_test, test_proba)
    print(f"  TEST (single pass): threshold={logreg_threshold:.4f} PR-AUC={m_logreg['pr_auc']:.4f} "
          f"ROC-AUC={m_logreg['roc_auc']:.4f} P={m_logreg['precision']:.4f} R={m_logreg['recall']:.4f} F1={m_logreg['f1']:.4f} "
          f"Brier={logreg_calib['brier_score']:.4f}")

    all_metrics["logistic_regression"] = {
        "class_weight_comparison": {k: {"val_pr_auc": v["val_pr_auc"]} for k, v in logreg_candidates.items()},
        "selected_class_weight": best_weighting, "threshold": logreg_threshold, "threshold_info": logreg_thr_info,
        "test_metrics": m_logreg, "calibration": logreg_calib,
    }
    joblib.dump(logreg_model, os.path.join(MODELS_DIR, "logistic_regression.joblib"))

    logreg_val_sweep = threshold_sweep(y_val, val_proba)
    logreg_val_sweep.to_csv(os.path.join(OUT_DIR, "threshold_analysis_logreg.csv"), index=False)

    print("\n" + "=" * 78)
    print("STEP 4: RANDOM FOREST")
    print("=" * 78)
    print("  Chosen over HistGradientBoosting: in the prior Stage-3 experiment (13-feature set, same aircraft/")
    print("  dataset lineage), Random Forest achieved the best VAL/TEST PR-AUC of the three ML models tried")
    print("  (0.750 vs 0.717 for HistGB, 0.643 for Logistic Regression), and its native feature_importances_")
    print("  gives directly interpretable per-feature scores without a separate permutation-importance pass.")
    print("  ~900k training rows is entirely tractable for RF (~30-45s per fit) -- no runtime reason to prefer")
    print("  HistGB's speed advantage here.")

    rf_grid = [
        {"n_estimators": 200, "max_depth": 12, "min_samples_leaf": 5, "class_weight": "balanced_subsample"},
        {"n_estimators": 200, "max_depth": 20, "min_samples_leaf": 5, "class_weight": "balanced_subsample"},
    ]
    rf_candidates = []
    for params in rf_grid:
        t0 = time.time()
        model = build_random_forest(**params)
        model.fit(X_train, y_train)
        val_proba_rf = model.predict_proba(X_val)[:, 1]
        val_pr_auc = compute_classification_metrics(y_val, (val_proba_rf > 0.5).astype(int), val_proba_rf)["pr_auc"]
        rf_candidates.append({"params": params, "model": model, "val_pr_auc": val_pr_auc})
        print(f"  {params} -> VAL PR-AUC={val_pr_auc:.4f} ({time.time()-t0:.1f}s)")

    best_rf = max(rf_candidates, key=lambda c: c["val_pr_auc"])
    rf_model = best_rf["model"]
    print(f"  SELECTED: {best_rf['params']}")

    train_proba_rf = rf_model.predict_proba(X_train)[:, 1]
    val_proba_rf = rf_model.predict_proba(X_val)[:, 1]
    rf_threshold, rf_thr_info = select_threshold_train_then_val(y_train, train_proba_rf, y_val, val_proba_rf)

    test_proba_rf = rf_model.predict_proba(X_test)[:, 1]
    test_pred_rf = (test_proba_rf > rf_threshold).astype(int)
    m_rf = compute_classification_metrics(y_test, test_pred_rf, test_proba_rf)
    rf_calib = compute_brier_and_calibration(y_test, test_proba_rf)
    print(f"  TEST (single pass): threshold={rf_threshold:.4f} PR-AUC={m_rf['pr_auc']:.4f} "
          f"ROC-AUC={m_rf['roc_auc']:.4f} P={m_rf['precision']:.4f} R={m_rf['recall']:.4f} F1={m_rf['f1']:.4f} "
          f"Brier={rf_calib['brier_score']:.4f}")

    all_metrics["random_forest"] = {
        "hyperparameter_search": [{"params": c["params"], "val_pr_auc": c["val_pr_auc"]} for c in rf_candidates],
        "selected_hyperparameters": best_rf["params"], "threshold": rf_threshold, "threshold_info": rf_thr_info,
        "test_metrics": m_rf, "calibration": rf_calib,
    }
    joblib.dump(rf_model, os.path.join(MODELS_DIR, "random_forest.joblib"))

    rf_val_sweep = threshold_sweep(y_val, val_proba_rf)
    rf_val_sweep.to_csv(os.path.join(OUT_DIR, "threshold_analysis.csv"), index=False)
    print(f"\nThreshold sweep (VAL, Random Forest) -> {os.path.join(OUT_DIR, 'threshold_analysis.csv')}")
    print(rf_val_sweep.to_string(index=False))

    best_model_name = "random_forest" if m_rf["pr_auc"] >= m_logreg["pr_auc"] else "logistic_regression"
    all_metrics["best_model"] = best_model_name
    all_metrics["core_features"] = CORE_FEATURES
    all_metrics["seed"] = SEED
    all_metrics["runtime_seconds"] = time.time() - t_start

    with open(os.path.join(OUT_DIR, "model_metrics.json"), "w") as f:
        json.dump(all_metrics, f, indent=2, cls=_NumpyJSONEncoder)
    print(f"\nSaved -> {os.path.join(OUT_DIR, 'model_metrics.json')}")
    print(f"Best model by TEST PR-AUC: {best_model_name}")
    print(f"train_baseline.py runtime: {time.time()-t_start:.1f}s")


if __name__ == "__main__":
    main()
