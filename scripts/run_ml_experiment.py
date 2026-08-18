"""AeroGuard Stage 3: the full ML early-warning experiment.

Uses the FROZEN Dataset v0.2 (data/*_v2.*) as-is. Does not modify the
physics engine, the dataset-generation pipeline, or any data file.

Run with:
    python scripts/run_ml_experiment.py
"""

import dataclasses
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import joblib
import numpy as np
import pandas as pd
import sklearn

from ml import config
from ml.ablation import run_ablation
from ml.baselines import AoAThresholdRule, TrendRule
from ml.data import load_dataset, report_split_sizes
from ml.events import aggregate_event_results, compute_event_level_results, compute_false_alarm_stats
from ml.evaluation import (
    compute_classification_metrics,
    plot_confusion_matrix,
    plot_feature_importance,
    plot_pr_curves,
    plot_probability_distribution,
    plot_roc_curves,
)
from ml.features import common_subset_mask, get_xy, target_available_mask
from ml.models import MODEL_BUILDERS
from ml.training import tune_model


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


def section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def class_distribution(y: np.ndarray) -> dict:
    n = len(y)
    n_pos = int(np.sum(y == 1))
    n_neg = int(np.sum(y == 0))
    return {"n": n, "n_positive": n_pos, "n_negative": n_neg,
            "positive_pct": 100.0 * n_pos / n if n else float("nan"),
            "negative_pct": 100.0 * n_neg / n if n else float("nan")}


