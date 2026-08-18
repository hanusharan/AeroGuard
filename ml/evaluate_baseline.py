"""Steps 7-10 of the Task 4 baseline experiment: lead-time analysis,
feature importance + A/B/C ablation, regime/airspeed post-hoc analysis,
and generalization sanity checks. Loads the models train_baseline.py
already fit and froze -- does not re-tune anything.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import joblib
import numpy as np
import pandas as pd

from ml.calibration import select_threshold_train_then_val
from ml.evaluation import compute_classification_metrics, plot_confusion_matrix, plot_feature_importance, plot_pr_curves, plot_roc_curves, plot_probability_distribution
from ml.metrics import airspeed_bin_breakdown, compute_brier_and_calibration, lead_time_bucket_analysis, regime_breakdown
from ml.models import build_random_forest
from ml.plots import plot_calibration_curve, plot_lead_time_buckets
from ml.train_baseline import CORE_FEATURES, MODELS_DIR, OUT_DIR, TARGET, load_splits

METADATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "metadata", "trajectory_metadata_v2.csv")


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


def main():
    plots_dir = os.path.join(OUT_DIR, "plots")
    os.makedirs(plots_dir, exist_ok=True)
    t_start = time.time()

    with open(os.path.join(OUT_DIR, "model_metrics.json")) as f:
        primary_metrics = json.load(f)
    best_model_name = primary_metrics["best_model"]
    print(f"Best model from train_baseline.py: {best_model_name}")

    train, val, test = load_splits()
    rf_model = joblib.load(os.path.join(MODELS_DIR, "random_forest.joblib"))
    logreg_model = joblib.load(os.path.join(MODELS_DIR, "logistic_regression.joblib"))
    rf_threshold = primary_metrics["random_forest"]["threshold"]

    X_test, y_test = test[CORE_FEATURES], test[TARGET].to_numpy().astype(int)
    test_proba_rf = rf_model.predict_proba(X_test)[:, 1]
    test_pred_rf = (test_proba_rf > rf_threshold).astype(int)

    # =========================================================================
    print("\n" + "=" * 78)
    print("STEP 7: LEAD-TIME-BY-TIME-TO-EVENT ANALYSIS (TEST, Random Forest)")
    print("=" * 78)
    # =========================================================================
    lead_df = lead_time_bucket_analysis(test["time_to_stall"].to_numpy(), y_test, test_pred_rf)
    lead_df.to_csv(os.path.join(OUT_DIR, "lead_time_analysis.csv"), index=False)
    print(lead_df.to_string(index=False))
    plot_lead_time_buckets(lead_df, os.path.join(plots_dir, "lead_time_plot.png"),
                            f"Recall by time-to-actual-crossing ({best_model_name}, TEST)")

    # =========================================================================
    print("\n" + "=" * 78)
    print("STEP 8: FEATURE IMPORTANCE + A/B/C ABLATION (common full-window subset)")
    print("=" * 78)
    # =========================================================================
    importances = rf_model.feature_importances_
    fi_df = pd.DataFrame({"feature": CORE_FEATURES, "importance": importances}).sort_values("importance", ascending=False)
    fi_df.to_csv(os.path.join(OUT_DIR, "feature_importance.csv"), index=False)
    print(fi_df.to_string(index=False))
    plot_feature_importance(CORE_FEATURES, importances, os.path.join(plots_dir, "feature_importance.png"),
                             f"Feature importance: {best_model_name}")
    print("\nRedundancy note: 'alpha' and 'stall_margin' are algebraically identical (stall_margin = const - alpha).")
    print("Their individual importances below should NOT be read as independent evidence -- a tree model splits on")
    print("whichever of the two happens to be picked first at each node, so their importances partially trade off")
    print("against each other rather than each representing a distinct source of information.")

    ABLATION_A = ["V", "alpha", "gamma", "pitch_rate", "altitude", "elevator", "throttle", "stall_margin"]
    ABLATION_B = ABLATION_A + ["dV_dt", "dalpha_dt", "dgamma_dt", "dq_dt"]
    ABLATION_C = ABLATION_B + ["alpha_trend_1s", "alpha_trend_2s", "alpha_trend_3s"]

    full_window_train = train[train["alpha_trend_3s"].notna()]
    full_window_val = val[val["alpha_trend_3s"].notna()]
    full_window_test = test[test["alpha_trend_3s"].notna()]
    print(f"\nCommon full-window subset (required so A/B/C are compared on IDENTICAL rows, not just identical feature "
          f"counts): train={len(full_window_train):,} val={len(full_window_val):,} test={len(full_window_test):,}")

    rf_params = primary_metrics["random_forest"]["selected_hyperparameters"]
    ablation_rows = []
    for name, features in [("A_state_only", ABLATION_A), ("B_state_plus_derivatives", ABLATION_B), ("C_state_derivatives_history", ABLATION_C)]:
        Xtr, ytr = full_window_train[features], full_window_train[TARGET].to_numpy().astype(int)
        Xv, yv = full_window_val[features], full_window_val[TARGET].to_numpy().astype(int)
        Xte, yte = full_window_test[features], full_window_test[TARGET].to_numpy().astype(int)

        model = build_random_forest(**rf_params)
        model.fit(Xtr, ytr)
        proba_tr = model.predict_proba(Xtr)[:, 1]
        proba_v = model.predict_proba(Xv)[:, 1]
        thr, _ = select_threshold_train_then_val(ytr, proba_tr, yv, proba_v)
        proba_te = model.predict_proba(Xte)[:, 1]
        pred_te = (proba_te > thr).astype(int)
        m = compute_classification_metrics(yte, pred_te, proba_te)
        ablation_rows.append({"condition": name, "n_features": len(features), "pr_auc": m["pr_auc"], "roc_auc": m["roc_auc"],
                               "precision": m["precision"], "recall": m["recall"], "f1": m["f1"]})
        print(f"  {name:30s} n_features={len(features):2d} PR-AUC={m['pr_auc']:.4f} F1={m['f1']:.4f} recall={m['recall']:.4f}")

    ablation_df = pd.DataFrame(ablation_rows)
    ablation_df.to_csv(os.path.join(OUT_DIR, "ablation_results.csv"), index=False)
    print(
        "\nIMPORTANT CAVEAT (do not compare these PR-AUC values directly to the primary model's TEST PR-AUC above):\n"
        "  The full-window subset required for a fair A/B/C comparison EXCLUDES each trajectory's first 3 seconds,\n"
        "  which also means it excludes every trajectory under ~8s total duration entirely (Task 3's finding).\n"
        "  Those short trajectories were disproportionately the fast, hard-to-predict 'stall'-regime departures\n"
        "  (Step 7 above shows recall collapses for anything more than 1s before the actual crossing). The ablation's\n"
        "  higher absolute PR-AUC (~0.93 vs. ~0.74 for the primary model) reflects evaluation on an EASIER,\n"
        "  longer/slower-developing subset of trajectories, not that state-only features suddenly work much better\n"
        "  in general. The RELATIVE ordering across A -> B -> C (which features help, by how much) is still valid;\n"
        "  the absolute numbers are not comparable across the two experiments."
    )

    # =========================================================================
    print("\n" + "=" * 78)
    print("STEP 9: REGIME + AIRSPEED POST-HOC ANALYSIS (TEST, Random Forest; regime NEVER a model input)")
    print("=" * 78)
    # =========================================================================
    metadata = pd.read_csv(METADATA_PATH)[["trajectory_id", "generation_mode", "initial_airspeed"]]
    test_with_meta = test.merge(metadata, on="trajectory_id", how="left")
    regime_df = regime_breakdown(y_test, test_pred_rf, test_proba_rf, test_with_meta["generation_mode"].to_numpy())
    regime_df.to_csv(os.path.join(OUT_DIR, "regime_performance.csv"), index=False)
    print(regime_df.to_string(index=False))

    airspeed_df = airspeed_bin_breakdown(y_test, test_pred_rf, test_with_meta["initial_airspeed"].to_numpy())
    airspeed_df.to_csv(os.path.join(OUT_DIR, "airspeed_bin_performance.csv"), index=False)
    print(airspeed_df.to_string(index=False))

    # =========================================================================
    print("\n" + "=" * 78)
    print("STEP 10: GENERALIZATION SANITY CHECKS (remove-one-group, VAL only -- diagnostic, not tuning)")
    print("=" * 78)
    # =========================================================================
    baseline_val_pr_auc = None
    removal_groups = {
        "full_core_set (reference)": CORE_FEATURES,
        "remove_altitude": [f for f in CORE_FEATURES if f != "altitude"],
        "remove_stall_margin": [f for f in CORE_FEATURES if f != "stall_margin"],
        "remove_alpha": [f for f in CORE_FEATURES if f != "alpha"],
        "remove_control_inputs (elevator+throttle)": [f for f in CORE_FEATURES if f not in ("elevator", "throttle")],
    }
    sanity_rows = []
    for name, features in removal_groups.items():
        Xtr, ytr = train[features], train[TARGET].to_numpy().astype(int)
        Xv, yv = val[features], val[TARGET].to_numpy().astype(int)
        model = build_random_forest(**rf_params)
        model.fit(Xtr, ytr)
        proba_v = model.predict_proba(Xv)[:, 1]
        m = compute_classification_metrics(yv, (proba_v > 0.5).astype(int), proba_v)
        if baseline_val_pr_auc is None:
            baseline_val_pr_auc = m["pr_auc"]
        delta = m["pr_auc"] - baseline_val_pr_auc
        sanity_rows.append({"condition": name, "n_features": len(features), "val_pr_auc": m["pr_auc"], "delta_vs_full": delta})
        print(f"  {name:45s} n_features={len(features):2d} VAL PR-AUC={m['pr_auc']:.4f}  (delta={delta:+.4f})")

    sanity_df = pd.DataFrame(sanity_rows)
    sanity_df.to_csv(os.path.join(OUT_DIR, "generalization_sanity_checks.csv"), index=False)
    print("\nNote: 'remove regime-related metadata' is not applicable as a removal test -- generation_mode/regime")
    print("was never included as a model input in the first place (Step 9 confirms this: it is used only to slice")
    print("already-computed TEST predictions for post-hoc analysis above, never passed to any model's .fit()).")

    # =========================================================================
    print("\n" + "=" * 78)
    print("PLOTS")
    print("=" * 78)
    # =========================================================================
    logreg_threshold = primary_metrics["logistic_regression"]["threshold"]
    test_proba_logreg = logreg_model.predict_proba(X_test)[:, 1]
    test_pred_logreg = (test_proba_logreg > logreg_threshold).astype(int)

    curves = [("random_forest", y_test, test_proba_rf), ("logistic_regression", y_test, test_proba_logreg)]
    plot_pr_curves(curves, os.path.join(plots_dir, "precision_recall_curve.png"))
    plot_roc_curves(curves, os.path.join(plots_dir, "roc_curve.png"))

    m_rf = compute_classification_metrics(y_test, test_pred_rf, test_proba_rf)
    plot_confusion_matrix(m_rf["confusion_matrix"], os.path.join(plots_dir, "confusion_matrix.png"), f"Confusion matrix: {best_model_name} (TEST)")

    rf_calib = compute_brier_and_calibration(y_test, test_proba_rf)
    plot_calibration_curve(rf_calib, os.path.join(plots_dir, "calibration_curve.png"), f"Calibration: {best_model_name} (TEST)")

    plot_probability_distribution(y_test, test_proba_rf, os.path.join(plots_dir, "probability_distribution.png"),
                                   f"Predicted probability distribution: {best_model_name} (TEST)", threshold=rf_threshold)
    print(f"Plots -> {plots_dir}")

    # =========================================================================
    experiment_config = {
        "seed": 20260817,
        "core_features": CORE_FEATURES,
        "ablation_conditions": {"A_state_only": ABLATION_A, "B_state_plus_derivatives": ABLATION_B, "C_state_derivatives_history": ABLATION_C},
        "best_model": best_model_name,
        "random_forest_hyperparameters": rf_params,
        "random_forest_threshold": rf_threshold,
        "logistic_regression_threshold": logreg_threshold,
        "dataset_version": "stage2-v0.2-calibration",
        "ml_dataset_version": "ml_v2.0",
    }
    with open(os.path.join(OUT_DIR, "experiment_config.json"), "w") as f:
        json.dump(experiment_config, f, indent=2, cls=_NumpyJSONEncoder)
    print(f"\nSaved -> {os.path.join(OUT_DIR, 'experiment_config.json')}")
    print(f"evaluate_baseline.py runtime: {time.time()-t_start:.1f}s")


if __name__ == "__main__":
    main()
