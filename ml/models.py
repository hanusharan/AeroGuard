"""Model builders and their (deliberately small) TRAIN/VAL hyperparameter grids.

Section 9-11: Logistic Regression (interpretable baseline), Random Forest
(nonlinear interactions), and gradient boosting. No xgboost/lightgbm is
installed in this environment (checked before writing this module); per
the instructions, sklearn's own HistGradientBoostingClassifier is used
instead of adding a new dependency -- it is well-supported and, unlike
plain GradientBoostingClassifier, designed to be fast on datasets this
size (~900k rows).
"""

from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from . import config


def build_logistic_regression(C: float, class_weight) -> Pipeline:
    """StandardScaler + LogisticRegression. The scaler is part of the
    pipeline so training.py's "fit only on TRAIN" discipline is
    automatic: pipeline.fit(X_train, y_train) fits the scaler on X_train
    only, and transform() on val/test reuses those fitted statistics."""
    return Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(
            C=C, class_weight=class_weight, max_iter=1000,
            random_state=config.ML_SEED, solver="lbfgs",
        )),
    ])


def build_random_forest(n_estimators: int, max_depth, min_samples_leaf: int, class_weight) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=n_estimators, max_depth=max_depth, min_samples_leaf=min_samples_leaf,
        class_weight=class_weight, random_state=config.ML_SEED, n_jobs=-1,
    )


def build_gradient_boosting(max_iter: int, max_depth, learning_rate: float, class_weight) -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        max_iter=max_iter, max_depth=max_depth, learning_rate=learning_rate,
        class_weight=class_weight, random_state=config.ML_SEED,
    )


# Deliberately small, documented grids (Section 10/11: "reasonable,
# computationally modest ... do not perform an enormous search").
LOGISTIC_REGRESSION_GRID = [
    {"C": 0.1, "class_weight": "balanced"},
    {"C": 1.0, "class_weight": "balanced"},
    {"C": 10.0, "class_weight": "balanced"},
    {"C": 1.0, "class_weight": None},
]

RANDOM_FOREST_GRID = [
    {"n_estimators": 200, "max_depth": 12, "min_samples_leaf": 5, "class_weight": "balanced_subsample"},
    {"n_estimators": 200, "max_depth": 20, "min_samples_leaf": 5, "class_weight": "balanced_subsample"},
    {"n_estimators": 300, "max_depth": 20, "min_samples_leaf": 2, "class_weight": "balanced_subsample"},
]

GRADIENT_BOOSTING_GRID = [
    {"max_iter": 150, "max_depth": 6, "learning_rate": 0.1, "class_weight": "balanced"},
    {"max_iter": 300, "max_depth": 6, "learning_rate": 0.05, "class_weight": "balanced"},
    {"max_iter": 150, "max_depth": 10, "learning_rate": 0.1, "class_weight": "balanced"},
]

MODEL_BUILDERS = {
    "logistic_regression": (build_logistic_regression, LOGISTIC_REGRESSION_GRID),
    "random_forest": (build_random_forest, RANDOM_FOREST_GRID),
    "gradient_boosting": (build_gradient_boosting, GRADIENT_BOOSTING_GRID),
}
