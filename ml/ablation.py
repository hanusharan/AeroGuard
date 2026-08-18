"""Feature-set ablation (Section 17): Alpha-only vs State vs State+Dynamics.

Uses ONE model family (the best-performing model from the primary
comparison, by VAL PR-AUC on Feature Set C) with its ALREADY-SELECTED
hyperparameters, refit unchanged on each feature set's own data. Only
the input columns change between conditions -- the model type,
hyperparameters, and tuning procedure do not -- so any metric
difference between A/B/C isolates the feature effect, not a
confounding algorithm or tuning change.
"""

from typing import Dict

import numpy as np

from . import config
from .calibration import select_threshold_train_then_val
from .events import aggregate_event_results, compute_event_level_results
from .evaluation import compute_classification_metrics
from .features import common_subset_mask, get_xy
from .models import MODEL_BUILDERS


def run_ablation(model_name: str, hyperparameters: dict, dataset, verbose: bool = True) -> Dict[str, dict]:
    builder, _grid = MODEL_BUILDERS[model_name]
    train_df, val_df, test_df = dataset.split_df("train"), dataset.split_df("val"), dataset.split_df("test")
    n_test_traj = test_df["trajectory_id"].nunique()

    results = {}
    for feature_set_name, feature_columns in config.FEATURE_SETS.items():
        if verbose:
            print(f"  ablation condition: {feature_set_name} ({feature_columns})")

        X_train, y_train = get_xy(train_df, feature_columns, require_common_subset=True)
        X_val, y_val = get_xy(val_df, feature_columns, require_common_subset=True)
        X_test, y_test = get_xy(test_df, feature_columns, require_common_subset=True)

        model = builder(**hyperparameters)
        model.fit(X_train, y_train)

        train_proba = model.predict_proba(X_train)[:, 1]
        val_proba = model.predict_proba(X_val)[:, 1]
        threshold, threshold_info = select_threshold_train_then_val(y_train, train_proba, y_val, val_proba)

        test_proba = model.predict_proba(X_test)[:, 1]
        test_pred = (test_proba > threshold).astype(int)
        metrics = compute_classification_metrics(y_test, test_pred, test_proba)

        test_sub = test_df.loc[common_subset_mask(test_df)]
        event_results = compute_event_level_results(test_sub, test_pred, config.LABELING_HORIZON_S)
        event_agg = aggregate_event_results(event_results)

        results[feature_set_name] = {
            "feature_columns": feature_columns,
            "n_features": len(feature_columns),
            "threshold": threshold,
            "threshold_info": threshold_info,
            "test_metrics": metrics,
            "event_level": event_agg,
        }
        if verbose:
            print(f"    PR-AUC={metrics['pr_auc']:.4f} F1={metrics['f1']:.4f} event_recall={event_agg['event_recall']:.3f} "
                  f"median_lead={event_agg['median_lead_time_s']}")

    return results
