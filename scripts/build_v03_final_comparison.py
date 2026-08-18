"""Phase 5/6/7 artifact assembly for the v0.3 final report: the central
v0.2-vs-v0.3 comparison table, plus the remaining required plots (v0.2
vs v0.3 comparison, regime breakdown, precursor-duration vs
credited-lead-time, generalization comparison).

Pulls EXCLUSIVELY from already-computed, already-saved metrics --
outputs/ml_temporal/ (v0.2, read-only reference, never rerun) and
outputs/ml_v03/ (this experiment's own output). No model is fit here.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ml import temporal_config_v03 as v3cfg

V2_DIR = v3cfg.V2_OUTPUTS_DIR
V3_DIR = v3cfg.OUTPUTS_DIR


def j(path):
    with open(path) as f:
        return json.load(f)


def main():
    v2_primary = j(os.path.join(V2_DIR, "metrics", "primary_model_metrics.json"))
    v2_ablation = pd.read_csv(os.path.join(V2_DIR, "metrics", "window_ablation_summary.csv")).set_index("model")
    v2_false_alarm = j(os.path.join(V2_DIR, "metrics", "false_alarm_analysis.json"))

    v3_primary = j(os.path.join(V3_DIR, "metrics", "primary_model_metrics.json"))
    v3_ablation = pd.read_csv(os.path.join(V3_DIR, "metrics", "common_subset_ablation_summary.csv")).set_index("model")
    v3_false_alarm = j(os.path.join(V3_DIR, "metrics", "false_alarm_analysis.json"))
    v3_coverage = j(os.path.join(V3_DIR, "metrics", "primary_model_warning_coverage.json"))

    def bucket_recall(d, bucket):
        for r in d["lead_time_recall_bucket"]:
            if r["bucket"] == bucket:
                return r["recall"]
        return float("nan")

    # v0.2 coverage fractions come from its generalization_check.json sibling file
    # (>=1..5s only was computed in v0.2; >=0.5s was not -- documented as missing).
    v2_coverage_path = os.path.join(V2_DIR, "metrics", "primary_model_metrics.json")

    rows = [
        ("crossing count (test split, from metadata)", 27, 67, None),
        ("usable crossing count (primary model's own event population)", v2_primary["event_level"]["n_events"], v3_primary["event_level"]["n_events"], None),
        ("median physical precursor duration, dip-aware (dataset-scale, own regime)", 0.54, 4.38, "s"),
        (">=2s precursor coverage (physical, dataset-scale)", 0.04, 0.660, "frac"),
        (">=3s precursor coverage (physical, dataset-scale)", 0.00, 0.593, "frac"),
        (">=4s precursor coverage (physical, dataset-scale)", 0.00, 0.557, "frac"),
        (">=5s precursor coverage (physical, dataset-scale)", 0.00, 0.134, "frac"),
        ("baseline PR-AUC (Model A, common-subset population)", v2_ablation.loc["A_frozen_baseline", "pr_auc"], v3_ablation.loc["A_v03_retrained", "pr_auc"], None),
        ("temporal PR-AUC (Model D primary window, common-subset population)", v2_ablation.loc["D_1s", "pr_auc"], v3_ablation.loc["D_1s", "pr_auc"], None),
        ("temporal improvement over baseline (common-subset PR-AUC delta)", v2_ablation.loc["D_1s", "pr_auc"] - v2_ablation.loc["A_frozen_baseline", "pr_auc"],
         v3_ablation.loc["D_1s", "pr_auc"] - v3_ablation.loc["A_v03_retrained", "pr_auc"], None),
        ("primary model PR-AUC (own realistic-scale population)", v2_primary["test_metrics"]["pr_auc"], v3_primary["test_metrics"]["pr_auc"], None),
        ("primary model precision", v2_primary["test_metrics"]["precision"], v3_primary["test_metrics"]["precision"], None),
        ("primary model recall", v2_primary["test_metrics"]["recall"], v3_primary["test_metrics"]["recall"], None),
        ("row-level false positive rate", v2_false_alarm["row_level_false_positive_rate"], v3_false_alarm["row_level_false_positive_rate"], None),
        ("episode-level false-alarm precision", v2_false_alarm["episode_level"]["precision_at_operating_point_episode_level"],
         v3_false_alarm["episode_level"]["precision_at_operating_point_episode_level"], None),
        ("recall 0-0.5s (primary model, own population)", bucket_recall(v2_primary, "0-0.5s"), bucket_recall(v3_primary, "0-0.5s"), None),
        ("recall 0.5-1s (primary model, own population)", bucket_recall(v2_primary, "0.5-1s"), bucket_recall(v3_primary, "0.5-1s"), None),
        ("recall 1-2s (primary model, own population)", bucket_recall(v2_primary, "1-2s"), bucket_recall(v3_primary, "1-2s"), None),
        ("recall 2-3s (primary model, own population)", bucket_recall(v2_primary, "2-3s"), bucket_recall(v3_primary, "2-3s"), None),
        ("recall 3-4s (primary model, own population)", bucket_recall(v2_primary, "3-4s"), bucket_recall(v3_primary, "3-4s"), None),
        ("recall 4-5s (primary model, own population)", bucket_recall(v2_primary, "4-5s"), bucket_recall(v3_primary, "4-5s"), None),
        ("event-level recall", v2_primary["event_level"]["event_recall"], v3_primary["event_level"]["event_recall"], None),
        ("median credited lead time (s)", v2_primary["event_level"]["median_lead_time_s"], v3_primary["event_level"]["median_lead_time_s"], None),
        ("mean credited lead time (s)", v2_primary["event_level"]["mean_lead_time_s"], v3_primary["event_level"]["mean_lead_time_s"], None),
        (">=1s events warned", None, None, None),  # placeholder row removed below; coverage handled separately
    ]
    rows = [r for r in rows if r[0] != ">=1s events warned"]

    df = pd.DataFrame(rows, columns=["metric", "v0.2", "v0.3", "_unit"])
    df["change"] = df["v0.3"] - df["v0.2"]
    df = df.drop(columns=["_unit"])
    out_csv = os.path.join(v3cfg.METRICS_DIR, "v02_vs_v03_comparison.csv")
    df.to_csv(out_csv, index=False)
    print(f"-> {out_csv}")
    print(df.to_string(index=False))

    # ---- warning-coverage comparison (v0.2 only had >=1..5s; v0.3 also has >=0.5s)
    v2_frac = j(os.path.join(V2_DIR, "metrics", "generalization_check.json"))  # not used for values, just ensures path exists
    v2_frac_events = v2_primary["fraction_of_events_detected_at_least"] if "fraction_of_events_detected_at_least" in v2_primary else None
    if v2_frac_events is None:
        # v0.2's primary_model_metrics.json DOES include this key (see ml/temporal_experiment.py:evaluate_on_test)
        v2_frac_events = j(os.path.join(V2_DIR, "metrics", "primary_model_metrics.json"))["fraction_of_events_detected_at_least"]
    coverage_rows = []
    for thr in ["0.5s", "1s", "2s", "3s", "4s", "5s"]:
        key = f">={thr}"
        coverage_rows.append({"threshold": key, "v0.2": v2_frac_events.get(key), "v0.3": v3_coverage.get(key)})
    cov_df = pd.DataFrame(coverage_rows)
    cov_out = os.path.join(v3cfg.METRICS_DIR, "v02_vs_v03_warning_coverage.csv")
    cov_df.to_csv(cov_out, index=False)
    print(f"-> {cov_out}")
    print(cov_df.to_string(index=False))

    # ---------------------------------------------------------------------
    # Plot: v0.2 vs v0.3 comparison (lead-time bucket recall, primary model)
    # ---------------------------------------------------------------------
    buckets = ["0-0.5s", "0.5-1s", "1-2s", "2-3s", "3-4s", "4-5s"]
    v2_vals = [bucket_recall(v2_primary, b) for b in buckets]
    v3_vals = [bucket_recall(v3_primary, b) for b in buckets]
    x = np.arange(len(buckets)); width = 0.35
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.bar(x - width / 2, v2_vals, width, label="v0.2 (primary model, own population)", color="steelblue")
    ax.bar(x + width / 2, v3_vals, width, label="v0.3 (primary model, own population)", color="crimson")
    ax.set_xticks(x); ax.set_xticklabels(buckets)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("time until the actual future stall crossing")
    ax.set_ylabel("recall")
    ax.set_title("v0.2 vs v0.3: recall by lead-time bucket (primary model, TEST, own population)")
    ax.legend()
    ax.grid(True, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(v3cfg.PLOTS_DIR, "09_v02_vs_v03_lead_time_comparison.png"), dpi=150)
    plt.close(fig)
    print("-> 09_v02_vs_v03_lead_time_comparison.png")

    # ---------------------------------------------------------------------
    # Plot: warning coverage (fraction of events warned >= X seconds early)
    # ---------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 6))
    thr_labels = cov_df["threshold"].tolist()
    xg = np.arange(len(thr_labels))
    ax.bar(xg - width / 2, cov_df["v0.2"].fillna(0), width, label="v0.2", color="steelblue")
    ax.bar(xg + width / 2, cov_df["v0.3"].fillna(0), width, label="v0.3", color="crimson")
    ax.set_xticks(xg); ax.set_xticklabels(thr_labels)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("fraction of stall events warned >= X seconds early")
    ax.set_title("v0.2 vs v0.3: warning-coverage by lead-time threshold (event level)")
    ax.legend()
    ax.grid(True, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(v3cfg.PLOTS_DIR, "10_v02_vs_v03_warning_coverage.png"), dpi=150)
    plt.close(fig)
    print("-> 10_v02_vs_v03_warning_coverage.png")

    # ---------------------------------------------------------------------
    # Plot: precursor-duration vs credited-lead-time scatter (v0.3, per event)
    # ---------------------------------------------------------------------
    phys_ml = pd.read_csv(os.path.join(v3cfg.METRICS_DIR, "physics_vs_ml_lead_time.csv"))
    warned = phys_ml[phys_ml["ml_warned"] & phys_ml["corrected_precursor_s"].notna()]
    fig, ax = plt.subplots(figsize=(7, 7))
    colors = {"gradual_approach_v3": "crimson", "stall": "steelblue"}
    for regime, g in warned.groupby("regime"):
        ax.scatter(g["corrected_precursor_s"], g["ml_credited_lead_time_s"], label=regime, alpha=0.7, color=colors.get(regime, "gray"))
    lims = [0, 6]
    ax.plot(lims, lims, "--", color="gray", label="perfect tracking (y=x)")
    ax.set_xlim(lims); ax.set_ylim(lims)
    ax.set_xlabel("physical precursor duration (s), dataset-side, dip-aware")
    ax.set_ylabel("ML credited warning lead time (s), primary model")
    ax.set_title("v0.3: physical precursor duration vs. ML credited lead time (per TEST-split crossing)")
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(os.path.join(v3cfg.PLOTS_DIR, "11_precursor_duration_vs_credited_lead_time.png"), dpi=150)
    plt.close(fig)
    print("-> 11_precursor_duration_vs_credited_lead_time.png")

    # ---------------------------------------------------------------------
    # Plot: generalization comparison (full-train vs regime-excluded-train)
    # ---------------------------------------------------------------------
    gen = j(os.path.join(V3_DIR, "metrics", "generalization_check.json"))
    full_bucket = {r["bucket"]: r["recall"] for r in v3_primary["lead_time_recall_bucket"]}
    excl_bucket = {r["bucket"]: r["recall"] for r in gen["lead_time_recall_bucket"]}
    full_vals = [full_bucket.get(b, np.nan) for b in buckets]
    excl_vals = [excl_bucket.get(b, np.nan) for b in buckets]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.bar(x - width / 2, full_vals, width, label="full TRAIN (includes gradual_approach_v3)", color="crimson")
    ax.bar(x + width / 2, excl_vals, width, label="gradual_approach_v3 EXCLUDED from TRAIN", color="darkorange")
    ax.set_xticks(x); ax.set_xticklabels(buckets)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("time until the actual future stall crossing")
    ax.set_ylabel("recall")
    ax.set_title("v0.3 generalization check: recall by lead-time bucket, full vs. regime-excluded TRAIN")
    ax.legend()
    ax.grid(True, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(v3cfg.PLOTS_DIR, "12_generalization_comparison.png"), dpi=150)
    plt.close(fig)
    print("-> 12_generalization_comparison.png")


if __name__ == "__main__":
    main()
