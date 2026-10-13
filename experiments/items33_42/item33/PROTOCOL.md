# AeroGuard Item 33 — Control-Input Ablation Protocol

| | |
|---|---|
| **Status** | **DRAFT v0.3 — proposed for approval. NOT approved, NOT locked. No Item 33 experiment, research-panel read, model load, training, scoring or bootstrap has been performed.** (Only tracked JSON/CSV records were read and tracked files hashed during preparation.) |
| **Prepared** | 2026-10-13 (UTC), branch `claude/loving-fermi-ql3cyo`, HEAD `4320b3904f92b78cfcd9d5c8739fda6ec287bd9b`, working tree clean before this file was added |
| **Scope** | Item 33 only (control-input ablation) |
| **Out of scope** | Items 34–42; the Phase 3 protocol, code and results (unchanged); the frozen model; the paper; Zenodo records; `main` and `credibility-v1.1` |
| **Simulation only** | Every statement concerns a simulated aircraft. Nothing here can establish performance, safety or suitability for any real aircraft. |

### Revision history

- **v0.1, v0.2:** discussed in the working session only (not committed). v0.2 incorporated the researcher's provisional decisions D1–D4 (five-seed panel, inference-time masking, C3 exploratory, X1 added).
- **v0.3 (this file):** adopts the completion directive's primary-contrast definition (Δ1 = C0 − C1, Δ2 = C0 − C2; C1 − C2 secondary), which supersedes v0.2's choice of C1 − C2 as the second primary contrast (recorded as ISSUES I-01); re-verifies the feature schema and condition arithmetic against source and the stored model record; reconciles the historical figures against tracked artifacts (§2.2); adds median across seeds to the seed reporting; narrows the design (per-regime estimates deferred, §9.3); adds the computation estimate, provenance identifiers, gates and an acceptance mapping. A final pre-lock review then corrected: separation and interpretation of seed variability versus bootstrap uncertainty (§9.2); the shared-regime limitation (§9.3); regenerated-dataset provenance wording (§7, R1, R2); renamed register identifiers (SEC-1 to SEC-3) and masking substitutions (MS1 to MS3) to remove an identifier clash; a precise masking specification and analysis-family separation (§10); test-isolation guarantees and a gated `synthetic_fit` group (§14); an explicit stop after the first fit (§15); and per-gate authorizations with an explicit bootstrap gate (§17).

## 0. Reading conventions

- **[SPECIFIED]** — fixed by this protocol.
- **[ASSUMPTION]** — not yet verified; the protocol states how it will be checked and what happens if it fails.
- **[UNRESOLVED]** — needs a decision or later verification before the dependent step may run.
- **(verified: source)** — read in repository code during preparation. **(verified: executed)** — confirmed by running non-data code (config import, `sha256sum`, `git`). **(verified: artifact)** — read from a tracked file. **(historical)** — taken from an earlier record and not re-derived here. **(UNVERIFIED)** — not checked.
- This document is a plan. It contains no Item 33 result.

## 1. Scientific question, hypotheses and estimands

**Primary question.** How much predictive performance (PR-AUC) is lost when current control inputs, and then explicit recent control history, are removed from the temporal feature set, under the same predefined trajectory-level data split?

This is a **predictive-information** question. It is not a causal question, and it does not show that the model "uses" controls in any causal sense or how a pilot-in-the-loop system would behave.

**Hypotheses.** The study is estimation-oriented. There is **no directional hypothesis**: removal may lower, leave unchanged or raise PR-AUC, and all three are valid, reportable results. For each contrast the null reference is "no difference" (Δ = 0), assessed through an interval, not through a p-value.

| Id | Question | Contrast | Status |
|---|---|---|---|
| Q1 | Loss when both raw controls are absent | **Δ1 = PR-AUC(C0) − PR-AUC(C1)** | **Primary** |
| Q2 | Loss when raw controls and explicit 1 s elevator-change history are absent | **Δ2 = PR-AUC(C0) − PR-AUC(C2)** | **Primary** |
| Q2a | Contribution of `elevator_change_1s` when raw controls are already absent | C1 − C2 (= Δ2 − Δ1, algebraically) | Secondary |
| Q3 | Control-related information retained in state derivatives | C0 − C3 | Exploratory |
| Q2b | Contribution of `elevator_change_1s` beyond everything else | C0 − X1 | Exploratory |
| Q4 | Sensitivity of the fixed frozen model to altered inputs | Inference-time masking (§10) | Secondary, descriptive, separate family |

**Estimands across seeds (§9.2).** For condition c and training seed s let A_c(s) be the test PR-AUC. For a contrast between reference r and comparison k:

- **Primary estimand:** Δ̄ = mean over the five pre-specified seeds of [A_r(s) − A_k(s)].
- **Secondary estimand:** Δ(s₀) at the frozen model's seed 20260817.

## 2. Evidence categories, historical figures and test-exposure disclosure

### 2.1 Categories

- **E0** — stored original results (`outputs/ml_v03/**`). Context only; never edited.
- **E1** — Phase 3 results on the regenerated copy (`outputs/phase3/run_20261013T140820817642Z/`). Used only for the frozen-model anchor and for reconciliation.
- **E2** — new Item 33 results.

### 2.2 Reconciliation of historical figures with tracked artifacts (verified: artifact)

The figures in the task description are treated as historical claims. They agree with the tracked records as follows. The counts are those recorded by Phase 3 gate G5 on the regenerated copy; **this protocol has not re-derived them from the data** (that is G33-1).

| Figure | Task description | Tracked record | Recorded value | Status |
|---|---|---|---|---|
| Frozen model PR-AUC | 0.8903 | `outputs/ml_v03/metrics/primary_model_metrics.json` (E0) | 0.8902774777010881 | consistent |
| Frozen model PR-AUC, re-scored | 0.8903 | Phase 3 `bootstrap.json` (E1) | 0.8902774777010881 | identical to the printed digits |
| Instantaneous Model A PR-AUC | 0.8754 | Phase 3 `bootstrap.json` (E1) | 0.8754338390816084 | consistent |
| Difference | +0.0148 | Phase 3 `bootstrap.json` | 0.014843638619479682 | consistent |
| Paired 95% CI | [0.0079, 0.0230] | Phase 3 `bootstrap.json` | [0.007926567722612726, 0.023023972498221884] | consistent |
| Test rows | 538,034 | `primary_model_metrics.json` population; Phase 3 `population.json` | 538,034 | consistent |
| Test trajectories with usable rows | 456 | same | 456 (of 473) | consistent |
| Positive / negative rows | 46,169 / 491,865 | same | 46,169 / 491,865 | consistent |
| Events | 76 in 57 trajectories | Phase 3 `population.json` | 76; 57 | consistent |
| Eligible test time | 5,375.78 s | Phase 3 `population.json` | 5,375.78 s (span-based; rows × dt = 5,380.34 s) | consistent |

**Conflation hazard.** The older v0.3 ablation reports a different "Model A" (PR-AUC 0.9027 on a 2 s common subset of 492,618 rows, 452 trajectories). It is a different model and population. It is not the Phase 3 Model A and is never mixed with Phase 3 figures (ISSUES I-14).