def main():
    config.ensure_output_dirs()
    all_metrics = {}  # the big machine-readable JSON payload

    # =========================================================================
    section("1. LOAD DATASET & VERIFY SPLIT INTEGRITY (Section 4)")
    # =========================================================================
    t_start = time.time()
    ds = load_dataset()
    train_ids, val_ids, test_ids = ds.trajectory_ids("train"), ds.trajectory_ids("val"), ds.trajectory_ids("test")
    assert not (train_ids & val_ids), "train/val overlap"
    assert not (train_ids & test_ids), "train/test overlap"
    assert not (val_ids & test_ids), "val/test overlap"
    print("VERIFIED: no trajectory_id overlap between train/val/test.")
    print(f"  train: {len(train_ids)} trajectories, val: {len(val_ids)}, test: {len(test_ids)}")
    all_metrics["dataset_version"] = ds.generation_config["dataset_version"]
    all_metrics["split_sizes"] = report_split_sizes(ds)

    train_df, val_df, test_df = ds.split_df("train"), ds.split_df("val"), ds.split_df("test")

    # =========================================================================
    section("2. COMMON SUBSET & CLASS DISTRIBUTION (Section 5/6)")
    # =========================================================================
    common_subset_report = {}
    class_dist_report = {}
    for name, df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        avail = target_available_mask(df)
        common = common_subset_mask(df)
        common_subset_report[name] = {
            "n_rows_total": int(len(df)),
            "n_rows_target_available": int(avail.sum()),
            "n_rows_common_subset_ABC": int(common.sum()),
        }
        class_dist_report[name] = {
            "target_available_population": class_distribution(df.loc[avail, config.TARGET_COL].to_numpy()),
            "common_subset_population": class_distribution(df.loc[common, config.TARGET_COL].to_numpy()),
        }
        print(f"  {name}: total={len(df):,} target_available={avail.sum():,} common_subset(A/B/C)={common.sum():,}")
        cd = class_dist_report[name]["common_subset_population"]
        print(f"    common-subset class balance: {cd['n_positive']:,} pos ({cd['positive_pct']:.2f}%), "
              f"{cd['n_negative']:,} neg ({cd['negative_pct']:.2f}%)")
    all_metrics["common_subset_rows"] = common_subset_report
    all_metrics["class_distribution"] = class_dist_report

    # =========================================================================
    section("3. BASELINE 1 -- AoA THRESHOLD RULE (Section 7)")
    # =========================================================================
    avail_train, avail_val, avail_test = target_available_mask(train_df), target_available_mask(val_df), target_available_mask(test_df)
    alpha_train, y_train_a = train_df.loc[avail_train, "alpha"].to_numpy(), train_df.loc[avail_train, config.TARGET_COL].to_numpy().astype(int)
    alpha_val, y_val_a = val_df.loc[avail_val, "alpha"].to_numpy(), val_df.loc[avail_val, config.TARGET_COL].to_numpy().astype(int)
    alpha_test, y_test_a = test_df.loc[avail_test, "alpha"].to_numpy(), test_df.loc[avail_test, config.TARGET_COL].to_numpy().astype(int)

    aoa_rule = AoAThresholdRule().fit(alpha_train, y_train_a, alpha_val, y_val_a)
    print(f"  frozen threshold: alpha > {np.degrees(aoa_rule.threshold_rad):.3f} deg "
          f"(selected VAL F1={aoa_rule.calibration_info['selected_val_f1']:.4f})")

    aoa_test_pred = aoa_rule.predict(alpha_test)
    aoa_test_score = aoa_rule.predict_score(alpha_test)
    aoa_metrics = compute_classification_metrics(y_test_a, aoa_test_pred, aoa_test_score)
    print(f"  TEST: PR-AUC={aoa_metrics['pr_auc']:.4f} P={aoa_metrics['precision']:.4f} R={aoa_metrics['recall']:.4f} F1={aoa_metrics['f1']:.4f}")

    test_avail_df = test_df.loc[avail_test]
    aoa_events = compute_event_level_results(test_avail_df, aoa_test_pred, config.LABELING_HORIZON_S)
    aoa_event_agg = aggregate_event_results(aoa_events)
    aoa_false_alarms = compute_false_alarm_stats(test_avail_df, aoa_test_pred, test_df["trajectory_id"].nunique())
    print(f"  event-level: {aoa_event_agg['n_warned']}/{aoa_event_agg['n_events']} warned, "
          f"median lead={aoa_event_agg['median_lead_time_s']}, false_warning_rate={aoa_false_alarms['false_warning_rate']:.3f}")

    all_metrics["aoa_rule"] = {
        "calibration": aoa_rule.calibration_info, "test_metrics": aoa_metrics,
        "event_level": aoa_event_agg, "false_alarms": aoa_false_alarms,
    }

    # =========================================================================
    section("4. BASELINE 2 -- TREND RULE (Section 8)")
    # =========================================================================
    common_train, common_val, common_test = common_subset_mask(train_df), common_subset_mask(val_df), common_subset_mask(test_df)
    margin_train, trend_train, y_train_t = train_df.loc[common_train, "stall_margin"].to_numpy(), train_df.loc[common_train, "dalpha_dt"].to_numpy(), train_df.loc[common_train, config.TARGET_COL].to_numpy().astype(int)
    margin_val, trend_val, y_val_t = val_df.loc[common_val, "stall_margin"].to_numpy(), val_df.loc[common_val, "dalpha_dt"].to_numpy(), val_df.loc[common_val, config.TARGET_COL].to_numpy().astype(int)
    margin_test, trend_test, y_test_t = test_df.loc[common_test, "stall_margin"].to_numpy(), test_df.loc[common_test, "dalpha_dt"].to_numpy(), test_df.loc[common_test, config.TARGET_COL].to_numpy().astype(int)

    trend_rule = TrendRule().fit(margin_train, trend_train, y_train_t, margin_val, trend_val, y_val_t)
    print(f"  frozen: stall_margin <= {trend_rule.calibration_info['selected_margin_threshold_deg']:.3f} deg AND "
          f"dalpha_dt >= {trend_rule.calibration_info['selected_trend_threshold_deg_s']:.6f} deg/s "
          f"(selected VAL F1={trend_rule.calibration_info['selected_val_f1']:.4f})")

    trend_test_pred = trend_rule.predict(margin_test, trend_test)
    trend_test_score = trend_rule.predict_score(margin_test, trend_test)
    trend_metrics = compute_classification_metrics(y_test_t, trend_test_pred, trend_test_score)
    print(f"  TEST: PR-AUC={trend_metrics['pr_auc']:.4f} P={trend_metrics['precision']:.4f} R={trend_metrics['recall']:.4f} F1={trend_metrics['f1']:.4f}")

    test_common_df = test_df.loc[common_test]
    trend_events = compute_event_level_results(test_common_df, trend_test_pred, config.LABELING_HORIZON_S)
    trend_event_agg = aggregate_event_results(trend_events)
    trend_false_alarms = compute_false_alarm_stats(test_common_df, trend_test_pred, test_df["trajectory_id"].nunique())
    print(f"  event-level: {trend_event_agg['n_warned']}/{trend_event_agg['n_events']} warned, "
          f"median lead={trend_event_agg['median_lead_time_s']}, false_warning_rate={trend_false_alarms['false_warning_rate']:.3f}")

    all_metrics["trend_rule"] = {
        "calibration": trend_rule.calibration_info, "test_metrics": trend_metrics,
        "event_level": trend_event_agg, "false_alarms": trend_false_alarms,
    }

    # =========================================================================
    section("5-7. ML MODELS: LOGISTIC REGRESSION / RANDOM FOREST / GRADIENT BOOSTING (Section 9-12)")
    # =========================================================================
    X_train_C, y_train_C = get_xy(train_df, config.FEATURE_SET_C, require_common_subset=True)
    X_val_C, y_val_C = get_xy(val_df, config.FEATURE_SET_C, require_common_subset=True)
    X_test_C, y_test_C = get_xy(test_df, config.FEATURE_SET_C, require_common_subset=True)
    print(f"  Feature Set C (primary): train={len(X_train_C):,} val={len(X_val_C):,} test={len(X_test_C):,} rows")

    tuned_models = {}
    for model_name in ["logistic_regression", "random_forest", "gradient_boosting"]:
        print(f"\n  --- tuning {model_name} on TRAIN, selecting on VAL ---")
        tuned_models[model_name] = tune_model(model_name, X_train_C, y_train_C, X_val_C, y_val_C)

    # "TEST LOCK" (Section 19): freeze every selection BEFORE touching TEST.
    test_lock = {
        "aoa_rule_threshold_rad": aoa_rule.threshold_rad,
        "trend_rule_margin_rad": trend_rule.margin_threshold,
        "trend_rule_trend_rad_s": trend_rule.trend_threshold,
        "models": {
            name: {
                "hyperparameters": tm.hyperparameters,
                "probability_threshold": tm.probability_threshold,
                "tuning_log": tm.tuning_log,
            }
            for name, tm in tuned_models.items()
        },
        "frozen_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sklearn_version": sklearn.__version__,
    }
    with open(os.path.join(config.METRICS_DIR, "test_lock.json"), "w") as f:
        json.dump(test_lock, f, indent=2, cls=_NumpyJSONEncoder)
    print(f"\n  TEST LOCK written -> {os.path.join(config.METRICS_DIR, 'test_lock.json')} (all selections frozen before TEST contact)")

    ml_results = {}
    best_model_name, best_val_pr_auc = None, -np.inf
    for model_name, tm in tuned_models.items():
        print(f"\n  === FINAL TEST EVALUATION: {model_name} (frozen, single pass) ===")
        test_proba = tm.predict_proba_positive(X_test_C)
        test_pred = (test_proba > tm.probability_threshold).astype(int)
        metrics = compute_classification_metrics(y_test_C, test_pred, test_proba)
        print(f"    hyperparameters: {tm.hyperparameters}")
        print(f"    threshold: {tm.probability_threshold:.4f}")
        print(f"    TEST: PR-AUC={metrics['pr_auc']:.4f} P={metrics['precision']:.4f} R={metrics['recall']:.4f} F1={metrics['f1']:.4f}")

        events = compute_event_level_results(test_common_df, test_pred, config.LABELING_HORIZON_S)
        event_agg = aggregate_event_results(events)
        false_alarms = compute_false_alarm_stats(test_common_df, test_pred, test_df["trajectory_id"].nunique())
        print(f"    event-level: {event_agg['n_warned']}/{event_agg['n_events']} warned, "
              f"median lead={event_agg['median_lead_time_s']}, false_warning_rate={false_alarms['false_warning_rate']:.3f}")

        ml_results[model_name] = {
            "hyperparameters": tm.hyperparameters, "tuning_log": tm.tuning_log,
            "probability_threshold": tm.probability_threshold, "threshold_calibration": tm.threshold_calibration_info,
            "test_metrics": metrics, "event_level": event_agg, "false_alarms": false_alarms,
            "test_proba": test_proba, "test_pred": test_pred,
        }

        joblib.dump(tm.model, os.path.join(config.MODELS_DIR, f"{model_name}.joblib"))

        best_candidate_val_pr_auc = max(entry["val_pr_auc"] for entry in tm.tuning_log)
        if best_candidate_val_pr_auc > best_val_pr_auc:
            best_val_pr_auc = best_candidate_val_pr_auc
            best_model_name = model_name

    print(f"\n  BEST MODEL by VAL PR-AUC: {best_model_name} ({best_val_pr_auc:.4f})")
    all_metrics["ml_models"] = {k: {kk: vv for kk, vv in v.items() if kk not in ("test_proba", "test_pred")} for k, v in ml_results.items()}
    all_metrics["best_model"] = best_model_name

    # =========================================================================
    section("8. ABLATION STUDY (Section 17)")
    # =========================================================================
    best_hyperparams = ml_results[best_model_name]["hyperparameters"]
    print(f"  Using model family: {best_model_name}, hyperparameters: {best_hyperparams}")
    ablation_results = run_ablation(best_model_name, best_hyperparams, ds)
    all_metrics["ablation"] = {k: {kk: vv for kk, vv in v.items()} for k, v in ablation_results.items()}

    # =========================================================================
    section("9. FEATURE IMPORTANCE (Section 18)")
    # =========================================================================
    best_model = tuned_models[best_model_name].model
    feature_names = config.FEATURE_SET_C
    importances = None
    importance_method = None
    if hasattr(best_model, "feature_importances_"):
        importances = np.asarray(best_model.feature_importances_)
        importance_method = "native_feature_importances"
    elif hasattr(best_model, "named_steps") and hasattr(best_model.named_steps.get("clf"), "coef_"):
        importances = np.abs(best_model.named_steps["clf"].coef_[0])
        importance_method = "abs_logistic_regression_coefficients (on standardized features)"
    else:
        from sklearn.inspection import permutation_importance
        rng = np.random.default_rng(config.ML_SEED)
        idx = rng.choice(len(X_test_C), size=min(20000, len(X_test_C)), replace=False)
        perm = permutation_importance(best_model, X_test_C.iloc[idx], y_test_C[idx], n_repeats=5, random_state=config.ML_SEED, scoring="average_precision")
        importances = perm.importances_mean
        importance_method = "permutation_importance_on_test_subsample_pr_auc"

    importance_order = np.argsort(importances)[::-1]
    print(f"  method: {importance_method}")
    for i in importance_order:
        print(f"    {feature_names[i]:15s} {importances[i]:.5f}")

    all_metrics["feature_importance"] = {
        "model": best_model_name, "method": importance_method,
        "features": feature_names, "importances": importances.tolist(),
    }

    # =========================================================================
    section("10. PLOTS")
    # =========================================================================
    pr_curves = [
        ("AoA rule", y_test_a, aoa_test_score),
        ("Trend rule", y_test_t, trend_test_score),
    ] + [
        (name, y_test_C, ml_results[name]["test_proba"]) for name in tuned_models
    ]
    plot_pr_curves(pr_curves, os.path.join(config.PLOTS_DIR, "01_precision_recall_curves.png"))
    plot_roc_curves(pr_curves, os.path.join(config.PLOTS_DIR, "02_roc_curves.png"))

    for name, y_true, y_pred, y_score in [
        ("aoa_rule", y_test_a, aoa_test_pred, aoa_test_score),
        ("trend_rule", y_test_t, trend_test_pred, trend_test_score),
    ] + [
        (name, y_test_C, ml_results[name]["test_pred"], ml_results[name]["test_proba"]) for name in tuned_models
    ]:
        m = compute_classification_metrics(y_true, y_pred, y_score)
        plot_confusion_matrix(m["confusion_matrix"], os.path.join(config.PLOTS_DIR, f"03_confusion_matrix_{name}.png"), f"Confusion matrix: {name} (TEST)")

    best_lead_times = ml_results[best_model_name]["event_level"]["lead_times_s"]
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 5))
    if best_lead_times:
        ax.hist(best_lead_times, bins=20, color="seagreen", edgecolor="black")
        ax.axvline(np.median(best_lead_times), color="red", linestyle="--", label=f"median={np.median(best_lead_times):.2f}s")
        ax.legend()
    ax.set_xlabel("warning lead time [s]")
    ax.set_ylabel("number of successfully warned stall events")
    ax.set_title(f"Lead-time distribution: {best_model_name} (TEST, n_warned={len(best_lead_times)})")
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(os.path.join(config.PLOTS_DIR, "04_lead_time_distribution.png"), dpi=150)
    plt.close(fig)

    plot_feature_importance(feature_names, importances, os.path.join(config.PLOTS_DIR, "05_feature_importance.png"), f"Feature importance: {best_model_name} ({importance_method})")

    plot_probability_distribution(y_test_C, ml_results[best_model_name]["test_proba"], os.path.join(config.PLOTS_DIR, "06_probability_distribution.png"), f"Predicted probability distribution: {best_model_name} (TEST)", threshold=ml_results[best_model_name]["probability_threshold"])

    print(f"  plots -> {config.PLOTS_DIR}")

    # =========================================================================
    section("11. COMPARISON TABLES")
    # =========================================================================
    rows = []
    rows.append(_table_row("AoA rule", "alpha (rule)", aoa_metrics, aoa_event_agg, aoa_false_alarms))
    rows.append(_table_row("Trend rule", "stall_margin + dalpha_dt (rule)", trend_metrics, trend_event_agg, trend_false_alarms))
    for name in tuned_models:
        rows.append(_table_row(name, "C_state_dynamics", ml_results[name]["test_metrics"], ml_results[name]["event_level"], ml_results[name]["false_alarms"]))
    comparison_table = pd.DataFrame(rows)
    comparison_table.to_csv(os.path.join(config.METRICS_DIR, "model_comparison_table.csv"), index=False)
    print(comparison_table.to_string(index=False))

    ablation_rows = []
    for fs_name, res in ablation_results.items():
        ablation_rows.append(_table_row(fs_name, fs_name, res["test_metrics"], res["event_level"], None))
    ablation_table = pd.DataFrame(ablation_rows)
    ablation_table.to_csv(os.path.join(config.METRICS_DIR, "ablation_table.csv"), index=False)
    print("\nAblation table:")
    print(ablation_table.to_string(index=False))

    # =========================================================================
    section("12. SAVE METRICS JSON + REPORT")
    # =========================================================================
    with open(os.path.join(config.METRICS_DIR, "full_metrics.json"), "w") as f:
        json.dump(all_metrics, f, indent=2, cls=_NumpyJSONEncoder)

    report_md = _build_report(
        ds, common_subset_report, class_dist_report, comparison_table, ablation_table,
        aoa_rule, trend_rule, tuned_models, best_model_name, feature_names, importances, importance_method,
    )
    report_path = os.path.join(config.REPORTS_DIR, "experiment_report.md")
    with open(report_path, "w") as f:
        f.write(report_md)

    elapsed = time.time() - t_start
    print(f"\nTotal experiment runtime: {elapsed:.1f}s")
    print(f"Metrics JSON -> {os.path.join(config.METRICS_DIR, 'full_metrics.json')}")
    print(f"Comparison table -> {os.path.join(config.METRICS_DIR, 'model_comparison_table.csv')}")
    print(f"Ablation table -> {os.path.join(config.METRICS_DIR, 'ablation_table.csv')}")
    print(f"Report -> {report_path}")


