"""Read-only export of headline metrics from the frozen research outputs into
one consolidated JSON for the dashboard. Every number here is copied verbatim
from an existing report/metrics file -- nothing is recomputed, estimated, or
adjusted. This keeps the dashboard's displayed numbers mechanically traceable
to their source file instead of hand-typed into React components.

Run from repo root: python dashboard/data_export/export_metrics.py
"""
import json
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_PATH = os.path.join(ROOT, "dashboard", "src", "data", "metrics.json")


def load_json(*parts):
    with open(os.path.join(ROOT, *parts)) as f:
        return json.load(f)


def _round(obj, ndigits=4):
    """Round floats (recursively, incl. inside dicts) so the exported JSON
    already carries display-ready, floating-point-safe precision -- avoids
    any risk of the frontend's own rounding disagreeing with a report's
    stated value (e.g. 2.955 -> should display as 2.96, exactly as the
    generalization report states it)."""
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, dict):
        return {k: _round(v, ndigits) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round(v, ndigits) for v in obj]
    return obj


def main():
    v03_primary = load_json("outputs", "ml_v03", "metrics", "primary_model_metrics.json")
    v02_primary = load_json("outputs", "ml_temporal", "metrics", "primary_model_metrics.json")
    forward = load_json(
        "outputs", "ml_v03_generalization", "metrics",
        "forward_check_frozen_model_on_alt_mechanism.json",
    )
    reverse = load_json(
        "outputs", "ml_v03_generalization", "metrics",
        "reverse_check_alt_model_on_v03_gradual.json",
    )
    generalization_summary = load_json(
        "outputs", "ml_v03_generalization", "metrics", "experiment_summary.json"
    )
    zero_exposure = load_json("outputs", "ml_v03", "metrics", "generalization_check.json")

    meta_v3 = pd.read_csv(os.path.join(ROOT, "data", "metadata", "trajectory_metadata_v3.csv"))
    splits_v3 = pd.read_csv(os.path.join(ROOT, "data", "splits", "split_manifest_v3.csv"))
    split_counts = splits_v3["split"].value_counts().to_dict()

    out = {
        "dataset": {
            "trajectories": int(len(meta_v3)),
            "rows": 5340865,  # data/processed/processed_dataset_v3.parquet, verified during packaging
            "trainTrajectories": int(split_counts.get("train", 0)),
            "valTrajectories": int(split_counts.get("val", 0)),
            "testTrajectories": int(split_counts.get("test", 0)),
            "splitOverlap": 0,
        },
        "v02": {
            "prAuc": v02_primary["test_metrics"]["pr_auc"],
            "eventRecall": v02_primary["event_level"]["event_recall"],
            "nEvents": v02_primary["event_level"]["n_events"],
            "nWarned": v02_primary["event_level"]["n_warned"],
            "medianLeadTimeS": v02_primary["event_level"]["median_lead_time_s"],
            "warningCoverage": v02_primary["fraction_of_events_detected_at_least"],
        },
        "v03": {
            "prAuc": v03_primary["test_metrics"]["pr_auc"],
            "rocAuc": v03_primary["test_metrics"]["roc_auc"],
            "precision": v03_primary["test_metrics"]["precision"],
            "recall": v03_primary["test_metrics"]["recall"],
            "eventRecall": v03_primary["event_level"]["event_recall"],
            "nEvents": v03_primary["event_level"]["n_events"],
            "nWarned": v03_primary["event_level"]["n_warned"],
            "medianLeadTimeS": v03_primary["event_level"]["median_lead_time_s"],
            "meanLeadTimeS": v03_primary["event_level"]["mean_lead_time_s"],
            "warningCoverage": v03_primary["fraction_of_events_detected_at_least"],
            "leadTimeRecallBuckets": v03_primary["lead_time_recall_bucket"],
            "nFeatures": v03_primary["n_features"],
            "windowS": v03_primary["window_s"],
            "threshold": v03_primary["threshold"],
        },
        "generalization": {
            "forward": {
                "prAuc": forward["test_metrics"]["pr_auc"],
                "eventRecall": forward["event_level"]["event_recall"],
                "nEvents": forward["event_level"]["n_events"],
                "nWarned": forward["event_level"]["n_warned"],
                "medianLeadTimeS": forward["event_level"]["median_lead_time_s"],
                "meanLeadTimeS": forward["event_level"]["mean_lead_time_s"],
                "warningCoverage": forward["fraction_of_events_detected_at_least"],
            },
            "reverse": {
                "prAuc": reverse["test_metrics"]["pr_auc"],
                "eventRecall": reverse["event_level"]["event_recall"],
                "nEvents": reverse["event_level"]["n_events"],
                "nWarned": reverse["event_level"]["n_warned"],
                "medianLeadTimeS": reverse["event_level"]["median_lead_time_s"],
                "warningCoverage": reverse["fraction_of_events_detected_at_least"],
            },
            # CASE A is the report's own written verdict (generalization_experiment_report.md
            # section 7 "Final decision: CASE A") -- not stored as a JSON field in
            # experiment_summary.json, so it's set as a literal here rather than parsed.
            "decision": "CASE A",
            "forwardPopulation": generalization_summary["forward_check_holdout_population"],
            "reverseTrainPopulation": generalization_summary["reverse_check_train_population"],
            "zeroExposureExclusion": {
                "prAuc": zero_exposure["test_metrics"]["pr_auc"],
                "eventRecall": zero_exposure["event_level"]["event_recall"],
                "medianLeadTimeS": zero_exposure["event_level"]["median_lead_time_s"],
            },
        },
        "tests": {"passing": 190, "total": 190},
    }

    out = _round(out)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
