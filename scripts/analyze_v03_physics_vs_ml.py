"""Phase 9: physics-vs-ML consistency for the v0.3 final report.

Compares, per TEST-split crossing trajectory, the PHYSICAL precursor
duration (outputs/dataset_audit_v3/v3_precursor_classification.csv --
dataset-side, computed independently of any model) against the ML
CREDITED warning lead time from the primary model
(outputs/ml_v03/models/primary_model_D_1s.joblib). Loads the already-
saved model and refits nothing.

Never modifies aeroguard/, data/processed/, data/splits/, data/ml/,
data/ml_temporal/, outputs/ml_temporal/, or the v0.3 dataset. Writes
only under outputs/ml_v03/.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import joblib
import numpy as np
import pandas as pd

from ml import temporal_config_v03 as v3cfg
from ml.events import compute_event_level_results
from ml.temporal_data_v03 import load_temporal_splits
from ml.temporal_experiment import NumpyJSONEncoder, get_xy
from ml.temporal_features import usable_mask_for_window


def main():
    splits = load_temporal_splits(force=False, verbose=False)
    test = splits["test"]
    window_s = v3cfg.PRIMARY_WINDOW_S
    feats = v3cfg.model_d_features(window_s)
    test_mask = usable_mask_for_window(test, window_s)
    Xte, yte, test_sub = get_xy(test, feats, test_mask)

    model = joblib.load(os.path.join(v3cfg.MODELS_DIR, f"primary_model_D_{v3cfg._fmt(window_s)}s.joblib"))
    with open(os.path.join(v3cfg.OUTPUTS_DIR, "experiment_config.json")) as f:
        thr = json.load(f)["primary_model_threshold"]
    proba = model.predict_proba(Xte)[:, 1]
    pred = (proba > thr).astype(int)

    event_results = compute_event_level_results(test_sub, pred, v3cfg.LABELING_HORIZON_S)
    ml_events_all = pd.DataFrame([
        {"trajectory_id": r.trajectory_id, "crossing_time": r.crossing_time, "ml_warned": r.warned, "ml_credited_lead_time_s": r.lead_time_s}
        for r in event_results
    ])
    n_multi = (ml_events_all["trajectory_id"].value_counts() > 1).sum()
    print(f"note: {n_multi} test trajectories have >1 stall episode (is_unsafe re-entered); "
          f"physics classification (v3_precursor_classification.csv) covers the FIRST crossing only, "
          f"so this join uses the FIRST (earliest crossing_time) ML episode per trajectory too, for a fair 1:1 comparison.")
    ml_events = ml_events_all.sort_values("crossing_time").groupby("trajectory_id", as_index=False).first()

    physical = pd.read_csv(os.path.join(v3cfg.V2_PRECURSOR_DIR, "v3_precursor_classification.csv"))
    split_manifest = pd.read_csv(v3cfg.SPLIT_MANIFEST_PATH)
    physical_test = physical.merge(split_manifest, on="trajectory_id", how="inner")
    physical_test = physical_test[physical_test["split"] == "test"]

    merged = physical_test.merge(ml_events, on="trajectory_id", how="left")
    # trajectories with a physical crossing but no ML row-level prediction available
    # (e.g. crossing occurs within the first window_steps(1s) rows -- excluded by
    # usable_mask_for_window, consistent with every other stage of this experiment)
    merged["ml_row_population_available"] = merged["ml_credited_lead_time_s"].notna() | merged["ml_warned"].notna()
    merged["ml_warned"] = merged["ml_warned"].fillna(False)

    out_path = os.path.join(v3cfg.METRICS_DIR, "physics_vs_ml_lead_time.csv")
    merged.to_csv(out_path, index=False)
    print(f"-> {out_path}  ({len(merged)} test-split crossing trajectories)")

    summary = {}
    for regime, g in merged.groupby("regime"):
        usable = g[g["ml_row_population_available"]]
        both = usable.dropna(subset=["corrected_precursor_s"])
        warned = both[both["ml_warned"]]
        corr = float(np.corrcoef(warned["corrected_precursor_s"], warned["ml_credited_lead_time_s"])[0, 1]) if len(warned) >= 3 else None
        summary[regime] = {
            "n_test_crossings": int(len(g)),
            "n_usable_for_ml": int(len(usable)),
            "n_with_physical_precursor_estimate": int(both["corrected_precursor_s"].notna().sum()),
            "n_ml_warned": int(usable["ml_warned"].sum()),
            "median_physical_precursor_s": float(both["corrected_precursor_s"].median()) if len(both) else None,
            "median_ml_credited_lead_time_s_warned_only": float(warned["ml_credited_lead_time_s"].median()) if len(warned) else None,
            "mean_physical_precursor_s": float(both["corrected_precursor_s"].mean()) if len(both) else None,
            "mean_ml_credited_lead_time_s_warned_only": float(warned["ml_credited_lead_time_s"].mean()) if len(warned) else None,
            "pearson_r_physical_vs_credited_lead_time": corr,
            "n_paired_for_correlation": int(len(warned)),
        }
    save_path = os.path.join(v3cfg.METRICS_DIR, "physics_vs_ml_summary.json")
    with open(save_path, "w") as f:
        json.dump(summary, f, indent=2, cls=NumpyJSONEncoder)
    print(f"-> {save_path}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
