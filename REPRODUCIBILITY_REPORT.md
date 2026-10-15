# AeroGuard v0.3 Reproducibility Report

*Roadmap Item 27. Simulation-only research. Prepared with the assistance of Claude Code at the author's direction (see §15). Nothing in this report is a statement about real aircraft.*

**Evidence labels used throughout.**
**[Stored]** a value read from a tracked historical artifact.
**[Reproduced]** a value from the Item 26 check on regenerated data.
**[Derived]** a value computed from stored records or regenerated records.
**[Interpretation]**, **[Hypothesis]** and **[Recommendation]** are judgements, not observations.

---

## 1. Purpose and Scope

This report consolidates what is known about whether the frozen AeroGuard v0.3 evaluation can be reproduced. It records what was checked, how, what matched, what did not match or could not be checked, and how a reader can repeat the parts that can be repeated.

Three different things must not be merged into one claim of "reproducibility":

| | Concept | What it is here | Status |
|---|---|---|---|
| **A** | Historical v0.3 evaluation | The results stored in the repository from the original v0.3 run (`outputs/ml_v03/`). | Stored; origin dates undocumented. |
| **B** | Item 26 reproduction | The frozen model re-evaluated on a v0.3 dataset **regenerated** from the tracked code and seed (RL-006, 2026-10-13). | Done; all preregistered gates passed. |
| **C** | Independent replication | A separate implementation or study by someone other than the original experimenter. | **Not done.** |

**What this report establishes:** the stored v0.3 numbers are internally consistent; the evaluated population can be reconstructed from tracked metadata alone; and the frozen model, applied with the strict `>` operator to a regenerated dataset, reproduces the stored confusion matrix and ROC-AUC exactly and the stored PR-AUC within 8.39e-11.

**What it does not establish:** that the original run's predictions were bit-for-bit identical (the original score arrays were never saved); that the threshold was chosen as the code says (the original selection record was not saved); that any result is correct for real aircraft; or anything about independent replication.

Related records: the how-to guide is [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md); the dated reasoning trail is [`RESEARCH_LOG.md`](RESEARCH_LOG.md) (RL-001 to RL-006 are the primary evidence for this report); the baseline manifest is [`baselines/v0.3.sha256`](baselines/v0.3.sha256) with [`baselines/README.md`](baselines/README.md).

---

## 2. Research and Evaluation Overview

