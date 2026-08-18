"""AeroGuard Stage 4: temporal early-warning experiment driver.

Research question: "Can temporal information recover useful
early-warning signal that is not available from the instantaneous
state?" -- see outputs/ml_temporal/temporal_experiment_report.md for
the full writeup this script's output feeds into.

Reads ONLY data/processed/processed_dataset_v2.parquet,
data/splits/split_manifest_v2.csv, data/metadata/trajectory_metadata_v2.csv,
and (read-only, for reference) outputs/ml_baseline/. Never modifies
aeroguard/, data/processed/, data/splits/, data/ml/, or
outputs/ml_baseline/. All new artifacts go under outputs/ml_temporal/
and data/ml_temporal/ (both new, additive locations).

Run with:
    python scripts/run_temporal_experiment.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from ml import temporal_config as tcfg
from ml.evaluation import plot_confusion_matrix, plot_feature_importance, plot_pr_curves
from ml.plots import plot_calibration_curve
from ml.temporal_data import load_temporal_splits
from ml.temporal_experiment import (
    NumpyJSONEncoder,
    evaluate_frozen_baseline,
    get_xy,
    lead_time_bucket_analysis_fine,
    physics_information_diagnosis,
    run_false_alarm_analysis,
    run_generalization_check,
    run_primary_model,
    run_regime_airspeed_breakdown,
    run_window_ablation,
    tune_rf_hyperparameters,
)
from ml.temporal_features import common_subset_mask
from ml.metrics import compute_brier_and_calibration
from ml.temporal_plots import (
    plot_diagnosis_distributions,
    plot_lead_time_by_group,
    plot_lead_time_recall_comparison,
    plot_lead_time_recall_vs_window,
    plot_pr_auc_vs_window,
    plot_warning_composition,
    plot_warning_time_distribution,
)

PRIMARY_WINDOW_S = 1.0  # chosen a priori for the "realistic full-population" model: enough
# history to be meaningfully temporal, small enough to keep row/trajectory loss minimal
# (see outputs/ml_temporal/temporal_experiment_report.md Section 6 for the row-population
# accounting that motivates this choice, and Section 9 for how it's revisited against the
# window-ablation results).


def save_json(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, cls=NumpyJSONEncoder)
    print(f"  -> {path}")


def save_csv(rows, path):
    pd.DataFrame(rows).to_csv(path, index=False)
    print(f"  -> {path}")


def main():
    t_start = time.time()
    tcfg.ensure_dirs()

    print("=" * 78)
    print("STAGE 0: LOAD / BUILD TEMPORAL FEATURE PANELS")
    print("=" * 78)
    splits = load_temporal_splits(force=False, verbose=True)

    print("\n" + "=" * 78)
    print("STAGE 1: HYPERPARAMETER TUNING (frozen for the whole hierarchy)")
    print("=" * 78)
    rf_params, tuning_log = tune_rf_hyperparameters(splits, tuning_window_s=2.0, verbose=True)
    save_json({"grid": tuning_log, "selected": rf_params}, os.path.join(tcfg.METRICS_DIR, "hyperparameter_tuning.json"))

    print("\n" + "=" * 78)
    print("STAGE 2: FAIR WINDOW ABLATION (Task 4/5/8, common subset) -- A/B/C_w/D_w")
    print("=" * 78)
    ablation_results = run_window_ablation(splits, rf_params, windows_s=tcfg.HISTORY_WINDOWS_S, verbose=True)
    save_json(ablation_results, os.path.join(tcfg.METRICS_DIR, "window_ablation_common_subset.json"))

    summary_rows = []
    for key, res in ablation_results.items():
        if key == "common_subset_population":
            continue
        m = res["test_metrics"]
        row = {"model": key, "n_features": res.get("n_features"), "pr_auc": m["pr_auc"], "roc_auc": m["roc_auc"],
               "precision": m["precision"], "recall": m["recall"], "f1": m["f1"],
               "event_recall": res["event_level"]["event_recall"], "median_lead_time_s": res["event_level"]["median_lead_time_s"]}
        for b in res["lead_time_recall_bucket"]:
            row[f"recall_{b['bucket']}"] = b["recall"]
        summary_rows.append(row)
    save_csv(summary_rows, os.path.join(tcfg.METRICS_DIR, "window_ablation_summary.csv"))

    print("\n" + "=" * 78)
    print(f"STAGE 3: PRIMARY MODEL (Model D, window={PRIMARY_WINDOW_S}s, own realistic-scale population)")
    print("=" * 78)
    primary_model, primary_thr, primary_res, primary_proba, primary_pred, primary_test_sub, primary_test_mask = run_primary_model(
        splits, rf_params, window_s=PRIMARY_WINDOW_S, verbose=True,
    )
    print(f"  PRIMARY TEST: PR-AUC={primary_res['test_metrics']['pr_auc']:.4f} F1={primary_res['test_metrics']['f1']:.4f} "
          f"event_recall={primary_res['event_level']['event_recall']:.3f} median_lead={primary_res['event_level']['median_lead_time_s']}")
    save_json(primary_res, os.path.join(tcfg.METRICS_DIR, "primary_model_metrics.json"))
    import joblib
    joblib.dump(primary_model, os.path.join(tcfg.MODELS_DIR, f"primary_model_D_{tcfg._fmt(PRIMARY_WINDOW_S)}s.joblib"))

    primary_y_true = primary_test_sub[tcfg.TARGET_COL].to_numpy().astype(int)

    print("\n" + "=" * 78)
    print("STAGE 4: FALSE-ALARM CONTROL (Task 7, primary model)")
    print("=" * 78)
    false_alarm_res = run_false_alarm_analysis(primary_test_sub, primary_y_true, primary_pred)
    save_json(false_alarm_res, os.path.join(tcfg.METRICS_DIR, "false_alarm_analysis.json"))
    print(f"  episode precision={false_alarm_res['episode_level']['precision_at_operating_point_episode_level']:.3f} "
          f"row FPR={false_alarm_res['row_level_false_positive_rate']:.4f} "
          f"warnings/traj={false_alarm_res['episode_level']['warnings_per_trajectory']:.3f} "
          f"false_alarms/min={false_alarm_res['false_alarms_per_minute']:.4f}")

    print("\n" + "=" * 78)
    print("STAGE 5: REGIME / AIRSPEED BREAKDOWN (Task 10, primary model, post-hoc only)")
    print("=" * 78)
    regime_df, airspeed_df, lead_by_regime, lead_by_airspeed = run_regime_airspeed_breakdown(
        primary_test_sub, primary_y_true, primary_pred, primary_proba,
    )
    regime_df.to_csv(os.path.join(tcfg.METRICS_DIR, "regime_breakdown.csv"), index=False)
    airspeed_df.to_csv(os.path.join(tcfg.METRICS_DIR, "airspeed_breakdown.csv"), index=False)
    lead_by_regime.to_csv(os.path.join(tcfg.METRICS_DIR, "lead_time_by_regime.csv"), index=False)
    lead_by_airspeed.to_csv(os.path.join(tcfg.METRICS_DIR, "lead_time_by_airspeed.csv"), index=False)
    print(regime_df.to_string(index=False))

    print("\n" + "=" * 78)
    print("STAGE 6: PHYSICS / INFORMATION DIAGNOSIS (Task 9)")
    print("=" * 78)
    diag_df, diag_samples = physics_information_diagnosis(splits["test"])
    diag_df.to_csv(os.path.join(tcfg.METRICS_DIR, "physics_diagnosis.csv"), index=False)
    print(diag_df.pivot(index="variable", columns="lead_time_s", values="separability_auc").to_string())

    print("\n" + "=" * 78)
    print("STAGE 7: GENERALIZATION CHECK (Task 11, exclude 'stall' regime from TRAIN)")
    print("=" * 78)
    generalization_res = run_generalization_check(splits, rf_params, window_s=PRIMARY_WINDOW_S, verbose=True)
    save_json(generalization_res, os.path.join(tcfg.METRICS_DIR, "generalization_check.json"))
    print(f"  full-train stall-regime recall (reference, from Stage 5 above): "
          f"{[r for r in regime_df.to_dict('records') if r['regime']=='stall']}")
    print(f"  stall-excluded-train stall-regime recall: "
          f"{[r for r in generalization_res['regime_breakdown'] if r['regime']=='stall']}")

    print("\n" + "=" * 78)
    print("STAGE 8: PLOTS")
    print("=" * 78)
    plots_dir = tcfg.PLOTS_DIR

    common_test_mask = common_subset_mask(splits["test"], tcfg.HISTORY_WINDOWS_S)
    frozen_res = ablation_results["A_frozen_baseline"]
    best_d_key = max((k for k in ablation_results if k.startswith("D_")), key=lambda k: ablation_results[k]["test_metrics"]["pr_auc"])

    # Plot 1: PR curve for the primary (realistic-population) model vs. the frozen baseline re-scored on ITS OWN population
    from ml.train_baseline import CORE_FEATURES
    import joblib as _joblib
    baseline_on_primary_pop = evaluate_frozen_baseline(splits["test"], primary_test_mask)
    baseline_model = _joblib.load(os.path.join(tcfg.BASELINE_MODELS_DIR, "random_forest.joblib"))
    Xte_a, yte_a, _ = get_xy(splits["test"], CORE_FEATURES, primary_test_mask)
    proba_a = baseline_model.predict_proba(Xte_a)[:, 1]
    pred_a = (proba_a > baseline_on_primary_pop["threshold"]).astype(int)
    plot_pr_curves(
        [("A: frozen instantaneous baseline", primary_y_true, proba_a),
         (f"D (primary): state+derivatives+{PRIMARY_WINDOW_S}s temporal", primary_y_true, primary_proba)],
        os.path.join(plots_dir, "01_pr_curve_instantaneous_vs_temporal.png"),
        title="PR curve: instantaneous vs. temporal (same TEST population)",
    )

    lead_dfs = {
        "A: instantaneous baseline": lead_time_bucket_analysis_fine(primary_test_sub["time_to_stall"].to_numpy(), yte_a, pred_a),
        f"D (primary, {PRIMARY_WINDOW_S}s)": pd.DataFrame(primary_res["lead_time_recall_bucket"]),
    }
    plot_lead_time_recall_comparison(lead_dfs, os.path.join(plots_dir, "02_lead_time_recall_comparison.png"),
                                      "Recall by actual lead time: instantaneous vs. temporal")

    plot_warning_composition(false_alarm_res["warning_composition_by_time_to_nearest_crossing"],
                              os.path.join(plots_dir, "03_warning_composition_by_lead_time.png"),
                              "Warning composition by proximity to nearest actual crossing (primary model)")

    plot_pr_auc_vs_window(ablation_results, os.path.join(plots_dir, "04_pr_auc_vs_history_window.png"))
    plot_lead_time_recall_vs_window(ablation_results, os.path.join(plots_dir, "04b_early_warning_recall_vs_history_window.png"))

    plot_warning_time_distribution(primary_res["event_level"]["lead_times_s"],
                                    os.path.join(plots_dir, "05_warning_time_distribution.png"),
                                    "Distribution of credited warning (lead) time -- primary model, TEST")

    plot_feature_importance(primary_res["feature_columns"], primary_model.feature_importances_,
                             os.path.join(plots_dir, "06_feature_importance_primary_model.png"),
                             f"Feature importance: primary model (Model D, {PRIMARY_WINDOW_S}s window)")

    plot_confusion_matrix(primary_res["test_metrics"]["confusion_matrix"],
                           os.path.join(plots_dir, "06b_confusion_matrix_primary_model.png"),
                           "Confusion matrix: primary model (TEST)")

    plot_lead_time_by_group(lead_by_regime, "regime", os.path.join(plots_dir, "07_lead_time_by_regime.png"),
                             "Lead-time recall by regime (primary model, TEST, regime NEVER a model input)")

    plot_lead_time_by_group(lead_by_airspeed, "airspeed_bin_m_s", os.path.join(plots_dir, "08_lead_time_by_airspeed.png"),
                             "Lead-time recall by initial-airspeed bin (primary model, TEST)")

    from ml.temporal_experiment import DIAGNOSIS_VARIABLES
    plot_diagnosis_distributions(diag_samples, DIAGNOSIS_VARIABLES, [1, 3, 5],
                                  os.path.join(plots_dir, "09_feature_distributions_near_vs_safe.png"))

    primary_calib = compute_brier_and_calibration(primary_y_true, primary_proba)
    plot_calibration_curve(primary_calib, os.path.join(plots_dir, "10_calibration_curve_primary_model.png"),
                            "Calibration: primary model (TEST)")
    save_json(primary_calib, os.path.join(tcfg.METRICS_DIR, "primary_model_calibration.json"))

    print(f"  plots -> {plots_dir}")

    print("\n" + "=" * 78)
    print("STAGE 9: EXPERIMENT CONFIG")
    print("=" * 78)
    config_out = {
        "seed": tcfg.SEED,
        "dt": tcfg.DT,
        "history_windows_s": tcfg.HISTORY_WINDOWS_S,
        "rf_hyperparameters_frozen": rf_params,
        "primary_window_s": PRIMARY_WINDOW_S,
        "instantaneous_state_features": tcfg.INSTANTANEOUS_STATE_FEATURES,
        "state_derivative_features_model_b": tcfg.STATE_DERIVATIVE_FEATURES,
        "temporal_feature_columns_by_window": {tcfg._fmt(w): tcfg.temporal_feature_columns(w) for w in tcfg.HISTORY_WINDOWS_S},
        "primary_model_threshold": primary_thr,
        "best_window_ablation_model_by_common_subset_pr_auc": best_d_key,
        "runtime_seconds": time.time() - t_start,
    }
    save_json(config_out, os.path.join(tcfg.OUTPUTS_DIR, "experiment_config.json"))

    print(f"\nTotal runtime: {time.time()-t_start:.1f}s")


if __name__ == "__main__":
    main()