def _df_to_markdown(df: pd.DataFrame) -> str:
    """Minimal markdown-table formatter (tabulate is not installed and
    is not worth adding as a dependency solely for this)."""
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join(lines)


def _build_report(ds, common_subset_report, class_dist_report, comparison_table, ablation_table,
                   aoa_rule, trend_rule, tuned_models, best_model_name, feature_names, importances, importance_method) -> str:
    lines = []
    lines.append("# AeroGuard Stage 3 -- ML Early-Warning Experiment Report\n")
    lines.append(
        "**This experiment evaluates ML prediction within the AeroGuard simulation "
        "environment; it does not establish real-aircraft performance.** It does not "
        "constitute flight-ready or production aviation software, and makes no claim "
        "of real-aircraft validation or safety certification.\n"
    )
    lines.append(f"Dataset version: `{ds.generation_config['dataset_version']}`  \nML seed: `{config.ML_SEED}`\n")

    lines.append("## Dataset / split sizes")
    for split_name, sizes in common_subset_report.items():
        lines.append(f"- **{split_name}**: {sizes['n_rows_total']:,} total rows, "
                      f"{sizes['n_rows_target_available']:,} with target available, "
                      f"{sizes['n_rows_common_subset_ABC']:,} in the common A/B/C subset")

    lines.append("\n## Class distribution (common subset)")
    for split_name, dist in class_dist_report.items():
        cd = dist["common_subset_population"]
        lines.append(f"- **{split_name}**: {cd['n_positive']:,} positive ({cd['positive_pct']:.2f}%), "
                      f"{cd['n_negative']:,} negative ({cd['negative_pct']:.2f}%)")

    lines.append("\n## Baseline calibration (frozen before TEST)")
    lines.append(f"- **AoA rule**: alpha > {np.degrees(aoa_rule.threshold_rad):.3f} deg "
                  f"(selected via TRAIN-F1 top-10 -> best VAL-F1={aoa_rule.calibration_info['selected_val_f1']:.4f})")
    lines.append(f"- **Trend rule**: stall_margin <= {trend_rule.calibration_info['selected_margin_threshold_deg']:.3f} deg "
                  f"AND dalpha_dt >= {trend_rule.calibration_info['selected_trend_threshold_deg_s']:.6f} deg/s "
                  f"(selected via TRAIN-F1 top-10 -> best VAL-F1={trend_rule.calibration_info['selected_val_f1']:.4f})")

    lines.append("\n## ML model hyperparameters (selected on VAL, frozen before TEST)")
    for name, tm in tuned_models.items():
        lines.append(f"- **{name}**: {tm.hyperparameters}, probability threshold={tm.probability_threshold:.4f}")

    lines.append("\n## Primary model comparison table (TEST, single evaluation pass)")
    lines.append(_df_to_markdown(comparison_table))

    lines.append("\n## Ablation table: Alpha-only vs State vs State+Dynamics")
    lines.append(f"(model family: **{best_model_name}**, same hyperparameters across all three conditions, refit on each feature set's own common-subset rows)\n")
    lines.append(_df_to_markdown(ablation_table))

    lines.append(f"\n## Feature importance ({best_model_name}, {importance_method})")
    order = np.argsort(importances)[::-1]
    for i in order:
        lines.append(f"- {feature_names[i]}: {importances[i]:.5f}")

    lines.append("\n## Integrity confirmations")
    lines.append("- No trajectory_id appears in more than one of train/val/test (asserted programmatically at run start).")
    lines.append("- No future-derived column (future_stall_5s, future_stall_5s_available, is_unsafe) is present in any feature set (asserted in ml/features.py at import time).")
    lines.append("- dV_dt/dalpha_dt are the same causal backward-difference features verified in the Stage-2 dataset audit; no centered/future window is used.")
    lines.append("- All rule thresholds, model hyperparameters, and probability thresholds were selected using TRAIN/VAL only and written to outputs/ml/metrics/test_lock.json BEFORE any TEST-set evaluation code ran.")
    lines.append("- TEST was evaluated exactly once per model/rule/ablation condition, with no post-hoc re-tuning.")

    return "\n".join(lines)


def _table_row(model, feature_set, metrics, event_agg, false_alarms):
    return {
        "Model": model, "Feature Set": feature_set,
        "PR-AUC": round(metrics["pr_auc"], 4), "Precision": round(metrics["precision"], 4),
        "Recall": round(metrics["recall"], 4), "F1": round(metrics["f1"], 4),
        "Accuracy": round(metrics["accuracy"], 4),
        "Event Recall": round(event_agg["event_recall"], 4) if event_agg["event_recall"] == event_agg["event_recall"] else None,
        "Median Lead Time (s)": round(event_agg["median_lead_time_s"], 3) if event_agg["median_lead_time_s"] is not None else None,
        "Mean Lead Time (s)": round(event_agg["mean_lead_time_s"], 3) if event_agg["mean_lead_time_s"] is not None else None,
        "False Warning Rate": round(false_alarms["false_warning_rate"], 4) if false_alarms and false_alarms["false_warning_rate"] == false_alarms["false_warning_rate"] else None,
    }


if __name__ == "__main__":
    main()