- **System.** A simulated 2D longitudinal fixed-wing flight model (RK4 integration). No real flight, wind-tunnel or telemetry data was used at any stage (see the README's Limitations).
- **Dataset v0.3** [Stored]: 3,150 trajectories, 5,340,865 rows, time step 0.01 s, seed 20260823, dataset version `stage2-v0.3-full`. Regimes: `normal` 500, `stall` 250, `gradual_approach_v3` 2,400 (`scripts/generate_dataset_v3.py:65-68`; `data/metadata/trajectory_metadata_v3.csv`).
- **Unsafe state.** A sample is unsafe when `|alpha|` exceeds the angle of attack at the peak of the modelled lift curve (`aeroguard_dataset/events.py:35-41`, strict `>`).
- **Label.** `future_stall_5s` is 1 if any sample in `(t, t + 5 s]` is unsafe, 0 if not, and unavailable for the last 500 rows of a trajectory (`aeroguard_dataset/labeling.py:26-55`).
- **Split.** Trajectory-level 70/15/15: 2,205 train, 472 validation, 473 test trajectories, by a seeded shuffle of the sorted trajectory IDs (`aeroguard_dataset/splitting.py:20-46`; `data/splits/split_manifest_v3.csv`).
- **Model.** A RandomForest (200 trees, depth 12, minimum leaf 5, `class_weight=balanced_subsample`, seed 20260817) on 23 causal features with a 1.0 s history window (§6, §7).
- **Evaluated population.** Only rows with an available label and a full 1.0 s feature window are scored: 538,034 test rows from 456 of the 473 test trajectories (46,169 positive, 491,865 negative).
- **Event metrics.** An event is a maximal run of unsafe samples inside the evaluated rows; a warning episode is a maximal run of positive predictions; lead time is `min(crossing − earliest qualifying episode start, 5 s)` with no persistence requirement (`ml/events.py:49-102`).

---

## 3. Artifact Inventory and Integrity

### 3.1 Tracked artifacts that define the v0.3 baseline

SHA-256 prefixes are the first 16 hex characters. "Manifest" means the file is one of the 79 entries of `baselines/v0.3.sha256`. All files below were byte-identical to `HEAD` when this report was written.

| Artifact | Role | Manifest | SHA-256 prefix |
|---|---|---|---|
| `outputs/ml_v03/models/primary_model_D_1s.joblib` | Frozen model (full hash below) | yes | `707d4c61a791af94` |
| `outputs/ml_v03/metrics/primary_model_metrics.json` | Row, bucket and event metrics; threshold; feature list | yes | `8bb4b8e42a224fe4` |
| `outputs/ml_v03/metrics/primary_model_warning_coverage.json` | Coverage at 0.5–5 s | yes | `7ad61215271606dd` |
| `outputs/ml_v03/experiment_config.json` | Seed, windows, RF parameters, `primary_model_threshold` | yes | `4c512a1e25774e91` |
| `outputs/ml_v03/v03_temporal_ml_report.md` | Original v0.3 report | yes | `f3b573e2b50a7ae6` |
| `outputs/ml_v03/metrics/false_alarm_analysis.json` | Warning episodes, false alarms | no | `60f6795abf84f5dd` |
| `outputs/ml_v03/metrics/physics_vs_ml_lead_time.csv`, `outputs/ml_v03/metrics/physics_vs_ml_summary.json` | Per-crossing records and regime summary | no | `ca97bf467cef44b8`, `69ce489f23d9c7fd` |
| `outputs/ml_v03/metrics/regime_breakdown.csv`, `outputs/ml_v03/metrics/airspeed_breakdown.csv` | Slices of the row metrics | no | `14d89e53b9a136d5`, `43d297ee8593a218` |
| `data/splits/split_manifest_v3.csv` | Trajectory split | yes | `d7d6eb825d10c6ac` |
| `data/metadata/trajectory_metadata_v3.csv` | Per-trajectory metadata (`n_steps`, regime, first stall time) | yes | `924e0df6ccb303a2` |
| `data/metadata/generation_config_v3.json`, `data/metadata/feature_schema_v3.json` | Generation config and schema | yes | `752acb2c64bf2074`, `54e435c84d7fdf89` |
| `dashboard/src/data/metrics.json`, `dashboard/src/data/flightReplay.json` | Dashboard export (4-decimal rounding) | no | `1faaab514b38bc4a`, `d28b96a73a5908a8` |

**Frozen model SHA-256:** `707d4c61a791af940549f81520a0c8429edaa8ef8d67eb0f02c3174c5fe603f3`. It records scikit-learn 1.9.0 (`outputs/ml/metrics/test_lock.json`, `sklearn_version`; see [`baselines/README.md`](baselines/README.md)).

**Baseline manifest.** `sha256sum -c baselines/v0.3.sha256` passed 79 of 79 entries when this report was written. The manifest covers the model, the v0.3 config, metadata and split manifest, four metric files, reports, the final report and status, the paper PDF, and the code under `aeroguard/`, `aeroguard_dataset/`, `ml/` and the v0.3 scripts. It does not cover the datasets (gitignored; no hash of the original files was ever recorded) or the files marked "no" above, which are checked here against `HEAD` instead.

**Uncommitted state.** `baselines/` and `requirements-pinned.txt` are new, untracked files at the time of writing; so are this report and `RESEARCH_LOG.md`. Nothing from Items 1–27 has been committed.

### 3.2 Regenerated scratch artifacts (not repository artifacts)

The Item 26 check produced these in a session scratch directory outside the repository. They are **temporary and may not persist**: the regenerated `processed_dataset_v3.parquet` (449,345,877 bytes); the three panels `temporal_{train,val,test}.parquet` (1,188,953,925, 246,442,707 and 261,347,990 bytes); four score arrays; event and comparison tables; and five scratch scripts (Appendix C). The score arrays are **not** the original predictions. The repository retains only the written record in RL-006.

---

## 4. Environment

| | Python | scikit-learn | joblib | NumPy | pandas | PyArrow | SciPy | Matplotlib |
|---|---|---|---|---|---|---|---|---|
| **Item 26 reproduction** [RL-006] | 3.12.3 | 1.9.0 | 1.6.0 | 2.5.4 | 3.0.6 | 26.0.0 | 1.18.1 | 3.11.2 |
| **`requirements-pinned.txt`** | CPython 3.12 (tested) | 1.9.0 | 1.6.0 | 2.5.4 | 3.0.6 | 26.0.0 | 1.18.1 | 3.11.2 |
| **Historical original** | not recorded | **1.9.0** (embedded in the model and in `outputs/ml/metrics/test_lock.json`) | not recorded | not recorded | not recorded | not recorded | not recorded | not recorded |

- The Item 26 versions equal the pins for the seven packages checked. The Item 26 interpreter also contained other packages (for example CFF and browser tooling), none used by the pipeline.
- `requirements-pinned.txt` is a newly tested environment, **not** a reconstruction of the original one. Only the scikit-learn version has recorded evidence for the original run. A different pandas or NumPy version in the original environment could in principle have changed panel values; the regenerated panel counts and metrics matched anyway, but this is not proof that nothing differed.
- Item 26 observed resource use: dataset generation 465.7 s with a 2.5 GB peak; panel build 95.1 s with a 5.5 GB peak; scoring 1.6 GB peak.
- The shipped `requirements.txt` has loose lower bounds and was not re-tested.

---

## 5. Dataset Generation and Splitting

- **Source logic.** `scripts/generate_dataset_v3.py` constructs the config (seed 20260823, 3,150 trajectories, regime counts above) and calls `aeroguard_dataset.dataset_builder_v3.build_dataset_v3` (line 138), which draws every trajectory from a single `numpy.random.default_rng(seed)` stream in sequence. A subset (for example test only) therefore cannot be generated without altering the code.
- **Splitting.** `split_trajectory_ids` is a function of the sorted trajectory IDs and the seed alone; the tracked manifests regenerate exactly from them (`tests/test_audit_labels_features_splits.py`).
- **How Item 26 regenerated the data.** A scratch-only wrapper imported the unchanged constants from `scripts/generate_dataset_v3.py` and called the unchanged `build_dataset_v3` with the same configuration expression. It wrote only the processed parquet and compared the regenerated metadata and manifest with the tracked files in memory. It skipped the raw parquet, the audit report, the plots and all v0.2 data. **The wrapper is not a supported command-line tool and is not in the repository.** The unchanged `scripts/generate_dataset_v3.py` was run in the earlier RL-001 check (2026-10-12; about 520 s), with an identical manifest.
- **Panels.** Built with the unchanged `ml.temporal_data_v03.load_temporal_splits` (`ml/temporal_data_v03.py:80`), which always builds all three splits.

**Preregistered acceptance gates and outcomes** (gates written in RL-006 before any data were generated):

| Gate | Criterion | Observed [Reproduced] | Result |
|---|---|---|---|
| A | 5,340,865 rows; 3,150 trajectories | 5,340,865; 3,150 | pass |
| A | Split manifest identical to tracked | text-identical | pass |
| A | Metadata within 1e-12 (non-numeric exact) | max relative difference 8.93e-13 (max absolute 4.55e-13, column `minimum_alpha`); no non-matching column | pass |
| B | Panel rows 3,749,572 / 771,995 / 819,298 | identical (52 columns each) | pass |
| B | Usable test rows 538,034; positives 46,169; negatives 491,865 | identical; 456 of 473 test trajectories have usable rows | pass |

The tolerance was applied as a relative difference, the form measured on 2026-10-12. The panel counts in the gate came from the unmerged `credibility-v1.1` branch's run log.

---

## 6. Feature and Label Construction

- **Features.** The model's 23 inputs are exactly `ml.temporal_config.model_d_features(1.0)`: eight instantaneous state and control channels (`V`, `alpha`, `gamma`, `pitch_rate`, `altitude`, `elevator`, `throttle`, `stall_margin`); five backward-difference derivatives (`dV_dt`, `dalpha_dt`, `dgamma_dt`, `dq_dt`, `d2alpha_dt2`); and ten 1.0 s windowed statistics (`alpha_mean/min/max/range/slope/trend`, `V_slope`, `gamma_slope`, `pitch_rate_slope`, `elevator_change`). The list is stored in `outputs/ml_v03/metrics/primary_model_metrics.json` (`feature_columns`) and equals the loaded model's `feature_names_in_` (checked by a test and by the Item 26 scoring script).
- **Causality.** Windows are trailing and computed per trajectory (`ml/temporal_features.py:143`). A window of 1.0 s needs 101 samples, so the first usable row is index 100. A test perturbs a single future sample in every raw channel and finds no change in any of the 23 inputs at earlier rows, with a non-causal control that is detected (`tests/test_audit_labels_features_splits.py`).
- **Label.** Defined above (§2). Boundary tests: exactly at the horizon is positive, one step beyond is not, the current sample does not count. Rows already inside an unsafe run are labelled positive while a later unsafe sample lies within the horizon.
- **Usability mask.** `usable_mask_for_window` (`ml/temporal_features.py:187`) keeps rows where the label is available and every temporal column is non-null. For a trajectory of `n_steps` rows this gives `max(0, n_steps − 600)` rows (500 unlabeled rows at the end, 100 rows without a full window at the start). Summing this over the tracked metadata reproduces the stored 2,443,881 / 491,322 / 538,034 rows and 456 of 473 test trajectories exactly (RL-005) [Derived].
- **Scope of these statements.** They rest on the implementation, the audit tests (36 tests, all passing when this report was written) and the existing suites (`tests/test_temporal_features.py`, `tests/test_temporal_v03_integrity.py`). Passing tests support software correctness; they do not validate the science.

---

## 7. Model and Threshold

- **Frozen model.** `outputs/ml_v03/models/primary_model_D_1s.joblib`, SHA-256 `707d4c61a791af940549f81520a0c8429edaa8ef8d67eb0f02c3174c5fe603f3`, scikit-learn 1.9.0. RF parameters in `ml/temporal_config_v03.py:81-86`; random seed 20260817; saved `n_jobs=-1`.
- **Threshold.** **0.8585534589255494** [Stored], identical in `outputs/ml_v03/experiment_config.json` (`primary_model_threshold`) and `outputs/ml_v03/metrics/primary_model_metrics.json` (`threshold`); the dashboard shows it rounded to 0.8586.
- **Operator.** A row is predicted positive when `probability > threshold` (strict), at `ml/temporal_experiment.py:109` inside `evaluate_on_test`. Other places use `>=` (the dashboard export, the `threshold_sweep` helper and the unmerged `credibility-v1.1` analysis script; RL-004 lists them). They do not define the published numbers. In the regenerated scores no value equals the threshold, so `>` and `>=` give identical predictions (§10).
- **Selection code path.** `run_primary_model_v03` (`ml/temporal_experiment_v03.py:141`) calls `fit_rf_and_threshold` (`ml/temporal_experiment.py:79-88`), which fits on train and calls `select_threshold_train_then_val` (`ml/calibration.py:27-49`): the 10 thresholds with the highest **train** F1 are scored on **validation** F1 and the best is kept. The selector takes no test argument (an existing test asserts this), and `evaluate_on_test` is called only after the threshold is returned. The train ranking uses the forest's scores on its own training rows. The threshold optimises row-level F1 of the label; it was not tuned for event recall, lead time or false alarms.
- **Hyperparameters and window.** The RF parameters were chosen from a two-configuration grid by validation PR-AUC on the v0.2 dataset (`outputs/ml_temporal/metrics/hyperparameter_tuning.json`) and reused unchanged. The v0.2 and v0.3 datasets share no trajectory ID and no identical initial-condition triple (RL-004). The 1.0 s primary window is commented "chosen a priori" in the code.

**Limitations retained from RL-004.**
1. The original v0.3 threshold **candidate list and validation F1 values were not saved**: `fit_rf_and_threshold` returns them as `thr_info`, but every v0.3 caller discards it (`ml/temporal_experiment_v03.py:60, 109, 122, 158, 219`).
2. **Historical chronology cannot be established** from current artifacts: the repository begins with one snapshot commit (2026-08-18), and the remote `pre-clean-history-backup` branch has the same lineage. "Pre-registered" and "chosen a priori" in code comments are the author's statements that Git cannot check.
3. The current code path **supports** the intended train-then-validation selection but **does not prove** that every historical action followed it. The stored threshold was not recomputed (that needs a retrain, which was not done).
4. The v0.3 test split was used repeatedly (ablation, generalization checks, physics-vs-ML, the dashboard replay, later analyses). None of these re-selected the primary threshold as far as the code shows. The replay trajectory `traj_00413` was chosen after seeing test results, for display only.

---

## 8. Historical Evaluation Results

All values [Stored]; source `outputs/ml_v03/metrics/primary_model_metrics.json` unless stated. Definitions are in §2 and §6.

### 8.1 Row level (538,034 evaluated test rows)

| Metric | Value |
|---|---|
| PR-AUC | 0.8902774777010881 |
| ROC-AUC | 0.9775387048062552 |
| Precision | 0.9348095172603493 |
| Recall (rows) | 0.7360999805064004 |
| F1 | 0.8236391837526053 |
| Accuracy | 0.9729496648910664 |
| False-positive rate | 0.00481839529139093 (`outputs/ml_v03/metrics/false_alarm_analysis.json`) |
| Confusion (tn / fp / fn / tp) | 489,495 / 2,370 / 12,184 / 33,985 |
| Positives / negatives | 46,169 / 491,865 |

Row recall by distance to the crossing (positive rows only; buckets `(lo, hi]` of `time_to_stall`):

| Bucket | Positive rows | Warned | Missed | Recall |
|---|---|---|---|---|
| 0–0.5 s | 20,547 | 19,967 | 580 | 0.9718 |
| 0.5–1 s | 3,725 | 2,593 | 1,132 | 0.6961 |
| 1–2 s | 6,790 | 4,199 | 2,591 | 0.6184 |
| 2–3 s | 5,621 | 2,709 | 2,912 | 0.4819 |
| 3–4 s | 5,109 | 2,397 | 2,712 | 0.4692 |
| 4–5 s | 4,372 | 2,117 | 2,255 | 0.4842 |
| **Sum** | **46,164** | **33,982** | **12,182** | |

The bucket sums fall 5 positive rows (3 warned, 2 missed) short of the confusion matrix. §12 explains this.

### 8.2 Event level

| Quantity | Value |
|---|---|
| Evaluated events | 76 |
| Warned / missed | 73 / 3 |
| **Event recall over the 76 evaluated events** | **96.05% (reported as 96.1%)** |
| Median credited lead time (warned events only) | 4.72 s |
| Mean / population SD / min / max (warned events only) | 3.424 s / 1.879 s / 0.14 s / 5.0 s |
| Warned events at the 5 s cap | 29 of 73 |
| Coverage of lead time ≥ 0.5 / 1 / 2 / 3 / 4 / 5 s (over all 76 events) | 70 / 55 / 49 / 45 / 42 / 29 events (0.921 / 0.724 / 0.645 / 0.592 / 0.553 / 0.382) |
| Warning episodes / true / false | 121 / 93 / 28 (episode precision 0.7686; 0.265 per trajectory; 0.3125 false alarms per minute) |

### 8.3 What 96.1% means, and what it does not

> **96.1% is not recall over all possible stall crossings.** It is 73 warned out of 76 events that lie inside the evaluated rows. The 4.72 s median is taken over the 73 warned events only; missed events have no lead time and are not counted in it.

- 456 of 473 test trajectories have evaluated rows; the other 17 have none.
- The test split holds 67 crossing trajectories. Ten of their first crossings occur in the last 5 s of the trajectory, where no label exists, so they are outside the evaluated rows. They count as neither warned nor missed. No recall for them was measured.
- The 76 events are 57 first events plus 19 later events (§11). The pooled figures mix the two groups.
- Lead time is capped at 5 s and uses the earliest qualifying warning episode with no minimum duration.

Regime slices (rows; positives; recall; precision; F1): `normal` 113,481 / 0 / n.a. / 0 / 0; `gradual_approach_v3` 396,207 / 30,001 / 0.8054 / 0.9339 / 0.8649; `stall` 28,346 / 16,168 / 0.6076 / 0.9999 / 0.7558 (`outputs/ml_v03/metrics/regime_breakdown.csv`). Regime is never a model input.

---

## 9. Item 26 Reproduction Procedure

Executed on 2026-10-13 (RL-006). The plan, gates and tolerances were written in RL-006 before any data were generated; results were appended afterwards under a separate heading, and the planned text was left unchanged.

1. **Baseline.** Branch `claude/loving-fermi-ql3cyo`, HEAD `66b5661`; 24 working-tree entries; 0 staged; 79 of 79 baseline hashes passing; a SHA-256 fingerprint of every modified or untracked file was recorded.
2. **Scratch copy.** Built with `git archive HEAD` (code, tracked metadata and split manifests, `outputs/ml_v03`) in a directory outside the repository. The scientific directories in the copy were identical to the working tree. Assertions before any generation: `ml` and `aeroguard_dataset.paths.PROJECT_ROOT` resolved inside the copy; no editable installation; the copy's model hash matched; at least 4 GB free (a conservative margin, not a measured minimum).
3. **Dataset regeneration** (§5), then **Gate A**.
4. **Panel build** with the unchanged repository function, then **Gate B**.
5. **Scoring.** A scratch-only script loaded the frozen model read-only and the stored threshold from `outputs/ml_v03/experiment_config.json`, used the repository's `get_xy`, `usable_mask_for_window` and `evaluate_on_test` (strict `>`), and scored the test rows four times: three runs with the model's saved `n_jobs=-1` and one with `n_jobs=1` (set on the in-memory object only). The model file hash was checked before and after. It also ran the repository's false-alarm, regime and airspeed functions, listed every event, and diagnosed the five-row discrepancy and the unsafe runs outside the evaluated rows.
6. **Gate C and comparison.** A comparison script compared 514 values (the metric artifacts, the dashboard export and cross-checks) with tolerances fixed beforehand: counts exact; PR-AUC, ROC-AUC and other floating-point values within 1e-9.
7. **Post-run integrity.** The repository fingerprint, the 79 baseline hashes and the model hash were rechecked; only `RESEARCH_LOG.md` differed from the pre-run state.

**Not done in Item 26:** no retraining, no threshold selection or sweep, no change to the frozen model, code or stored metrics, no independent environment, and no comparison against original score arrays (none exist). The unchanged `scripts/generate_dataset_v3.py` was not run in Item 26 (it was in RL-001).

---

## 10. Reproduction Results

| Quantity | Stored | Regenerated | Status |
|---|---|---|---|
| Rows / trajectories | 5,340,865 / 3,150 | same | exact |
| Split manifest | tracked | text-identical | exact |
| Metadata | tracked | max relative difference 8.93e-13 | within tolerance (1e-12) |
| Panel rows (train / val / test) | 3,749,572 / 771,995 / 819,298 | same | exact |
| Usable test rows; positives; negatives | 538,034; 46,169; 491,865 | same | exact |
| Confusion tn / fp / fn / tp | 489,495 / 2,370 / 12,184 / 33,985 | same in all 4 scoring variants | exact |
| ROC-AUC | 0.9775387048062552 | same in all 4 variants | exact |
| PR-AUC | 0.8902774777010881 | same in 3 variants; 0.8902774777849808 in saved-setting run 1 | exact in 3; within 1e-9 in 1 (difference 8.39e-11) |
| Precision, recall, F1, accuracy, row FPR | stored | same | exact |
| Lead-time buckets (6) | stored | same counts and recalls | exact |
| Events 76 / 73 / 3; recall; mean; SD; min; max | stored | same | exact |
| 73 lead times, median 4.72 s, 29 at the cap | stored | same | exact |
| Coverage counts (70, 55, 49, 45, 42, 29) | stored | same | exact |
| Warning episodes 121 / 93 / 28; regime and airspeed slices | stored | same | exact |
| Dashboard export (4-decimal values) | `dashboard/src/data/metrics.json` | equal after rounding | exact |
| 67 stored first-crossing records | `outputs/ml_v03/metrics/physics_vs_ml_lead_time.csv` | usable and warned flags, crossing times, leads agree | exact |
| RL-005 decomposition (first-event median 3.15 s) | stored to 2 decimals | 3.1500000000000004 | within tolerance (0.005, set before the run) |
| Original row-level scores or predictions | — | — | **not independently verifiable** (never saved) |
| Original threshold candidate list, validation F1 values | — | — | **not independently verifiable** (never saved) |

**Totals.** 444 gate-C comparisons, 0 differences. Counting the dashboard export and the cross-checks, 514 comparisons: 512 exact, 2 within tolerance, 0 differing. All three preregistered gates passed.

**Score-level variation (observation).** The four scoring runs differed in the last bits of the probabilities: 28,328 to 50,320 rows differed from run 1, by at most 4.4e-16. Run 1 had 132,489 distinct scores; the other three had 132,490. PR-AUC differed from the stored value (8.39e-11) in run 1 only; ROC-AUC did not change in any run. Row-level predictions were identical in all four variants. **The cause is not proven.** Reading scikit-learn's code, forest `predict_proba` with `n_jobs>1` adds tree outputs in thread-completion order, which is a plausible mechanism [Hypothesis], but `n_jobs=1` also differed from run 1 at the last bit, so it is untested. PR-AUC should be compared with a tolerance, not for exact equality.

**Strict `>` versus `>=`.** Exact ties at the threshold: 0 in every variant. The nearest scores were 0.85848739223472 and 0.858583256634222, 2.98e-5 from the threshold. Rows where `>` and `>=` differ: 0. On these scores the operators are interchangeable; this says nothing about the original arrays beyond the exact reproduction of the stored confusion matrix under strict `>`. The 2026-10-12 run (RL-001) applied `>=` and matched the event metrics; that alone was not evidence of row-level equality.

---

## 11. Event Population and Interpretation

All counts in this section were derived from the regenerated evaluation records (§9). They match the figures derived earlier from stored records (RL-005). **They do not prove that the original predictions were identical.**

| | First events | Later events | Pooled |
|---|---|---|---|
| Events | 57 | 19 | 76 |
| Warned | 54 (94.7%) | 19 (100%) | 73 (96.05%) |
| Missed | 3 | 0 | 3 |
| Median lead, warned (s) | **3.15** | **5.00** | **4.72** |
| Mean lead, warned (s) | 2.94 | 4.79 | 3.42 |
| Warned at the 5 s cap | 13 | 16 | 29 |
| Coverage ≥ 3 s | 27 / 57 | 18 / 19 | 45 / 76 |
| Coverage ≥ 5 s | 13 / 57 | 16 / 19 | 29 / 76 |

- **First events** are the first evaluated unsafe run in a trajectory (57 trajectories). The three misses (`traj_00314`, `traj_00593`, `traj_02024`) are all `gradual_approach_v3`.
- **Later events** are further unsafe runs after a trajectory re-enters the unsafe region (19; 14 `gradual_approach_v3`, 5 `stall`).
- **Shared warning episodes.** 16 of the 19 later events are credited to the **same warning episode** as the first event of their trajectory (16 episodes, each credited to two events, none to more than two). Of the 16 later events at the cap, 14 share that episode and 2 come from a different one; 2 events share an episode without being capped (4.98 s and 3.27 s); the remaining later event (`traj_00593`) follows a missed first event.
- **Effect on interpretation.** [Interpretation] Adding 19 mostly capped values to the 54 first-event values raises the pooled median from 3.15 s to 4.72 s. The pooled figures are correct under the stated definition. A reader who takes 4.72 s as the typical lead time before a *first* stall is overstating it; the stored results do not show why later events have long credited leads, although one long warning being credited to two events is the dominant pattern.
- **Outside the evaluated rows.** In the regenerated test data there are 90 unsafe runs in 67 trajectories; 76 have evaluated rows (the events) and 14 do not. The 14 are the **ten excluded first crossings** (8 `stall`, 2 `gradual_approach_v3`; each in the last 5 s of its trajectory) and **four additional later unsafe runs** (all `stall`: `traj_00355`, `traj_00979`, `traj_02168`, `traj_02682`, starting 0.41 to 2.58 s before the end), in trajectories whose first run was evaluated. **None of the ten excluded-first-crossing trajectories has any further unsafe run.** This answers, on regenerated data only, the question RL-003 left open.
- **[Recommendation]** Present first-event and pooled metrics together, with their sample sizes (57 and 19), and keep the historical pooled result unchanged. Do not replace 96.1% or 4.72 s with any other number.

---

## 12. Five-Row Lead-Time Bucket Discrepancy

The stored bucket counts sum to 46,164 positive rows against 46,169 in the confusion matrix. In the regenerated data, exactly five positive rows (`future_stall_5s = 1`, `is_unsafe = False`) have `time_to_stall = 5.000000000000001` s (5 plus 8.88e-16), so they lie outside the bucket `(4, 5]` although the integer-step label includes them:

| Trajectory | Time (s) | Score | Prediction |
|---|---|---|---|
| `traj_00824` | 3.29 | 0.4087 | missed |
| `traj_01165` | 4.55 | 0.9669 | warned |
| `traj_02121` | 4.63 | 0.9402 | warned |
| `traj_02187` | 3.37 | 0.9098 | warned |
| `traj_02891` | 5.70 | 0.7748 | missed |

Three warned and two missed, the same split as the stored files. `time_to_stall` is computed as a difference of floating-point times (`scripts/prepare_ml_dataset.py:118-139`) while the label uses an integer number of steps. **Scope:** this met the preregistered criterion for the explanation to count as *supported* on the regenerated data. It is **not** proven against the unsaved original score arrays. It does not change any stored headline metric (0.011% of positive rows).

---

## 13. Limitations and Open Questions

1. **No original row-level probability arrays** were saved; the regenerated scores cannot be compared with them.
2. **No proof of bit-for-bit historical prediction identity.** Regenerated scores themselves vary in the last bits between runs (§10).
3. **No independent replication** (concept C). Item 26 used the same code, author and an author-controlled environment.
4. **Incomplete historical environment.** Only the scikit-learn version is evidenced (§4).
5. **Unrecovered threshold record.** The original candidate list and validation F1 values were not saved, and the stored threshold was not recomputed by retraining (§7).
6. **Historical chronology unresolved** (§7); the v0.3 test split was reused for many later analyses.
7. **Shared warning episodes** and the pooled-versus-first-event distinction affect how the 4.72 s median and 96.1% recall should be read (§11).
8. **Excluded events.** Ten first crossings were never scored. Four later unsafe runs were outside the evaluated rows in the regenerated data; their counterpart in the original data is inferred, not observed.
9. **Regenerated data are not the original data.** Floating-point values agree to about 1e-12 (metadata); the original data files were not preserved or hashed.
10. **Single seed and one split.** No confidence intervals are reported here. The unmerged `credibility-v1.1` branch contains a bootstrap analysis and a run log in which the frozen metrics were also reproduced; it is by the same author, was not verified by this report, and used `>=`.
11. **Simulation-only scope.** A simplified 2D longitudinal model with plausible, not measured, coefficients. No real flight, wind-tunnel or certification data. Nothing here supports a claim of real-aircraft safety, operational readiness or flightworthiness.
12. **Software tests** support correctness of the code paths covered; they do not validate the science. The original "190/190 tests" figure is a historical claim.
13. **Older documents carry less-qualified numbers** (Appendix B). They were not rewritten.
14. **Scratch tooling is temporary.** No committed script reproduces the Item 26 scoring (§14).

---

## 14. Exact Reproduction Instructions

Commands are given only where they exist in the repository. The Item 26 scratch scripts (Appendix C) were **temporary, are not committed, and may not persist**; none of the commands below refers to them. The scoring procedure in step C is a description, not a committed script.

### A. Saved-artifact checks (no data needed)

```bash
sha256sum -c baselines/v0.3.sha256        # macOS: shasum -a 256 -c baselines/v0.3.sha256

python3 - <<'EOF'
import json, statistics
p = json.load(open("outputs/ml_v03/metrics/primary_model_metrics.json"))
cm = p["test_metrics"]["confusion_matrix"]; tn, fp, fn, tp = (cm[k] for k in ("tn", "fp", "fn", "tp"))
print("rows", tn + fp + fn + tp, "precision", tp / (tp + fp), "recall", tp / (tp + fn), "fpr", fp / (fp + tn))
ev = p["event_level"]; lt = ev["lead_times_s"]
print("events", ev["n_events"], "warned", len(lt), "median", statistics.median(lt), "at cap", sum(1 for x in lt if x == 5.0))
EOF

# audit tests (use the pinned environment; they read the frozen model and tracked metadata only)
python -m pytest tests/test_audit_labels_features_splits.py tests/test_audit_event_metrics.py -q
```

The second command prints `rows 538034 … events 76 warned 73 median 4.72 at cap 29` on the stored artifacts. The test command gave 36 passed when this report was written. The full CI selection is in `.github/workflows/tests.yml` (not yet committed).

### B. Regenerating the dataset and evaluation panels

**Prerequisites.** Python 3.12 with the versions in `requirements-pinned.txt` (`pip install -r requirements-pinned.txt` from your working checkout; the file is not yet committed); about 2.1 GB of disk for the minimal route measured in Item 26 (more with the unchanged script, which also writes the raw parquet, audit report and plots; not measured); about 5.5 GB of RAM at the panel build (measured); about 8 minutes for generation and 1.6 minutes for the panels (measured in Item 26).

**Run in a scratch copy, never in your working checkout.** `scripts/generate_dataset_v3.py` overwrites these 16 tracked files: the three files `trajectory_metadata_v3.csv`, `generation_config_v3.json` and `feature_schema_v3.json` in `data/metadata/`; `data/splits/split_manifest_v3.csv`; `outputs/dataset_audit_v3/audit_report_v3.md` and `outputs/dataset_audit_v3/audit_report_v3.json`; and the ten PNG files in `outputs/dataset_audit_v3/plots/`.

```bash
mkdir ../aeroguard-scratch
git archive HEAD | tar -x -C ../aeroguard-scratch     # clean copy of the committed state
cd ../aeroguard-scratch
python scripts/generate_dataset_v3.py                  # ~520 s (RL-001); raw + processed parquet
python -c "from ml.temporal_data_v03 import load_temporal_splits as L; L(force=False, verbose=True)"
```

`git archive HEAD` copies the committed state only; files that exist only in an uncommitted working tree are absent. Check the gates in §5 by hand: 5,340,865 rows and 3,150 trajectories; the regenerated `data/splits/split_manifest_v3.csv` identical to the committed one; panel rows 3,749,572 / 771,995 / 819,298; usable test rows 538,034. The wrapper used in Item 26 skipped the raw parquet, audit and plots; the unchanged script above does not.

### C. Re-scoring the frozen model

Prerequisite: step B in the same scratch copy. [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) (§ "Re-scoring the frozen model on regenerated v0.3 data (level 4)") contains a snippet that scores the test panel and prints PR-AUC, event recall, events, median lead and the row count. It applies strict `>` as of this report (it was corrected from `>=` in Item 25; the 2026-10-12 execution used `>=`, and the corrected line has not itself been executed).

The full Item 26 evaluation additionally (i) took the threshold from `outputs/ml_v03/experiment_config.json`, (ii) called `ml.temporal_experiment.evaluate_on_test` (strict `>`) for the confusion matrix, AUCs, buckets and events, (iii) called `run_false_alarm_analysis` and `run_regime_airspeed_breakdown_v03`, and (iv) scored with `n_jobs=1` and with the saved `n_jobs=-1` several times. No committed script does all of this. [Recommendation] Add a small reviewed scoring script in a later item.

### D. Retraining (not part of Item 26)

`python scripts/run_temporal_experiment_v03.py` retrains and overwrites `outputs/ml_v03/` (about 22 minutes originally). It was **not** run in Item 26 or Item 27 and has not been tested for reproduction. A retrained model is not expected to be byte-identical to the frozen one. Use a scratch copy.

---

## 15. Research Integrity and AI Assistance

- **Authorship.** The research idea is the author's: Bulusu Hanu Sharan is the sole listed author of the [paper](https://doi.org/10.5281/zenodo.22724022) and the repository owner. No institutional affiliation is claimed. `CITATION.cff` currently encodes the name as family name "Sharan" and given names "Bulusu Hanu"; whether that structured split is right is an open author decision, and this report uses the exact publication name Bulusu Hanu Sharan.
- **AI assistance.** Claude Code, an AI coding assistant from Anthropic, assisted with building and implementing the project. It did not originate the research question, and its use is not independent verification of any result. The repository documents that the v0.3 control-profile calibration was investigated by two concurrent Claude Code sessions whose conflicting verdicts were reconciled (final report §11, §13, §21; `PROVENANCE.md` §3), and that Claude Code assisted with repository engineering and documentation (licence, citation, CI, dependency pinning, dashboard attribution, the audits and reproduction check recorded in RL-001 to RL-006, and this report).
- **What the record does not show.** The repository does not record, task by task, which experimental design choices, analyses, model-selection decisions or manuscript passages were made with Claude Code's assistance, so this report does not claim that any of them were made without it.
- **Consequence for the evidence.** The audit, reproduction and documentation items (including Items 25–27) were carried out by the same AI assistant under the author's direction. They are checks by the original experimenter's own toolchain, not independent verification. The text of the README, `RESEARCH_LOG.md` and this report keeps hypotheses, interpretations and recommendations separate from observations.

---

## 16. Final Reproducibility Verdict

> The v0.3 frozen-model evaluation was reproduced on regenerated data. The preregistered dataset, panel, and metric gates passed. The saved confusion matrix and ROC-AUC matched exactly, and PR-AUC matched within the preregistered tolerance. This check does not establish bit-for-bit identity with the original predictions or constitute independent replication.

Scope in one line: **concept B passed; concept A is internally consistent and its population is reconstructable from tracked metadata; concept C has not been attempted.**

Open items that this verdict does not close: the unsaved original score arrays and threshold record; the historical chronology; independent replication; and the less-qualified older documents listed in Appendix B.

---

## Appendix A. Claim-to-Evidence Summary

| Claim | Evidence source | Verification method | Result | Limitation |
|---|---|---|---|---|
| Model SHA-256 is `707d4c61…c603f3` | `outputs/ml_v03/models/primary_model_D_1s.joblib`; `baselines/v0.3.sha256`; RL-006 | `sha256sum` of the file; manifest check; text match in RL-006 | match | Hash of the file, not of the original training run |
| Threshold 0.8585534589255494 | `outputs/ml_v03/experiment_config.json`; `outputs/ml_v03/metrics/primary_model_metrics.json` | compared the two JSON values; RL-006 text | identical | Recomputation by retraining not done |
| Strict `>` is the primary operator | `ml/temporal_experiment.py:109` | read the code; RL-004 inventory | confirmed | Other `>=` sites exist outside the headline path |
| Confusion 489,495 / 2,370 / 12,184 / 33,985 | `outputs/ml_v03/metrics/primary_model_metrics.json`; RL-006 | read; arithmetic totals 538,034; Item 26 recomputation | match | Original arrays not saved |
| PR-AUC 0.8902774777010881; ROC-AUC 0.9775387048062552 | same; RL-006 | read; Item 26 scoring | exact, except PR-AUC 8.39e-11 in one run | Scoring not bit-deterministic |
| Precision 0.9348…, recall 0.7361…, F1 0.8236…, accuracy 0.9729…, FPR 0.004818… | `outputs/ml_v03/metrics/primary_model_metrics.json`; `outputs/ml_v03/metrics/false_alarm_analysis.json` | read; recomputed from counts | match | Derived from the same counts |
| 5,340,865 rows; 3,150 trajectories; seed 20260823 | `data/metadata/trajectory_metadata_v3.csv` (sum of `n_steps`, row count, `random_seed`) | recomputed | match | Original data files not preserved |
| Splits 2,205 / 472 / 473 trajectories | `data/splits/split_manifest_v3.csv`; `tests/test_audit_labels_features_splits.py` | counted; regeneration test | match | |
| Panels 3,749,572 / 771,995 / 819,298; usable 538,034 (46,169 / 491,865); 456 of 473 | RL-006 (Gate B); `outputs/ml_v03/metrics/primary_model_metrics.json` | Item 26 Gate B; metadata reconstruction (RL-005) | match | Panels were regenerated |
| Evaluated rows = `max(0, n_steps − 600)` per trajectory | `ml/temporal_features.py:187`; `aeroguard_dataset/labeling.py:26-55` | summed over metadata | exact for all three splits | Assumes the 1.0 s window |
| Events 76 / 73 / 3; median 4.72 s; 29 at cap; coverage counts | `outputs/ml_v03/metrics/primary_model_metrics.json`; `outputs/ml_v03/metrics/primary_model_warning_coverage.json` | recomputed from the 73 stored leads; Item 26 | match | Event list itself not stored |
| 57 first (54 warned) and 19 later (19 warned); medians 3.15 and 5.00 s | RL-005; RL-006 | per-crossing records; regenerated event list | match | Regenerated data |
| 16 of 19 later events share the first event's warning episode | RL-006; scratch event tables | Item 26 analysis | observed | Why later leads are long is not shown |
| 10 excluded first crossings; none has a further run; 4 later runs elsewhere | RL-003; RL-006 | metadata; regenerated unsafe runs | match | Regenerated data only |
| Five rows at `time_to_stall = 5.000000000000001`; 3 warned, 2 missed | RL-006; `scripts/prepare_ml_dataset.py:118-139` | regenerated rows listed | supported | Not proven on original arrays |
| Environment versions | RL-006; `requirements-pinned.txt` | compared | match for 7 packages | Original environment unknown |
| Zero score ties; `>` = `>=` on regenerated scores | RL-006 | counted in four variants | confirmed | Regenerated scores only |
| 79 of 79 baseline hashes | `baselines/v0.3.sha256` | `sha256sum -c` | pass | Data not covered |
| Threshold candidate list not saved | `ml/temporal_experiment_v03.py:60,109,122,158,219` | read the code; search of artifacts | confirmed | Cannot be recovered without a retrain |

## Appendix B. Older Documents That Carry Less-Qualified Statements

Not modified by Item 27; listed for a future controlled update.

| Document | Statement | Note |
|---|---|---|
| `paper/AeroGuard_Research_Paper.md`, `.html`, `.pdf`; dashboard copy; Zenodo record | Report 96.1% recall and 4.72 s without the evaluated-population and warned-only qualifiers | Draft wording in `paper/PROPOSED_AMENDMENT_event_metrics_scope.md` (proposal only). The PDF and Zenodo record also show the old repository URL. |
| `outputs/final/AEROGUARD_FINAL_RESEARCH_REPORT.md`, `outputs/final/FINAL_STATUS.md`, `outputs/ml_v03/v03_temporal_ml_report.md` | Frozen reports; unqualified headline figures (the v0.3 report shows the exclusion in a table) | Frozen; do not edit |
| `README.md`, `dashboard/public/docs/AEROGUARD_README.md`, `dashboard/src/components/sections/KeyResults.tsx` | State that the metadata does not establish how many later episodes fall outside the evaluated rows | Regenerated data now give a count (RL-006); update after review |
| `dashboard/src/data/metrics.json` | Contains `tests: 190/190` | Historical claim; not recomputed |
| `dashboard/dist/` | Build output with older copies of the documents | Gitignored build output |
| `REPRODUCIBILITY.md` (Level 4 evidence) | The 2026-10-12 run used `>=`; a note says so | Add the Item 26 strict-`>` result in a later update |

## Appendix C. Item 26 Scratch Tooling (Not in the Repository)

Names and hashes are recorded in RL-006 so that a reader can recognise them if they are ever recovered: `gen_v3_min.py` (`0e0c8303…`), `gate_B.py` (`98fec555…`), `score_v03.py` (`6a0b4113…`), `compare_v03.py` (`164d3bb0…`), `extra_checks.py` (`fd8258de…`). The full source was reproduced in the Item 26 final report and is not duplicated here.