### 2.3 Test-exposure disclosure [SPECIFIED]

The test trajectories and labels have been used, and test results examined, in: the original v0.3 frozen-model evaluation (E0); the v0.3 ablation (E0/E1); the `credibility-v1.1` run (E1); Item 26 (E1); and Phase 3 (E1). The protocol author has also read the stored feature-importance ranking (`elevator` 0.088 among the top five, `outputs/ml_v03/v03_temporal_ml_report.md`) and the Phase 3 results.

Consequently every Item 33 result is a **controlled re-evaluation of previously exposed data on a regenerated copy**. It is:

- **not** blind, **not** independent replication, **not** untouched-data evidence;
- **not** evidence of generalisation to real aircraft or to other simulation designs.

Primary contrasts are described as "pre-specified", never "confirmatory". Safeguards that remain valid: models and thresholds are fixed from train and validation before test scoring; each fitted model is scored on test once; the contrasts, metrics, population, seeds and bootstrap configuration are written here before any scoring.

## 3. Feature inventory and verified schema

**Verification performed (verified: executed).** `ml.temporal_config_v03.model_d_features(1.0)` (source) has 23 unique features, equal **and in the same order** to `feature_columns` in `outputs/ml_v03/metrics/primary_model_metrics.json` (the frozen model's stored record). All seven names removed by the conditions exist in that list. `thrust`, `theta` and `vertical_speed` are not in it. The frozen estimator itself was **not** loaded, so its internal `feature_names_in_` is UNVERIFIED (ISSUES I-10).

Frozen 23-feature order (C0): `V, alpha, gamma, pitch_rate, altitude, elevator, throttle, stall_margin, dV_dt, dalpha_dt, dgamma_dt, dq_dt, d2alpha_dt2, alpha_mean_1s, alpha_min_1s, alpha_max_1s, alpha_range_1s, alpha_slope_1s, alpha_trend_1s, V_slope_1s, gamma_slope_1s, pitch_rate_slope_1s, elevator_change_1s`.

### 3.1 Control inputs and control history

| Feature | Definition / unit | Provenance | Role | Open question |
|---|---|---|---|---|
| `elevator` | commanded deflection, rad (`data/metadata/feature_schema_v3.json`) | recorded from the control profile at each step, `aeroguard_dataset/trajectory_sim.py:140`; equals per-trajectory trim plus scripted pulses (`control_profiles.py:119-122`) | **Direct control input** | Includes trim, so it may carry initial-condition information [UNRESOLVED, G33-1] |
| `throttle` | commanded throttle, dimensionless, nominally 0–1 | `trajectory_sim.py:141` | **Direct control input** | Inert in `gradual_approach_v3` (`generation_config_v3.json`), so a per-trajectory constant there; possible trajectory fingerprint [UNRESOLVED, G33-1] |
| `elevator_change_1s` | `elevator[t] − elevator[t − 1 s]`, rad; causal endpoint difference grouped by trajectory (`ml/temporal_features.py:123-127`) | derived | **Control history** | none |
| `thrust` | `throttle × thrust_max`, N (`aeroguard/aerodynamics.py:107-113`) | exact linear function of throttle | Exact control function; **not** in the frozen model | Excluded from every manifest and guarded by a test |

### 3.2 Candidate proxies (removed only in C3)

| Feature | Definition | Basis for candidacy | Status |
|---|---|---|---|
| `dq_dt` | backward difference of `pitch_rate`, rad/s² (`ml/temporal_data_v03.py:49`) | `Iyy·dq/dt = E·elevator − D·q − K·alpha` (`aeroguard/dynamics.py:85-90`): given `q` and `alpha`, analytically linked to `elevator` | Link verified in the equation; empirical recoverability from discretised data UNVERIFIED |
| `dV_dt` | backward difference of `V`, m/s² (`aeroguard_dataset/features.py:22-31`) | `m·dV/dt = T·cos(alpha) − D − m·g·sin(gamma)` (`dynamics.py:67`) | Same; throttle is inert in the dominant regime |
| `pitch_rate_slope_1s` | OLS slope of `pitch_rate` over 1 s, rad/s² | windowed analogue of `dq_dt` | Hypothesis only |
| `V_slope_1s` | OLS slope of `V` over 1 s, m/s² | windowed analogue of `dV_dt` | Hypothesis only |

Correlation with a control is never taken as proof of proxy status; C3 tests a stated physical hypothesis.

### 3.3 The 16 features retained in every condition

`V` (m/s), `alpha` (rad), `gamma` (rad), `pitch_rate` (rad/s), `altitude` (m), `stall_margin` (rad; exact function of `alpha`), `dalpha_dt` (rad/s), `dgamma_dt` (rad/s; contains `T·sin(alpha)`, a weak throttle path, not removed), `d2alpha_dt2` (rad/s²), `alpha_mean_1s`, `alpha_min_1s`, `alpha_max_1s`, `alpha_range_1s` (rad), `alpha_slope_1s`, `alpha_trend_1s` (rad/s), `gamma_slope_1s` (rad/s). Units for derived features follow their definitions in source; the schema file states units only for the raw columns and `dV_dt`, `dalpha_dt`, `stall_margin`.

**Count check (verified: executed):** 3 control and history features + 4 candidate proxies + 16 retained = **23**.

### 3.4 Never admitted to any predictor matrix

`theta`, `vertical_speed`, `thrust`, `future_stall_5s`, `future_stall_5s_available`, `is_unsafe`, `time_to_stall`, `trajectory_id`, `time`, `split`. Existing guards (`ml/temporal_experiment.py:63-76`) refuse the label, availability flag, `is_unsafe`, identifiers and `time_to_stall`; the new code adds its own manifest-equality check.

**Residual control information.** After C3, `dalpha_dt`, `d2alpha_dt2`, `dgamma_dt`, `gamma_slope_1s` and the alpha window features still carry consequences of past controls, because state variables integrate past controls. **No condition is "control-free" and no such claim is made.**

## 4. Experimental conditions [SPECIFIED]

| Condition | Removed from C0 | n features (verified: executed) | Status |
|---|---|---|---|
| **C0** | none | 23 | Retrained baseline |
| **C1** | `elevator`, `throttle` | 21 | **Primary** (Δ1) |
| **C2** | C1 plus `elevator_change_1s` | 20 | **Primary** (Δ2; secondary C1 − C2) |
| **C3** | C2 plus `dq_dt`, `dV_dt`, `pitch_rate_slope_1s`, `V_slope_1s` | 16 | **Exploratory** |
| **X1** | `elevator_change_1s` only | 22 | **Exploratory** |

Nesting verified (verified: executed): C3 ⊂ C2 ⊂ C1 ⊂ C0 and C2 ⊂ X1 ⊂ C0. Feature order within each condition is C0's order with the removed names deleted, and is asserted against literal manifests at fit and score time. If any feature is absent, renamed or defined differently, the run stops; no substitute is used.

**Constants across conditions.** Model class, hyperparameters, training/validation/test rows, label, threshold procedure, bootstrap configuration and software environment.

**Feature subsampling (verified: executed arithmetic; scikit-learn 1.9.0 default `max_features="sqrt"`).** The number of features examined per split is `max(1, int(√n))` = 4 for n = 23, 22, 21, 20 and 16. It is constant, but the probability that a given feature is a candidate at a split changes (4/23 versus 4/16). This is a recorded limitation (ISSUES I-11). The implementation asserts the resolved value.

**Assessment of the nested design.** It answers Q1 and Q2 as stated; increments are order-dependent; Δ1 cannot separate the elevator channel from the throttle channel; Δ2 does not separate raw controls from explicit history, which is why C1 − C2 is reported as a secondary contrast. X1 answers "history beyond everything else". Single-channel conditions (throttle only, elevator only) are **not** adopted, to limit multiplicity.

### What X1 can and cannot establish

- **Can:** the conditional marginal contribution of `elevator_change_1s` when `elevator`, `throttle`, `dq_dt`, `pitch_rate_slope_1s` and all other features remain.
- **Cannot:** that a near-zero difference means the feature is uninformative (it may be redundant with `elevator`, `dq_dt`, `pitch_rate` or the alpha windows); causal role; general importance of control history.
- **Why exploratory:** added after the Stage 1 audit and after the author had seen the importance ranking and Phase 3 results; one of several possible single-feature removals, so reporting this one is a forking path; the difference may be small relative to seed noise; no multiplicity adjustment.

## 5. Model, preprocessing and missing values [SPECIFIED]

- **Model class:** `RandomForestClassifier` as built by `ml/models.py:build_random_forest` — `n_estimators=200`, `max_depth=12`, `min_samples_leaf=5`, `class_weight="balanced_subsample"`, bootstrap on (scikit-learn default), `n_jobs=-1` (verified: source and executed for the frozen parameter dict, `FROZEN_RF_PARAMS` in `ml/temporal_config_v03.py`). There is no hyperparameter search.
- **Seed override.** The existing builder fixes `random_state=config.ML_SEED = 20260817`. Item 33 needs a different seed per fit, so a **new** builder with an explicit `random_state` is written in the Item 33 package. `ml/models.py` is not modified. The new builder must reproduce the existing parameter set exactly; a test compares them.
- **Preprocessing:** none. The forest takes the raw feature columns; no scaler and no imputer is fitted. The existing `get_xy` refuses NaN in the selected columns.
- **Missing values:** rows are admitted by the usable mask (§7) and therefore have a full 1 s window; no missing value is imputed. A NaN in a selected column after masking is an error that stops the run.
- **Failed fits** are recorded (§11), never silently retried.

## 6. Split, roles, threshold selection and comparison with the frozen model

- **Split [SPECIFIED].** The tracked `data/splits/split_manifest_v3.csv` (SHA-256 `d7d6eb825d10c6acd870e4c418f2a552ec82dc60e5e12e723f12ada11e4202fb`), 70/15/15 by `trajectory_id` (`aeroguard_dataset/splitting.py:20-59`), unchanged. Historical counts: 2,205 / 472 / 473 trajectories (Phase 3 `population.json`). Disjointness is checked at G33-1 and by synthetic tests. No assignment is changed.
- **Roles.** Train fits every model. Validation selects each model's threshold and defines the matched operating point (§9.4); nothing else. Test is used only for final scoring, once per fitted model. No test outcome selects a feature, threshold, seed, hyperparameter, condition or analysis.
- **Threshold procedure [SPECIFIED]** (verified: source, `ml/calibration.py:27-50`): rank candidate thresholds by **training** F1, keep the top 10, then keep the one with the best **validation** F1. Operator is strict `>`. Each (condition, seed) has its own threshold, fixed at fit time, before any test scoring. Random Forest training scores are optimistic, so absolute threshold values are not comparable across conditions.
- **Frozen-model anchor.** The frozen model is scored as saved, never refitted. Its Phase 3 scores (E1; SHA-256 `37801481115a4632590df95d1f5f88ac487c28e8c452d5a6540431920d61f6e9`, recorded in Phase 3 `audit.json`) are reused if the scratch copy survives and its hash matches; otherwise one re-score needs separate authorization.
- **Reproduction diagnostic (technical check, not a hypothesis).** C0 at seed 20260817 is compared with the frozen model. C0 is not required to reproduce it exactly (it is fitted in the Phase 3 environment, scikit-learn 1.9.0; the frozen model's fitting environment is unrecorded, UNVERIFIED). Reported, with no invented tolerance:
  - **R0** — all 538,034 scores bit-identical;
  - **R1** — scores differ, but the paired trajectory-bootstrap interval for PR-AUC(C0) − PR-AUC(frozen) includes 0;
  - **R2** — that interval excludes 0.
  - Also reported: maximum absolute score difference and the threshold difference (frozen: 0.8585534589255494).
  - R1 and R2 are discrepancies. They are investigated where cheap (software version, row order) and documented, never hidden. They do **not** invalidate Δ1 and Δ2, which compare retrained models with each other. Claims about the frozen model remain claims about the frozen model.

## 7. Evaluation population [SPECIFIED]

- **Rule.** The frozen model's 1 s usable rows (`phase3/population.py:315-317`, reusing `ml.temporal_features.usable_mask_for_window`): target available and a full 1.0 s window. The rule does **not** depend on a condition's features: dropping `elevator_change_1s` does not re-admit warm-up rows.
- **Expected counts (historical, Phase 3 G5, regenerated copy):**

| Split | Usable rows | Trajectories |
|---|---|---|
| Train | 2,443,881 | 2,205 total |
| Validation | 491,322 | 472 total |
| Test | 538,034 (46,169 positive; 491,865 negative) | 456 with usable rows, of 473 |

  Test events: 76 in 57 trajectories (57 first events, 19 later). Eligible test time: 5,375.78 s (span-based).
- **Identity check.** Each condition's test key set (trajectory, step) must equal the recorded Phase 3 key set (`row_keys.npz`, SHA-256 `893c7d30d5b0c1a4f268242a4b6c74bded00071a06476c9ef6ead22bc0420f62`, scratch). Any count, key or hash mismatch **stops the run**; the population is never silently widened or narrowed.
- **Data source.** The regenerated Item 26 copy; the original v0.3 dataset is absent (ISSUES I-02). Recorded identifiers:

| File | SHA-256 | Bytes |
|---|---|---|
| `processed/processed_dataset_v3.parquet` | `a533f9e940c16ab8bfddf3a4ca98d4326a17655247274142d98280ed03b4a38e` | 449,345,877 |
| `ml_temporal_v03/temporal_train.parquet` | `1a39472881280e084f3cab5d94fa4c80382d65a7075df59cd7a45fd4d5af4b43` | 1,188,953,925 |
| `ml_temporal_v03/temporal_val.parquet` | `9416fc8005b206eefbcdbeeb0d043a45036e8b2d6251ae3850b176765565a0e0` | 246,442,707 |
| `ml_temporal_v03/temporal_test.parquet` | `c03634b4cc793c57bbe065e710a4a98bfe2bf69fdf5a55beb56a1c0ba33241b8` | 261,347,990 |

  These four files exist in scratch storage (sizes confirmed by `ls`; contents **not** hashed or read during preparation; the hashes above are those recorded by Phase 3 at its own data gates). They are gitignored and are lost if the container is reclaimed. If any is missing or any hash differs, Item 33 stops.
- **Honest description of the regenerated copy.**
  - It is a regeneration (Item 26), **not the original v0.3 dataset**, which is absent. Item 33 results are therefore results on the regenerated copy and are never presented as results on the original.
  - No hash of the original dataset was found in a narrow search of the tracked records (`REPRODUCIBILITY*.md`, `PROVENANCE.md`, `RESEARCH_LOG.md`, `outputs/dataset_audit_v3`, `outputs/final`). Absence of such a record is not proven, and the regenerated copy has not been shown to be byte-identical to the original.
  - Recorded evidence of numerical closeness (historical, from Phase 3 `data_provenance.json` and `population.json`; not re-run here): all Item 26 gate-A checks passed with a maximum relative metadata difference of 8.93×10⁻¹³; the regenerated test rows, keys and labels equal Item 26's (538,034 rows); the trajectory assignment matches the tracked split manifest; and the frozen model's PR-AUC on the copy equals its stored value to the printed digits. This supports use of the copy. It does not make the evaluation independent, blind or an evaluation of the original data.
  - The train/validation/test assignment is the tracked manifest, unchanged; it is fixed by trajectory identifier and is not re-drawn.
- **Test composition by regime (historical, E0; sums reconcile with the population above):** normal 113,481 rows, **0 positive**; `gradual_approach_v3` 396,207 rows, 30,001 positive; stall 28,346 rows, 16,168 positive. Trajectories per regime are [UNRESOLVED, G33-1].

## 8. Metrics [SPECIFIED]

| Tier | Metric | Kind | Role |
|---|---|---|---|
| **Primary** | PR-AUC (`sklearn.metrics.average_precision_score`, as in `phase3/analysis.py`) | threshold-independent | Δ1, Δ2 |
| Secondary | ROC-AUC | threshold-independent | context |
| Secondary, descriptive | row-level precision, recall, F1 at each model's own threshold | threshold-dependent | §9.4 |
| Secondary, descriptive | event recall and lead time (`ml/events.py`) | threshold-dependent | descriptive only |
| Exploratory | the same row-level and event metrics at the matched operating point | threshold-dependent | §9.4 |
| Descriptive | validation PR-AUC | threshold-independent | sanity check; the threshold was selected on validation, so this is not independent evidence |

PR-AUC depends on prevalence (about 8.6% positive rows) and is not comparable across populations.

**Event metrics (verified: source, `ml/events.py:1-48`).** An event is a maximal run of `is_unsafe`; a warning episode is a maximal run of positive predictions; lead time is capped at the 5 s horizon at 0.01 s resolution. With 76 events in 57 trajectories, intervals are very wide and intervals for proportions near 100% are degenerate. Median lead time is over warned events only, so cross-condition comparison mixes different warned sets. Event metrics are descriptive and carry no test.

**Not reported:** false alarms per simulated hour and lead-time coverage curves (Items 37 and 38). No operational claim and no "acceptable loss" threshold is made or invented. A margin δ may be supplied by the researcher with a rationale before scoring (D5); none exists now.

## 9. Statistical analysis

### 9.1 Primary method: paired trajectory bootstrap [SPECIFIED]

- **Unit:** the trajectory. Resample the 456 eligible test trajectories with replacement, keeping all rows of a drawn trajectory together. Rows are never resampled independently.
- **Pairing:** within one replicate the **same draw is shared by every condition and every seed**; each difference is computed per replicate.
- **Statistic:** pooled-row PR-AUC (and ROC-AUC) per replicate, not an average of per-trajectory values.
- **Configuration:** B = 1000, seed 20261013, percentile interval at the 2.5th and 97.5th percentiles (the Phase 3 configuration, `phase3/__init__.py:51-53`), reused deliberately so draws are identical and comparable across analyses.
- **Undefined replicates:** a replicate with no positive rows has undefined PR-AUC. It is counted and reported, never silently dropped. The probability is at most (1 − 57/456)^456 ≈ 3.6×10⁻²⁷ (arithmetic; it assumes at least 57 positive-bearing trajectories and is an upper bound). Any occurrence is reported.
- **What the interval represents:** test-trajectory sampling uncertainty, conditional on the fitted models, the one train/validation/test split and this generation design. It excludes training-seed variability, train-split variability and uncertainty about the generation design.

### 9.2 Seeds and estimands [SPECIFIED once approved]

- **Seeds (fixed now, before any result):** forest `random_state` ∈ {**20260817, 20261101, 20261102, 20261103, 20261104**}.
  - Appropriateness (verified: executed): five distinct integers in [0, 2³²), valid for scikit-learn. `git grep` finds no use of 20261101–20261104 in any `.py` file. 20260817 is the frozen model's forest seed and the project's `ML_SEED`.
  - 20260818–20260822 were deliberately avoided: they were dataset-calibration seeds (`scripts/calibrate_v03.py:40`).
  - Matched seeds are used across every comparable condition. The panel runs **unconditionally**; no seed or condition is dropped or added after results are seen.
- **Sources of randomness (verified: source, `ml/models.py:34-39`):** per-tree row bootstrap and per-split feature sampling. Threshold selection and data order are deterministic. That `n_jobs=-1` leaves results unchanged under a fixed seed is believed but UNVERIFIED; Phase 3 documented about 1e-9 PR-AUC variation from `n_jobs=-1` (ISSUES I-09).
- **Common random numbers (believed; to be tested on synthetic data).** The per-tree row bootstrap indices should not depend on the features, so conditions at the same seed should see identical row samples. A synthetic test checks `estimators_samples_`.
- **Layers reported separately, never merged:**
  1. **Estimates:** every A_c(s); every per-seed paired delta Δ(s); the **mean and median** of Δ(s) across the five seeds (Δ̄ is the primary estimand).
  2. **Trajectory-bootstrap interval:** for Δ̄, the percentile interval of the replicate-wise mean over seeds of the paired difference (one shared draw). Per-seed intervals come from the same replicates. This is test-sampling uncertainty conditional on these five fitted model sets.
  3. **Seed variability:** min, median, max and SD (n − 1) of Δ(s) and of A_C0(s). Descriptive only. **No interval across seeds is computed**, and no combined seed-plus-trajectory interval is formed (no justified statistical model exists for one).
- **Interpretation of the layers.** The bootstrap interval answers "how much would Δ̄ change if a different sample of test trajectories were drawn, holding these five fitted model sets fixed". The seed range answers "how much does Δ(s) change when only the forest seed changes, holding the data and split fixed". They are different sources of variation. The across-seed SD is **not** a standard error of Δ̄ and is not compared with, added to or subtracted from the bootstrap interval; a wide seed range does not widen the interval, and a narrow interval does not shrink the seed range. If the seed range is large relative to the magnitude of Δ̄, the report says the effect is not separable from training noise at this seed count.
- **Sign consistency:** a flag records whether Δ(s) has the same sign for all five seeds; a zero counts as inconsistent.
- **Limits:** five seeds sample one randomness source (the forest seed) at fixed hyperparameters and one training set. They do not characterise training-data variability, hyperparameter sensitivity or software nondeterminism, and **do not establish generalisation across training randomness**.

### 9.3 Dependence, regime structure and the regime-stratified sensitivity [SPECIFIED]

- **Structure (verified: source).** Regimes are assigned by exact global counts (500 normal, 250 stall, 2,400 `gradual_approach_v3`) and shuffled (`aeroguard_dataset/dataset_builder_v3.py:50-62,153`); each trajectory then draws its own initial conditions and control profile from one master stream; the split is a random permutation of trajectory IDs, **not** stratified by regime. Given its regime, each trajectory is drawn independently in code. No specific mechanism of within-regime dependence was found, but this is not proof of independence: trajectories within a regime share the same control-parameter ranges, aircraft and trim logic, and are produced by one pseudo-random stream.
- **Limitation of the primary bootstrap.** The trajectory bootstrap is the appropriate resampling unit for dependent frames within a trajectory, but it treats the 456 test trajectories as exchangeable draws from one population. Trajectories generated under shared regimes or configurations may be more alike than that model assumes (for example, heterogeneous effects across the three regimes), in which case the interval could **understate** uncertainty. It cannot represent: generalisation to other generation designs or regime definitions; train-split variability (re-splitting would change historical assignments, which is prohibited); training-seed variability. With three regimes, regime-level clustering is not estimable. A narrow interval is therefore **not** evidence of generalisation beyond this sampled simulation population.
- **Pre-specified sensitivity S-R1 (no decision role).**
  - *Resampling unit:* trajectories, resampled with replacement **within each regime stratum**, regime counts fixed at the observed test composition.
  - *Estimand:* Δ̄ for Δ1 and Δ2, conditional on the observed test regime allocation.
  - *Configuration:* the same B, seed, pairing and percentile rule.
  - *Reported:* the interval, its width relative to the primary interval, and whether 0 is included under each method. If the two disagree on zero-inclusion the report states that the conclusion is sensitive to the resampling model; the primary method is **not** replaced.
  - *Feasibility:* needs each test trajectory's regime from tracked `data/metadata/trajectory_metadata_v3.csv` (SHA-256 `924e0df6ccb303a264579c3f9ba6a5c84e69e0d14bbb58feaa6e0b66abdde05d`; contents not read during preparation). The normal stratum has no positive rows (historical), so it changes only the negatives. Stratum sizes are confirmed at G33-1; an empty stratum stops the analysis and is documented.
- **Not adopted:** regime-level cluster bootstrap (three clusters); post-stratified reweighting to the generator mix (different estimand); re-splitting or cross-validation over trajectories (prohibited); larger B (departs from Phase 3). **Per-regime effect estimates are deferred**: they add four exploratory contrasts, are undefined for the normal regime, and can be proposed as a pre-scoring amendment if wanted (ISSUES I-16).
- **Standing statements.** Frames and seeds are never treated as independent trajectories. An interval excluding 0 is statistical evidence under the stated resampling model; it is not a p-value, not proof of a causal effect and not evidence of generalisation beyond this simulator, however narrow.

### 9.4 Threshold-dependent metrics and the matched operating point [SPECIFIED]

- **Directly interpretable across conditions:** PR-AUC and ROC-AUC.
- **Interpretable only as "each model operated as the existing pipeline would":** precision, recall, F1, event recall and lead time at each model's own validation-selected threshold. A difference mixes ranking quality with threshold position, so it **cannot** be read as "removal reduced recall". F1 is the least affected because each threshold maximises validation F1, but validation optimality does not transfer exactly. These metrics have no primary role and no hypothesis test.
- **Matched operating point (M-OP), exploratory, one level.**
  - *Purpose:* PR-AUC averages over all thresholds, including regions the pipeline never uses. M-OP examines the region it does use, separately from threshold position.
  - *Rule (validation only, no test labels):* for each seed, take C0's validation false-positive rate at its own selected threshold. For every other condition choose the smallest threshold among that condition's distinct validation scores such that the validation false-positive rate of `score > t` does not exceed the target. Record the achieved rate. Evaluate on test once.
  - *Reported:* row-level precision, recall, F1, warning-episode count and event recall versus C0, seed by seed with the seed range; event-level bootstrap intervals only at seed 20260817.
  - *Limitation:* a row-level false-positive rate is not an episode-level rate (Item 37).
  - *Multiplicity:* one extra operating point, descriptive, no decision role, no adjustment.

### 9.5 Comparison register, multiplicity and wording [SPECIFIED]

| Id | Comparison | Status | Estimand | Interval | Adjustment |
|---|---|---|---|---|---|
| **Δ1** | C0 − C1 | **Primary** | Δ̄ | percentile, marginal 95% | Bonferroni sensitivity (m = 2) |
| **Δ2** | C0 − C2 | **Primary** | Δ̄ | same | same |
| SEC-1 | Δ1, Δ2 at seed 20260817 | Secondary, pre-specified | Δ(s₀) | same | none |
| SEC-2 | C1 − C2 (= Δ2 − Δ1) | Secondary | Δ̄ | same | none |
| SEC-3 | ROC-AUC analogues of Δ1, Δ2 | Secondary, descriptive | Δ̄ | same | none |
| T1 | C0(s₀) vs frozen model | Technical check | level R0/R1/R2 | same | none |
| SR | S-R1 stratified resampling for Δ1, Δ2 | Sensitivity | Δ̄ | stratified percentile | none |
| X-a | C0 − C3 | **Exploratory** | Δ̄ | same | none |
| X-b | C0 − X1 | **Exploratory** | Δ̄ | same | none |
| X-c | M-OP (§9.4) | **Exploratory** | descriptive differences | seed by seed | none |
| X-d | own-threshold and event metrics | Descriptive | — | — | none |
| M | frozen-model masking (§10) | Secondary, descriptive, **separate family** | — | bootstrap for 9 variants | none |

- **Bonferroni sensitivity (pre-specified).** For Δ1 and Δ2 only, the same replicates give adjusted intervals at the 1.25th and 98.75th percentiles. With B = 1000 each tail holds about 12 replicates, so adjusted limits are noisy; this is stated in the report. A contrast whose marginal interval excludes 0 but whose adjusted interval includes it is described as "marginal-level evidence only". Δ1 and Δ2 are strongly dependent (C2 ⊂ C1), so Bonferroni is conservative.
- **Counts.** 2 primary contrasts and 2 exploratory PR-AUC contrasts with intervals (C0 − C3, C0 − X1). Exploratory intervals are unadjusted, and some will exclude 0 by chance.
- **Permitted wording.**
  - Δ1, Δ2: "a difference was demonstrated under this protocol" only if the marginal interval for Δ̄ excludes 0 **and** all five Δ(s) share its sign. If the interval excludes 0 but a seed differs in sign: "inconsistent across seeds". If the interval includes 0: "no difference was demonstrated" (never "equivalent"). Adjusted-interval status is stated alongside.
  - Exploratory comparisons: "was observed" and "exploratory". Never "demonstrated", "established" or "confirmed".
  - **Banned for every result:** "confirmatory", "confirmed", "validated", "proves", "the model relies on controls" (as a causal statement), "control-free", "independent", "blind".
- **No minimum meaningful loss is defined or invented.** Without a margin, "negligible" and "equivalent" cannot be claimed. If an interval includes 0 the report says no difference was demonstrated.

## 10. Frozen-model inference-time masking (secondary, descriptive) [SPECIFIED once approved]

- **Purpose and scope.** The sensitivity of the **frozen** model, scored as saved and never refitted, to replaced control-column values. It is a perturbation of inputs, not a measure of information content, and it does **not** measure the same estimand as retrained ablation. Results appear in separate tables and figures and are never subtracted from, averaged with or ranked against retrained results. Disagreement with the retrained results is informative, not an error.
- **Schema.** Columns are **replaced, not dropped**; the frozen model's 23-column input schema is preserved. Whether the estimator stores `feature_names_in_` is UNVERIFIED; the implementation checks on load and refuses a mismatch.
- **Masked sets:** M-A = `elevator`, `throttle`; M-B = `elevator_change_1s`; M-C = all three.
- **Substitutions (fixed in advance):**

| Code | Method (exact) | Weakness |
|---|---|---|
| MS1 | **Constant replacement.** Each masked column is replaced by the median of that column over the **training** usable rows (computed once from the train panel at G33-1; no validation or test row is used; the values are recorded before any test scoring). | a point mass absent from training data; strongly off-distribution |
| MS2 | **Global permutation.** One permutation of the 538,034 test rows, drawn as `numpy.random.default_rng(seed).permutation(538034)` and applied identically to every column in the masked set, with rows in the canonical Phase 3 key order. K = 5 draws, seeds 20261201–20261205. | preserves marginals but breaks joints with `dq_dt`, `pitch_rate`, `alpha`; creates physically inconsistent combinations |
| MS3 | **Within-trajectory permutation.** For each trajectory in canonical order, one permutation of its own usable rows is drawn from a single `numpy.random.default_rng(seed)` stream and applied identically to every column in the masked set. K = 5 draws, same seeds. | keeps trajectory-level offsets such as trim; breaks time alignment |

  - Derived columns are **not recomputed** after replacement: masking `elevator` and `throttle` (M-A) leaves `elevator_change_1s`, `dq_dt` and every other column unchanged, and masking `elevator_change_1s` (M-B) leaves `elevator` unchanged. The resulting internal inconsistency is part of what the analysis measures and is stated in the report.
  - The permutation seeds 20261201–20261205 are fixed now. `git grep` finds no use of them in any `.py` file (verified: executed during preparation; to be re-checked at G33-3).
- **Scoring passes:** 3 sets × (1 + 5 + 5) = 33 passes of the frozen model on 538,034 rows.
- **Separation from retrained ablation.** Every masking output row carries `analysis_family = "frozen_model_masking"`, in files named `masking_*`; retrained rows carry `analysis_family = "retrained_ablation"`. The two families never share a table, a figure or a ranking, and no masking result is subtracted from or averaged with a retrained result. Masked sets are named M-A/M-B/M-C and never use the condition labels C0–C3 or X1.
- **Metrics:** PR-AUC, plus row-level precision and recall at the frozen saved threshold 0.8585534589255494 (strict `>`), descriptive.
- **Bootstrap:** paired trajectory-bootstrap interval for the PR-AUC difference versus the unmasked frozen scores, for 9 variants: MS1 and the first draw (seed 20261201) of MS2 and MS3, for each set. The other four draws give point estimates only, to show permutation variability.
- **Out-of-distribution distortion.** Trees split on axis-aligned thresholds, so substituted values can route rows into branches rarely or never visited in training, and substituted controls contradict the equations of motion (a control value inconsistent with `dV_dt`, `dq_dt`, `pitch_rate`). Apparent reliance may be inflated or deflated relative to information content.
- It requires the separate test-scoring authorization G33-5b and may be declined without affecting any other analysis.

## 11. Failure and undefined-metric handling [SPECIFIED]

- A hash, count, key or schema mismatch **stops** the run and is recorded.
- A failed fit is recorded as `FAILED` with its exception text and is never silently rerun. No condition or seed is dropped. A rerun after a bug is a dated, recorded deviation; **both** the original and corrected outputs are retained and reported.
- Undefined metrics (e.g. a replicate without positives) are recorded as undefined with counts, not coerced to zero or dropped.
- A missing artifact (never produced) is recorded as distinct from a failed experiment.
- `failures.json` is always written (an empty list if none).
- Single-shot rule: after thresholds are frozen, each fitted model's test scores are computed once.

## 12. Provenance and environment [SPECIFIED]

Each run records: git commit and branch; UTC timestamp; condition, feature list, seed and model parameters; the data identifiers of §7 and the split and metadata hashes; the protocol SHA-256; source-file hashes; Python and package versions with `pip freeze`; CPU, memory and runtime where practical; failed fits; and any deviation. Unavailable items are marked unavailable, never invented. In particular no per-trajectory seeds were found in the metadata beyond the dataset seed, and no hash of the original dataset was found (§7).

**Reused code at HEAD `4320b39` (SHA-256 of file bytes; reused, not modified):**

| File | SHA-256 |
|---|---|
| `ml/models.py` | `41339d23007e307286a29e0231d4f6cc771d0e4eae601a6c07e27f0f870adced` |
| `ml/calibration.py` | `cf2156fddd27a29c1e380326e1f33e224b0d240d7d117545caaf0b2be71e8b19` |
| `ml/temporal_experiment.py` | `6280eabd9e1a2251c15e42dc8db3ee53c050ee77222c230d180ee0b8668ba026` |
| `ml/temporal_features.py` | `9b4f51e8fcf49042f032c37a3fee84a0ceb3d1876eba9dec0030e7cd7f699590` |
| `ml/temporal_config.py` | `9e33a5a5bdf728d7fde8a08cefecbf9bb3ae0e828924f36bf9791d4df0c769cc` |
| `ml/temporal_config_v03.py` | `a43bf7692debb550215fd954a01f139815ef6fef75458d67e29e15ea09b20ae6` |
| `ml/events.py` | `a3eb28a0e9d5bbd5ab49f69ce1988ff2fbe6fb3dcf403ce704e370ff4b8d5302` |
| `phase3/__init__.py` | `bb66c06c58e66d779ffaa8bb22fcbec42b16bfc6a0170d21047ba207af035b5b` |
| `phase3/analysis.py` | `3715363b6596c3047053e20ecf1f6ba3c835ecf3dd3277d9787f8ac12f495c65` |
| `phase3/population.py` | `37840c5addfc89711083ef3a4a460f87be4d4b4d69c3250ce42faf724f98a721` |
| `phase3/instantaneous.py` | `328bb8ddd2cbe4fe9902ea9da34b67681627ae67b0be49708d7610551a20b45f` |

**Protected references (verified: executed):** frozen model `outputs/ml_v03/models/primary_model_D_1s.joblib` SHA-256 `707d4c61a791af940549f81520a0c8429edaa8ef8d67eb0f02c3174c5fe603f3`; Phase 3 protocol SHA-256 `da9c62fa1d41beef6ae53aabaedda0eecb623fa5ee06c237c21191011d2a97f2`; `baselines/v0.3.sha256` passes 79 of 79; tracked identifiers `data/metadata/generation_config_v3.json` `752acb2c…aa02`, `data/metadata/feature_schema_v3.json` `54e435c8…9da1`, `outputs/ml_v03/metrics/primary_model_metrics.json` `8bb4b8e4…ccf`, `outputs/ml_v03/metrics/regime_breakdown.csv` `14d89e53…e6`.

**Environment.** The Phase 3 virtual environment (scratch; Python 3.12.3, scikit-learn 1.9.0, numpy 2.5.4, pandas 3.0.6, pyarrow 26.0.0, scipy 1.18.1, joblib 1.6.0; full `pip freeze` in the committed Phase 3 `protocol_lock.json`) is reused. It lives outside Git and can be rebuilt from that freeze. Hardware observed in preparation: 4 CPUs, about 16 GB RAM.

## 13. Layout and artifacts [SPECIFIED]

- **Protocol and code:** `experiments/items33_42/item33/` — `PROTOCOL.md`, `README.md`, `ISSUES.md`, and (Stage D, after approval) `src/` and `tests/`.
- **Run outputs:** `outputs/items33_42/item33/run_<UTC>/`, a new directory per run; every file is created exclusively (an existing path is an error); writes outside it, or into `outputs/ml_v03/`, `outputs/phase3/` or the frozen-model path, are refused by a guard that is tested.
- **Small records** (committable only with separate authorization): `protocol_lock.json`, `conditions_manifest.json`, `seeds.json`, `population.json`, `fit_record_<cond>_<seed>.json`, `threshold_<cond>_<seed>.json`, `metrics_primary.json` and `.csv` (long format; every row carries analysis family, condition, seed, metric, value, population id, evidence category, comparison-register status and exposure label), `bootstrap.json`, `paired_contrasts.json`, `seed_panel.json`, `regime_sensitivity.json`, `matched_operating_point.json`, `reproduction_check.json`, `event_level_<cond>_<seed>.json`, `masking_*.json`, `failures.json`, `audit.json`, `environment.json`, `REPORT.md` (generated only from the JSON), `REPRODUCIBILITY.md`, `ACCEPTANCE_CHECKLIST.md`.
- **Scratch only unless authorized:** fitted models, row-level scores, validation scores, replicate arrays. Their hashes are recorded in `audit.json`.
- **Not-Git-reproducible inputs:** the four panels, models and scores live in scratch. The report states that Git alone cannot reproduce the run.

## 14. Implementation plan and required tests (Stage D, after approval)

New code only; `ml/`, `phase3/`, `aeroguard*/` are imported but not modified.

**Modules:** declarative condition manifests with fail-closed validation; seed-parameterised forest builder; fit driver with gates (run from a tree without `.git`, with a confirmation flag per gate, exclusive writes, as in Phase 3); per-(condition, seed) score and threshold storage; seed-averaged paired bootstrap; stratified bootstrap; matched-operating-point routine; masking runner; contrasts-register writer; report generator.

**Synthetic-fixture tests (no research data, no model load, no research training).** Synthetic fixtures are never presented as results.

**Isolation guarantees (each enforced and tested):**
- All fixtures are generated in memory with fixed seeds. No test reads `data/processed/`, `data/ml_temporal_v03/`, any scratch panel, any `.parquet` file, `outputs/ml_v03/`, `outputs/phase3/` or the frozen-model path.
- An autouse fixture makes `pandas.read_parquet`, `joblib.load`, `pickle.load` and `open` raise if called with any such path, and a dedicated test confirms that attempting to open the frozen-model path raises.
- Fixture "test" tables carry synthetic labels that are explicitly marked; spies assert that the fit and threshold-selection code never touches them (the selector's signature has no test argument, and the fit function rejects a table whose split is not train or validation).
- The data-loading functions take an explicit path and an allowed-splits whitelist, as `phase3/population.py:load_split` does, and fail before opening a file when the split is not allowed.
- Only the Item 33 test directory is run. The historical test suite is never run. Tests write only to pytest temporary directories and never persist a model.
- **Fit-based tests are a separate marked group** (`synthetic_fit`): the seed-override and common-random-numbers checks must fit tiny forests on a few hundred random rows, which is training on synthetic data. They are **not run unless the researcher approves them at G33-3**; all other tests involve no fitting at all.

- exact feature membership and counts (23, 21, 20, 16, 22); deterministic order; nesting; missing/duplicate/unexpected feature rejection;
- leakage-field exclusion (label, availability flag, `is_unsafe`, `time_to_stall`, identifiers, `split`, `thrust`);
- identical eligible populations and row keys across conditions;
- trajectory isolation across train/validation/test and detection of an overlap;
- the fit function cannot receive a test table; threshold selection never reads test labels (the selector's signature has no test argument);
- known-answer PR-AUC and ROC-AUC values;
- paired-bootstrap behaviour: shared draws, self-pair gives zero, replicate 0 reproduced by hand, seed-averaged replicate mean, deterministic output for a fixed seed;
- stratified-bootstrap stratum counts fixed in every replicate; empty stratum refused;
- undefined-replicate counting; failed-fit recording;
- matched-operating-point fixture with known validation scores (achieved rate ≤ target, strict `>`, ties);
- seed override reaches the forest, the new builder reproduces the existing parameter set, resolved `max_features` is recorded, and the common-random-numbers check using `estimators_samples_` (the `synthetic_fit` group above);
- masking replaces rather than drops columns, refuses a schema mismatch, and permutations reproduce from their seeds;
- deterministic output schemas; exclusive-write and protected-path guards (frozen-model path, `outputs/ml_v03`, `outputs/phase3`).

Tests report their actual scope; passing them shows software correctness, not scientific validity.

## 15. Computation estimate (UNVERIFIED unless marked)

- **Fits:** 5 conditions × 5 seeds = **25 fits**. The Phase 3 8-feature fit took 251 s with peak RSS 2,552 MB on 4 CPUs (verified: artifact, `model_a_fit_record.json`, 2,443,881 training rows). These fits examine 4 features per split against 2, so I estimate 4–10 min each: **about 2–4 h**.
- **Bootstrap:** the Phase 3 outputs for 4 methods (PR-AUC, ROC-AUC and event metrics) were written about 16 min after the scores (file timestamps, including report writing). 26 score vectors (25 plus the frozen anchor) for PR-AUC, ROC-AUC and events for the 6 seed-s₀ vectors, and the stratified sensitivity on 15 vectors: **about 1.5–3 h**.
- **Masking:** 33 scoring passes and 9 bootstrapped variants: **about 0.5–1 h**.
- **Total:** about **5–9 h** wall-clock on 4 CPUs; peak memory about 2.5–4 GB; scratch disk about 1 GB (models about 25 MB each — the frozen model is 24,413,241 bytes — plus score arrays).
- **Cost confirmation gate.** Fit order is fixed in advance (seed-major, condition order C0, C1, C2, C3, X1). Authorization G33-4a covers **only** the first fit (C0, seed 20260817): it records runtime and memory and then the run **stops**. The researcher reconfirms the cost. **The remaining 24 fits start only after the separate authorization G33-4b**; once G33-4b is given they run unconditionally, with no seed or condition dropped. No test scoring occurs until all 25 fits and thresholds are frozen, and none occurs without G33-5a.

## 16. Limitations register [SPECIFIED]

| Id | Limitation |
|---|---|
| R1 | The **original v0.3 dataset is absent**. All Item 33 data are the Item 26 **regenerated copy** with four recorded hashes; no hash of the original was found, so byte identity with the original is not established (§7). |
| R2 | The frozen model was not trained on this copy; Phase 3 re-scored it on this copy and obtained a PR-AUC identical to its stored value to the printed digits (a metric-level match; stored row-level scores were not compared). |
| R3 | **Test data were previously exposed** (§2.3). |
| R4 | Panels, models, scores and the virtual environment live in **temporary scratch storage** and are lost if the container is reclaimed; large binaries are not in Git. |
| R5 | If a panel is missing or any hash differs, Item 33 **stops**. Whether a regeneration reproduces the same hashes is UNVERIFIED. |
| R6 | The frozen model's fitting environment is unrecorded (UNVERIFIED); retrained C0 may differ for that reason. |
| R7 | Thread-level nondeterminism is not excluded (UNVERIFIED). |
| R8 | Hyperparameters were tuned for the full feature set and are not retuned per condition. |
| R9 | One train/validation/test split and one generation design. |
| R10 | A single simulator with scripted open-loop controls; the stall in the dominant regime is produced by the scripted elevator pulse. Nothing generalises to real aircraft. |
| R11 | Ablation shows predictive-information dependence, not causal effects or causal independence. State-derived features may proxy for controls. |
| R12 | Trajectories may share generator and regime dependencies not captured by the trajectory bootstrap. |

## 17. Gates and required authorizations

Nothing in this document passes a gate. **Each gate needs its own explicit authorization.** Approval of one gate never implies the next; the researcher may grant several in one message only by naming them. Gates are listed in execution order.

| Order | Gate | Stage | Step | Needs |
|---|---|---|---|---|
| 1 | G33-0 | B/C | Approve and lock this protocol (record its SHA-256) | **Researcher approval.** Does not by itself authorize any later gate. |
| 2 | G33-3 | D | Implement `src/` and `tests/`; run the synthetic tests (the `synthetic_fit` group only if approved here) | **Separate authorization** |
| 3 | G33-1 | E | Data-dependent checks: hash the four panels; read schemas; reconcile population and counts; trajectory-disjoint splits; regime strata sizes; throttle and trim structure; compute the MS1 training medians; confirm the frozen model's `feature_names_in_` (loads the frozen model). No training, no scoring. | **Separate authorization** (reads panels, loads the frozen model) |
| 4 | G33-2 | E | Freeze conditions, seeds, masking spec, register, output schema and any δ; record the combined hash | Approval, **before any scoring** |
| 5 | G33-4a | F | Fit **only** C0 at seed 20260817; record cost; **stop** | **Separate approval to train** |
| 6 | G33-4b | F | Fit the remaining 24 models; freeze thresholds | **Separate approval after cost reconfirmation** |
| 7 | G33-5a | F | Score the retrained models on test, once each | **Separate approval of the final evaluation** |
| 8 | G33-5b | F | Score the frozen model under masking | **Separate approval** (may be declined without affecting any other analysis) |
| 9 | G33-6 | G/H | Bootstrap on test scores, matched operating point, stratified sensitivity, reproduction diagnostic, report | **Separate authorization** (it analyses test outcomes) |
| 10 | G33-7 | I | Independent consistency and acceptance audit | follows G33-6 |
| 11 | G33-8 | J | Preserve and commit small records | **Separate authorization** |

Stop conditions at any gate: a protected-artifact mismatch, a count or hash that does not reconcile, a missing or changed data file, an unavailable dependency version, an unexplained working-tree change, or an unrecorded deviation.

## 18. Acceptance criteria

**For protocol approval (G33-0), all of:**
1. Feature provenance for the 23 frozen features and the excluded columns is recorded with code references, and open items are marked.
2. C0, C1, C2, C3 and X1 are literal feature lists with counts 23, 21, 20, 16 and 22, verified against source and the stored model record.
3. Population, expected counts, regime composition and key-identity check are specified.
4. The threshold procedure is documented, uses no test data, and is the existing one. The matched operating point uses validation only.
5. Metrics are tiered, threshold-free separated from threshold-dependent, with interpretations stated.
6. Δ1 and Δ2 are the primary contrasts; the register assigns every comparison a status and permitted wording.
7. The bootstrap, stratified sensitivity, seed estimand and three reporting layers are specified.
8. The seed list, cost estimate, fit order and cost-reconfirmation step are specified.
9. The masking specification is complete and kept separate.
10. The output schema, failure rules and gates are specified. Historical artifacts are protected.
11. Limitations R1–R12 are written into the protocol.
12. The regenerated copy is described honestly (§7): provenance, fixed split, available hashes, absence of the original, no independent or blind claim.
13. The seed layers and the bootstrap are defined as separate quantities (§9.2), and the bootstrap's limitation under shared regimes is stated (§9.3).
14. Masking is specified precisely and kept in a separate analysis family (§10).
15. Test isolation guarantees (§14) and per-gate authorizations (§17, including the first-fit cost gate in §15) are specified.
16. Feature counts, seed lists, metrics, output paths, gates and acceptance criteria agree across `PROTOCOL.md`, `README.md` and `ISSUES.md`.

**For Item 33 to be declared COMPLETE (maps to the directive's 15 criteria):**

| # | Criterion | Evidence required |
|---|---|---|
| 1 | Protocol finalized before data-dependent experimentation | protocol hash recorded at G33-0, earlier than any data read |
| 2 | Feature schema and conditions verified | manifest test and G33-1 record |
| 3 | Approved conditions and seeds executed, or inability documented | 25 fit records, or `failures.json` |
| 4 | Same eligible population | identical key hashes across conditions |
| 5 | Trajectory-disjoint splits | G33-1 record and test |
| 6 | Threshold selection uses no test labels | selector signature, test, fit records |
| 7 | Primary contrasts computed correctly | known-answer tests and `paired_contrasts.json` |
| 8 | Uncertainty reported and interpreted correctly | three layers reported separately; wording rules obeyed |
| 9 | Failures and undefined metrics preserved | `failures.json`, undefined-replicate counts |
| 10 | Frozen model and historical results unchanged | hash checks and diff at G33-7 |
| 11 | Tests pass with their actual scope reported | test log |
| 12 | Provenance sufficient | `environment.json`, `audit.json`, protocol lock |
| 13 | Exposure and simulation limitations described | report sections |
| 14 | Independent consistency audit passes | `ACCEPTANCE_CHECKLIST.md` |
| 15 | Final files preserved in the intended location | repository diff, after authorization |

A good PR-AUC, or all scripts running, is not an acceptance criterion. If a gate fails the status is **BLOCKED** or **PARTIALLY COMPLETE**, with the failed criterion and evidence.

## 19. Approval record

*(Blank until the researcher records approval. Provisional decisions recorded in conversation, not yet locked: D1 five-seed panel subject to cost confirmation; D2 masking included as a secondary, descriptive analysis; D3 C3 exploratory; D4 X1 added as exploratory.)*
