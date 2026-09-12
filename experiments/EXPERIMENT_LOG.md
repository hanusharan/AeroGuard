# AeroGuard Experiment Log

Chronological record of the major research stages behind the frozen v1.0 result.

This log records the documented experiments already completed in this repository. It does not introduce new measurements.

## v0.1 — Initial dataset

**Objective:** establish the first end-to-end trajectory dataset.

**Configuration:** 1,000 trajectories: 500 normal, 250 stall, 250 boundary.

**Result:** 1,565,280 rows; 187/1,000 trajectories crossed the stall boundary.

**Interpretation:** the initial dataset established the pipeline but produced a short physical precursor.

**Primary artifacts:** `scripts/generate_dataset.py`, `outputs/dataset_audit/`.

## v0.2 — Corrected dataset

**Objective:** improve dataset correctness and establish the canonical instantaneous ML baseline.

**Changes:** boundary regime renamed to near_boundary; ground-contact detection added; control-profile calibration revised.

**Result:** 1,000 trajectories; 1,753,615 rows; baseline RandomForest test PR-AUC 0.742.

**Interpretation:** the corrected dataset supported the baseline ML result and exposed the short precursor problem more clearly.

**Primary artifacts:** `scripts/generate_dataset_v2.py`, `outputs/dataset_audit_v2/`, `outputs/ml_baseline/`.

## v0.2 — Temporal early-warning experiment

**Objective:** determine whether temporal features provide useful warning lead time.

**Model:** RandomForest; 23 temporal features; causal one-step derivatives plus a 1-second causal window.

**Result:** PR-AUC 0.813; event recall 100% (14/14); median credited lead 0.53s.

**Problem observed:** warning performance was concentrated near the stall boundary rather than several seconds ahead of it.

**Interpretation:** the model behaved primarily as an imminent-event detector.

**Primary artifact:** `outputs/ml_temporal/temporal_experiment_report.md`.

## Precursor diagnosis

**Objective:** determine whether the sub-second precursor was caused by the simulator physics or by the way control inputs were generated.

**Method:** trajectory-aligned analysis of angle of attack, elevator input, stall margin, and variable separability at multiple lead times.

**Result:** the fast control profiles drove rapid movement through the precursor region; the underlying dynamics could support slower approach behavior.

**Interpretation:** the short warning window was diagnosed as a control-profile timing artifact rather than evidence of a hard physics limit.

**Primary artifacts:** `outputs/precursor_diagnosis/`, `scripts/precursor_diagnosis.py`, `scripts/diagnose_precursor.py`.

## v0.3 — Control-profile intervention

**Objective:** create a genuine multi-second physical precursor without modifying the validated physics engine or stall boundary.

**Change:** slow and re-time the elevator profile while retaining the same underlying aircraft dynamics.

**Result:** 3,150 trajectories; 5,340,865 rows; 4.38s median physical precursor.

**Interpretation:** the intervention demonstrated that the earlier short precursor was controllable through the input-generation design.

**Primary artifacts:** `scripts/generate_dataset_v3.py`, `outputs/dataset_audit_v3/`, `outputs/v03_calibration/`.

## v0.3 — Final temporal ML experiment

**Objective:** evaluate multi-second early-warning performance on the frozen v0.3 dataset.

**Model:** RandomForest temporal classifier; 23 features; 1-second causal window.

**Result:** PR-AUC 0.890; event recall 96.1% (73/76); median credited lead 4.72s.

**Interpretation:** the model achieved multi-second warning performance on the held-out trajectory-level test set.

**Important distinction:** the 4.38s physical precursor is a property of the dataset; the 4.72s credited lead is an event-level model metric.

**Primary artifacts:** `outputs/ml_v03/`, `outputs/ml_v03/models/primary_model_D_1s.joblib`.

## Zero-exposure exclusion

**Objective:** test whether the model can produce multi-second warnings with zero exposure to the broader slow-approach phenomenon during training.

**Result:** PR-AUC 0.552; event recall 64.5%; median credited lead 0.73s.

**Interpretation:** multi-second performance collapses without training exposure to the phenomenon class.

**Conclusion:** the result is not universal zero-shot prediction.

**Primary artifact:** `outputs/ml_v03/metrics/generalization_check.json`.

## Forward cross-mechanism transfer

**Objective:** test the frozen v0.3 model on a structurally distinct control-input mechanism that was not used for training.

**Protocol:** freeze the v0.3 model; evaluate on a novel single-pulse precursor mechanism.

**Result:** PR-AUC 0.835; event recall 100% (46/46); median credited lead 2.96s.

**Interpretation:** the learned warning signal transfers across structurally different control-input mechanisms within the same broad physical phenomenon.

**Primary artifact:** `outputs/ml_v03_generalization/`.

## Reverse cross-mechanism transfer

**Objective:** test transfer in the opposite direction.

**Protocol:** train on the novel mechanism only; evaluate on v0.3's gradual-approach regime.

**Result:** PR-AUC 0.708; event recall 87.0% (47/54); median credited lead 5.00s (horizon cap).

**Interpretation:** transfer is bidirectional, although asymmetric.

**Primary artifact:** `outputs/ml_v03_generalization/`.

## Final decision

**Decision:** CASE A.

The combined evidence supports multi-second stall early-warning and transfer across structurally distinct control-input mechanisms producing the same underlying physical phenomenon.

It does not establish universal zero-shot stall prediction across arbitrary unseen flight regimes.

## Frozen v1.0 status

No new physics model, dataset generation, hyperparameter tuning, or additional experiment is represented by this log.

A future v0.4 should be a separate research stage focused on aircraft-parameter generalization rather than another unpublished extension of v1.0.
