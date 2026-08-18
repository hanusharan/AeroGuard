"""AeroGuard FINAL temporal early-warning experiment: v0.2 vs v0.3.

Research question: "Does the physically credible multi-second precursor
introduced in v0.3 produce genuinely useful early-warning performance
that was absent in v0.2?" See outputs/ml_v03/v03_temporal_ml_report.md
for the full writeup this script's output feeds into.

Pre-registered methodology (locked BEFORE this script was ever run, per
ml/temporal_config_v03.py's module docstring): SAME model family
(RandomForest, frozen v0.2 hyperparameters, no re-tuning), SAME feature
definitions (imported unchanged from ml/temporal_config.py), SAME
threshold-selection procedure (TRAIN-then-VAL), SAME event/lead-time
definitions (ml/events.py, unchanged), SAME lead-time bucket edges
(ml/temporal_experiment.py's LEAD_TIME_BINS_FINE, unchanged). The only
deliberate deviations from v0.2's exact experiment shape are efficiency
choices stated explicitly up front, not discovered after seeing results:
  - History windows: [0.5, 1, 2]s (not v0.2's [0.5,1,2,3]s) -- v0.2
    already showed 3s adds nothing (Sec 5/6 of its report).
  - Model C (temporal stats without derivatives) is skipped entirely --
    v0.2 showed it is consistently worse than A at every window.
  - No hyperparameter re-tuning stage -- v0.2's own frozen RF config is
    reused unchanged (ml/temporal_config_v03.py:FROZEN_RF_PARAMS).

Reads ONLY data/processed/processed_dataset_v3.parquet,
data/splits/split_manifest_v3.csv, data/metadata/trajectory_metadata_v3.csv
(all v0.3-generation-gate outputs, read-only) and, for reference only,
outputs/ml_temporal/ (v0.2's already-computed results -- never rerun).
Never modifies aeroguard/, data/processed/, data/splits/, data/ml/,
data/ml_temporal/, or outputs/ml_temporal/. All new artifacts go under
outputs/ml_v03/ and data/ml_temporal_v03/ (both new, additive locations).

Run with:
    python scripts/run_temporal_experiment_v03.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import joblib
import pandas as pd

from ml import temporal_config_v03 as v3cfg
from ml.evaluation import plot_confusion_matrix, plot_feature_importance, plot_pr_curves
from ml.plots import plot_calibration_curve
from ml.temporal_data_v03 import load_temporal_splits
from ml.temporal_experiment import (
    NumpyJSONEncoder,
    physics_information_diagnosis,
    run_false_alarm_analysis,
)
from ml.temporal_experiment_v03 import (
    fractions_detected_at_least_v03,
    run_common_subset_ablation_v03,
    run_generalization_check_v03,
    run_primary_model_v03,
    run_regime_airspeed_breakdown_v03,
)
from ml.metrics import compute_brier_and_calibration
from ml.temporal_plots import (
    plot_diagnosis_distributions,
    plot_lead_time_by_group,
    plot_lead_time_recall_comparison,
    plot_pr_auc_vs_window,
    plot_warning_time_distribution,
)


def save_json(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, cls=NumpyJSONEncoder)
    print(f"  -> {path}")


def save_csv(rows, path):
    pd.DataFrame(rows).to_csv(path, index=False)
    print(f"  -> {path}")


def main():
    t_start = time.time()
    v3cfg.ensure_dirs()
    rf_params = v3cfg.FROZEN_RF_PARAMS

    print("=" * 78)
    print("STAGE 0: LOAD / BUILD v0.3 TEMPORAL FEATURE PANELS")
    print("=" * 78)
    splits = load_temporal_splits(force=False, verbose=True)

    print("\n" + "=" * 78)
    print(f"STAGE 1: COMMON-SUBSET ABLATION (A retrained / B / D at {v3cfg.HISTORY_WINDOWS_S})")
    print("=" * 78)
    ablation_results, a_bundle = run_common_subset_ablation_v03(splits, rf_params, windows_s=v3cfg.HISTORY_WINDOWS_S, verbose=True)
    save_json(ablation_results, os.path.join(v3cfg.METRICS_DIR, "common_subset_ablation.json"))

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
    save_csv(summary_rows, os.path.join(v3cfg.METRICS_DIR, "common_subset_ablation_summary.csv"))

    print("\n" + "=" * 78)
    print(f"STAGE 2: PRIMARY MODEL (Model D, window={v3cfg.PRIMARY_WINDOW_S}s, own realistic-scale population)")
    print("=" * 78)
    primary_model, primary_thr, primary_res, primary_proba, primary_pred, primary_test_sub, primary_test_mask = run_primary_model_v03(
        splits, rf_params, window_s=v3cfg.PRIMARY_WINDOW_S, verbose=True,
    )
    print(f"  PRIMARY TEST: PR-AUC={primary_res['test_metrics']['pr_auc']:.4f} F1={primary_res['test_metrics']['f1']:.4f} "
          f"event_recall={primary_res['event_level']['event_recall']:.3f} median_lead={primary_res['event_level']['median_lead_time_s']}")
    save_json(primary_res, os.path.join(v3cfg.METRICS_DIR, "primary_model_metrics.json"))
    joblib.dump(primary_model, os.path.join(v3cfg.MODELS_DIR, f"primary_model_D_{v3cfg._fmt(v3cfg.PRIMARY_WINDOW_S)}s.joblib"))

    primary_y_true = primary_test_sub[v3cfg.TARGET_COL].to_numpy().astype(int)

    # Extend fraction-of-events-detected with the 0.5s threshold explicitly requested
    from ml.events import aggregate_event_results, compute_event_level_results
    primary_event_results = compute_event_level_results(primary_test_sub, primary_pred, v3cfg.LABELING_HORIZON_S)
    primary_res["fraction_of_events_detected_at_least"] = fractions_detected_at_least_v03(primary_event_results, v3cfg.LABELING_HORIZON_S)
    save_json(primary_res["fraction_of_events_detected_at_least"], os.path.join(v3cfg.METRICS_DIR, "primary_model_warning_coverage.json"))
    print(f"  warning coverage: {primary_res['fraction_of_events_detected_at_least']}")

    print("\n" + "=" * 78)
    print("STAGE 3: FALSE-ALARM CONTROL (primary model)")
    print("=" * 78)
    false_alarm_res = run_false_alarm_analysis(primary_test_sub, primary_y_true, primary_pred)
    save_json(false_alarm_res, os.path.join(v3cfg.METRICS_DIR, "false_alarm_analysis.json"))
    print(f"  episode precision={false_alarm_res['episode_level']['precision_at_operating_point_episode_level']:.3f} "
          f"row FPR={false_alarm_res['row_level_false_positive_rate']:.4f} "
          f"warnings/traj={false_alarm_res['episode_level']['warnings_per_trajectory']:.3f} "
          f"false_alarms/min={false_alarm_res['false_alarms_per_minute']:.4f}")

    print("\n" + "=" * 78)
    print("STAGE 4: REGIME / AIRSPEED BREAKDOWN (primary model, post-hoc only)")
    print("=" * 78)
    regime_df, airspeed_df, lead_by_regime = run_regime_airspeed_breakdown_v03(
        primary_test_sub, primary_y_true, primary_pred, primary_proba,
    )
    regime_df.to_csv(os.path.join(v3cfg.METRICS_DIR, "regime_breakdown.csv"), index=False)
    airspeed_df.to_csv(os.path.join(v3cfg.METRICS_DIR, "airspeed_breakdown.csv"), index=False)
    lead_by_regime.to_csv(os.path.join(v3cfg.METRICS_DIR, "lead_time_by_regime.csv"), index=False)
    print(regime_df.to_string(index=False))

    print("\n" + "=" * 78)
    print("STAGE 5: PHYSICS / INFORMATION DIAGNOSIS")
    print("=" * 78)
    diag_df, diag_samples = physics_information_diagnosis(splits["test"])
    diag_df.to_csv(os.path.join(v3cfg.METRICS_DIR, "physics_diagnosis.csv"), index=False)
    print(diag_df.pivot(index="variable", columns="lead_time_s", values="separability_auc").to_string())

    print("\n" + "=" * 78)
    print(f"STAGE 6: GENERALIZATION CHECK (exclude '{v3cfg.GRADUAL_REGIME_NAME}' from TRAIN)")
    print("=" * 78)
    generalization_res = run_generalization_check_v03(
        splits, rf_params, window_s=v3cfg.PRIMARY_WINDOW_S, exclude_regime=v3cfg.GRADUAL_REGIME_NAME, verbose=True,
    )
    save_json(generalization_res, os.path.join(v3cfg.METRICS_DIR, "generalization_check.json"))
    excl_regime_row = [r for r in generalization_res["regime_breakdown"] if r["regime"] == v3cfg.GRADUAL_REGIME_NAME]
    full_regime_row = [r for r in regime_df.to_dict("records") if r["regime"] == v3cfg.GRADUAL_REGIME_NAME]
    print(f"  full-train {v3cfg.GRADUAL_REGIME_NAME} recall (reference, Stage 4): {full_regime_row}")
    print(f"  {v3cfg.GRADUAL_REGIME_NAME}-excluded-train recall: {excl_regime_row}")

    print("\n" + "=" * 78)
    print("STAGE 7: PLOTS")
    print("=" * 78)
    plots_dir = v3cfg.PLOTS_DIR

    a_res = ablation_results["A_v03_retrained"]
    a_y_true = a_bundle["test_sub"][v3cfg.TARGET_COL].to_numpy().astype(int)

    plot_pr_curves(
        [("A: v0.3-retrained instantaneous baseline", a_y_true, a_bundle["proba"]),
         (f"D (primary): state+derivatives+{v3cfg.PRIMARY_WINDOW_S}s temporal (own population)", primary_y_true, primary_proba)],
        os.path.join(plots_dir, "01_pr_curve_instantaneous_vs_temporal.png"),
        title="v0.3: PR curve, instantaneous baseline (common-subset pop.) vs. primary temporal model (own pop.)",
    )

    lead_dfs = {
        "A: instantaneous baseline (common subset)": pd.DataFrame(a_res["lead_time_recall_bucket"]),
        f"D (primary, {v3cfg.PRIMARY_WINDOW_S}s, own pop.)": pd.DataFrame(primary_res["lead_time_recall_bucket"]),
    }
    plot_lead_time_recall_comparison(lead_dfs, os.path.join(plots_dir, "02_lead_time_recall_comparison.png"),
                                      "v0.3: recall by actual lead time, instantaneous vs. temporal")

    plot_pr_auc_vs_window({**{"A_frozen_baseline": ablation_results["A_v03_retrained"]}, **ablation_results},
                           os.path.join(plots_dir, "03_pr_auc_vs_history_window.png"), "v0.3: PR-AUC vs. history window length (common subset, TEST)")

    plot_warning_time_distribution(primary_res["event_level"]["lead_times_s"],
                                    os.path.join(plots_dir, "04_warning_time_distribution.png"),
                                    "v0.3: distribution of credited warning (lead) time -- primary model, TEST")

    plot_feature_importance(primary_res["feature_columns"], primary_model.feature_importances_,
                             os.path.join(plots_dir, "05_feature_importance_primary_model.png"),
                             f"v0.3: feature importance, primary model (Model D, {v3cfg.PRIMARY_WINDOW_S}s window)")

    plot_confusion_matrix(primary_res["test_metrics"]["confusion_matrix"],
                           os.path.join(plots_dir, "05b_confusion_matrix_primary_model.png"),
                           "v0.3: confusion matrix, primary model (TEST)")

    plot_lead_time_by_group(lead_by_regime, "regime", os.path.join(plots_dir, "06_lead_time_by_regime.png"),
                             "v0.3: lead-time recall by regime (primary model, TEST, regime NEVER a model input)")

    from ml.temporal_experiment import DIAGNOSIS_VARIABLES
    plot_diagnosis_distributions(diag_samples, DIAGNOSIS_VARIABLES, [1, 3, 5],
                                  os.path.join(plots_dir, "07_feature_distributions_near_vs_safe.png"))

    primary_calib = compute_brier_and_calibration(primary_y_true, primary_proba)
    plot_calibration_curve(primary_calib, os.path.join(plots_dir, "08_calibration_curve_primary_model.png"),
                            "v0.3: calibration, primary model (TEST)")
    save_json(primary_calib, os.path.join(v3cfg.METRICS_DIR, "primary_model_calibration.json"))

    print(f"  plots -> {plots_dir}")

    print("\n" + "=" * 78)
    print("STAGE 8: EXPERIMENT CONFIG")
    print("=" * 78)
    config_out = {
        "seed": v3cfg.SEED,
        "dt": v3cfg.DT,
        "history_windows_s": v3cfg.HISTORY_WINDOWS_S,
        "rf_hyperparameters_frozen": rf_params,
        "rf_hyperparameters_source": "reused unchanged from outputs/ml_temporal/experiment_config.json (v0.2), no re-tuning",
        "primary_window_s": v3cfg.PRIMARY_WINDOW_S,
        "instantaneous_state_features": v3cfg.INSTANTANEOUS_STATE_FEATURES,
        "state_derivative_features_model_b": v3cfg.STATE_DERIVATIVE_FEATURES,
        "temporal_feature_columns_by_window": {v3cfg._fmt(w): v3cfg.temporal_feature_columns(w) for w in v3cfg.HISTORY_WINDOWS_S},
        "primary_model_threshold": primary_thr,
        "generalization_excluded_regime": v3cfg.GRADUAL_REGIME_NAME,
        "runtime_seconds": time.time() - t_start,
    }
    save_json(config_out, os.path.join(v3cfg.OUTPUTS_DIR, "experiment_config.json"))

    print(f"\nTotal runtime: {time.time()-t_start:.1f}s")


if __name__ == "__main__":
    main()
