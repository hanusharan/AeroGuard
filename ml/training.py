"""TRAIN/VALIDATION model tuning and probability-threshold selection.

TEST is never touched by anything in this module (Section 9-12: "Tune
using TRAIN/VALIDATION only", "Do not use TEST during tuning").
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

import numpy as np
from sklearn.metrics import average_precision_score

from .calibration import select_threshold_train_then_val
from .models import MODEL_BUILDERS


@dataclass
class TunedModel:
    name: str
    model: Any
    hyperparameters: dict
    tuning_log: List[dict]
    probability_threshold: float = field(default=None)
    threshold_calibration_info: dict = field(default=None)

    def predict_proba_positive(self, X) -> np.ndarray:
        return self.model.predict_proba(X)[:, 1]

    def predict(self, X) -> np.ndarray:
        return (self.predict_proba_positive(X) > self.probability_threshold).astype(int)


def tune_model(model_name: str, X_train, y_train, X_val, y_val, verbose: bool = True) -> TunedModel:
    """Fit every candidate in the model's grid on TRAIN, score PR-AUC on
    VAL, keep the best-scoring fitted model. Then select a probability
    threshold via the shared TRAIN-then-VAL F1 procedure (Section 12)."""
    builder, grid = MODEL_BUILDERS[model_name]

    best_model = None
    best_params = None
    best_val_pr_auc = -np.inf
    tuning_log = []

    for params in grid:
        t0 = time.time()
        model = builder(**params)
        model.fit(X_train, y_train)
        val_proba = model.predict_proba(X_val)[:, 1]
        val_pr_auc = average_precision_score(y_val, val_proba)
        elapsed = time.time() - t0
        tuning_log.append({"params": params, "val_pr_auc": float(val_pr_auc), "fit_seconds": elapsed})
        if verbose:
            print(f"    {model_name} {params} -> val PR-AUC={val_pr_auc:.4f} ({elapsed:.1f}s)")
        if val_pr_auc > best_val_pr_auc:
            best_val_pr_auc = val_pr_auc
            best_model = model
            best_params = params

    train_proba = best_model.predict_proba(X_train)[:, 1]
    val_proba = best_model.predict_proba(X_val)[:, 1]
    threshold, threshold_info = select_threshold_train_then_val(y_train, train_proba, y_val, val_proba)

    return TunedModel(
        name=model_name,
        model=best_model,
        hyperparameters=best_params,
        tuning_log=tuning_log,
        probability_threshold=threshold,
        threshold_calibration_info=threshold_info,
    )
