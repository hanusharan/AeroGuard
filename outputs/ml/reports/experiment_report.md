# AeroGuard Stage 3 -- ML Early-Warning Experiment Report

**This experiment evaluates ML prediction within the AeroGuard simulation environment; it does not establish real-aircraft performance.** It does not constitute flight-ready or production aviation software, and makes no claim of real-aircraft validation or safety certification.

Dataset version: `stage2-v0.2-calibration`  
ML seed: `20260817`

## Dataset / split sizes
- **train**: 1,235,889 total rows, 893,482 with target available, 892,830 in the common A/B/C subset
- **val**: 255,890 total rows, 183,102 with target available, 182,965 in the common A/B/C subset
- **test**: 261,836 total rows, 188,189 with target available, 188,051 in the common A/B/C subset

## Class distribution (common subset)
- **train**: 59,021 positive (6.61%), 833,809 negative (93.39%)
- **val**: 18,929 positive (10.35%), 164,036 negative (89.65%)
- **test**: 9,855 positive (5.24%), 178,196 negative (94.76%)

## Baseline calibration (frozen before TEST)
- **AoA rule**: alpha > 14.445 deg (selected via TRAIN-F1 top-10 -> best VAL-F1=0.6236)
- **Trend rule**: stall_margin <= 5.245 deg AND dalpha_dt >= 0.000000 deg/s (selected via TRAIN-F1 top-10 -> best VAL-F1=0.4449)

## ML model hyperparameters (selected on VAL, frozen before TEST)
- **logistic_regression**: {'C': 1.0, 'class_weight': None}, probability threshold=0.3379
- **random_forest**: {'n_estimators': 200, 'max_depth': 12, 'min_samples_leaf': 5, 'class_weight': 'balanced_subsample'}, probability threshold=0.7731
- **gradient_boosting**: {'max_iter': 300, 'max_depth': 6, 'learning_rate': 0.05, 'class_weight': 'balanced'}, probability threshold=0.7816

## Primary model comparison table (TEST, single evaluation pass)
| Model | Feature Set | PR-AUC | Precision | Recall | F1 | Accuracy | Event Recall | Median Lead Time (s) | Mean Lead Time (s) | False Warning Rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AoA rule | alpha (rule) | 0.5984 | 0.9763 | 0.5049 | 0.6656 | 0.9734 | 1.0 | 0.06 | 0.076 | 0.125 |
| Trend rule | stall_margin + dalpha_dt (rule) | 0.5717 | 0.6582 | 0.3464 | 0.4539 | 0.9563 | 1.0 | 0.19 | 0.243 | 0.5172 |
| logistic_regression | C_state_dynamics | 0.6431 | 0.9029 | 0.5663 | 0.6961 | 0.9741 | 1.0 | 0.55 | 0.563 | 0.4 |
| random_forest | C_state_dynamics | 0.7501 | 0.7443 | 0.6516 | 0.6949 | 0.97 | 1.0 | 0.59 | 1.123 | 0.4634 |
| gradient_boosting | C_state_dynamics | 0.7166 | 0.6717 | 0.5955 | 0.6313 | 0.9636 | 1.0 | 0.57 | 0.766 | 0.7857 |

## Ablation table: Alpha-only vs State vs State+Dynamics
(model family: **random_forest**, same hyperparameters across all three conditions, refit on each feature set's own common-subset rows)

| Model | Feature Set | PR-AUC | Precision | Recall | F1 | Accuracy | Event Recall | Median Lead Time (s) | Mean Lead Time (s) | False Warning Rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_alpha_only | A_alpha_only | 0.5715 | 0.9171 | 0.5119 | 0.6571 | 0.972 | 1.0 | 0.115 | 0.326 | None |
| B_state | B_state | 0.7371 | 0.6225 | 0.6262 | 0.6243 | 0.9605 | 1.0 | 0.58 | 0.946 | None |
| C_state_dynamics | C_state_dynamics | 0.7501 | 0.7443 | 0.6516 | 0.6949 | 0.97 | 1.0 | 0.59 | 1.123 | None |

## Feature importance (random_forest, native_feature_importances)
- alpha: 0.14811
- elevator: 0.14459
- stall_margin: 0.13250
- pitch_rate: 0.07900
- theta: 0.07896
- dalpha_dt: 0.07061
- gamma: 0.06411
- vertical_speed: 0.06127
- V: 0.05849
- dV_dt: 0.05784
- altitude: 0.04310
- thrust: 0.03112
- throttle: 0.03030

## Integrity confirmations
- No trajectory_id appears in more than one of train/val/test (asserted programmatically at run start).
- No future-derived column (future_stall_5s, future_stall_5s_available, is_unsafe) is present in any feature set (asserted in ml/features.py at import time).
- dV_dt/dalpha_dt are the same causal backward-difference features verified in the Stage-2 dataset audit; no centered/future window is used.
- All rule thresholds, model hyperparameters, and probability thresholds were selected using TRAIN/VAL only and written to outputs/ml/metrics/test_lock.json BEFORE any TEST-set evaluation code ran.
- TEST was evaluated exactly once per model/rule/ablation condition, with no post-hoc re-tuning.