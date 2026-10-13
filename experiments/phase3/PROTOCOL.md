# AeroGuard Phase 3 — Experimental Protocol (Items 28–32)

| | |
|---|---|
| **Status** | **DRAFT v0.2 — researcher decisions incorporated; the revised protocol is NOT yet approved. No Phase 3 experiment has been executed.** |
| **Prepared** | 2026-10-13, branch `claude/loving-fermi-ql3cyo`, HEAD `a55f21f785350455886845693ae3c5bb9f4fb027` |
| **Scope** | Item 28 (AoA baseline), Item 29 (fair evaluation of the AoA baseline), Item 30 (stall-margin baseline), Item 31 (instantaneous-state model), Item 32 (temporal vs. instantaneous comparison) |
| **Out of scope** | Item 33 (control-input ablation) and every item after Item 32; the stall-margin *trend* rule; Model B as a rung; the warm-up-row sensitivity analysis (removed by the researcher's decision); any hyperparameter search |
| **Simulation only** | Every statement here concerns a generic simulated aircraft. Nothing in this protocol or its results can establish the safety, certification suitability or performance of any real aircraft. |

This document is a plan. Nothing in it is a result. Where it quotes numbers, they are **stored results from earlier work or counts reported by earlier records**, labelled as such (§2). No number in this document was produced by a Phase 3 run.

### Revision history
- **v0.1 (2026-10-13):** first draft.
- **v0.2 (2026-10-13):** incorporates the researcher's decisions D1, D2, D4, D6, D8, D10, D12, D13, D14, D15, D16 (recorded in §17); removes the larger-population sensitivity analysis (S1) and the hyperparameter check (D13/S4); converts the matched-operating-point analysis (D12) into a dormant template because no operational target exists; adds the source-code recheck (§18); adds the train-only negative-alpha investigation (§5.4); re-verifies the regenerated-data hashes.

## 0. How to read this document

- **[SPECIFIED]** — fixed by this protocol: verified from source (cited) or instructed by the researcher.
- **[ASSUMPTION]** — a working assumption, not yet verified; the protocol states how it will be checked and what happens if it fails.
- **[UNRESOLVED]** — a decision or fact that needs researcher approval or later verification before the dependent step may run (collected in §17 and §19).
- **(verified: source)** — I read it in the repository source during preparation. **(verified: artifact)** — I checked a file or hash. **(historical)** — taken from an earlier record and not re-derived by me. **(proposed)** — a procedure this protocol proposes, not an existing fact.

Counts that need a Python environment to re-derive are **(historical)** until gate G5.

## 1. Scientific question and non-claims

**Question.** Does temporal information (a causal 1.0 s history) give measurable predictive value over (a) a single-feature angle-of-attack rule and (b) a machine-learning model that sees only the current flight state, on the v0.3 simulated flight data?

**A result of "no meaningful difference" is valid and reportable.** The protocol is designed to measure, not to confirm.

**What this study cannot show** (stated in advance):

1. It cannot show that temporal reasoning *caused* any observed difference. The compared models differ in input features, in how they were produced (one frozen and previously tuned, one newly trained) and in other ways (§12).
2. It cannot show real-aircraft stall-warning performance. The data are simulated.
3. It is not a blind test. The test trajectories and labels were used by earlier experiments (§10).
4. It is not independent replication. It runs on regenerated data (§3) and is a controlled re-evaluation.
5. It does not establish a physical stall threshold. Any AoA threshold is a train/validation-selected operating point (§5).

## 2. Evidence categories and historical context

Three categories of evidence exist. They are never merged, and results from different categories are never ranked against each other.

| Tag | Meaning |
|---|---|
| **E0** | Results stored in this repository from the original v0.3 run (the original processed dataset is **not** in the working copy). |
| **E1** | Results stored on other provenance: a dataset regenerated and used by an earlier run (the `credibility-v1.1` run or Item 26), or retrained models in the v0.3 ablation. Provenance is stated per row. |
| **E2** | New results produced by this protocol from the regenerated copy (§3). **None exist yet.** |

### 2.1 Stored results — historical context only

None of these was produced or re-verified in preparing this protocol. They are **not** the comparison this protocol will produce.

| Source | Method | Population | Stored values | Tag |
|---|---|---|---|---|
| `outputs/ml_v03/metrics/primary_model_metrics.json` | Frozen temporal model (`primary_model_D_1s.joblib`, 23 features, threshold 0.8585534589255494) | 538,034 test rows, 456 of 473 test trajectories (1 s usable) | PR-AUC 0.8902774777010881; ROC-AUC 0.9775387048062552; confusion tn/fp/fn/tp 489,495 / 2,370 / 12,184 / 33,985; events 73/76 warned; median lead 4.72 s | E0 |
| `RESEARCH_LOG.md` RL-006 / `REPRODUCIBILITY_REPORT.md` | Same frozen model, re-scored on **regenerated** data | Same 538,034 rows | Confusion matrix and ROC-AUC identical; PR-AUC identical or within 8.39e-11 | E1 (Item 26: a reproduction on regenerated data, not independent replication) |
| `credibility-v1.1:outputs/analysis_v11/baselines_and_ci_summary.csv` (read with `git show`; the branch was not checked out) | AoA threshold rule, fitted threshold 0.21723935451615506 rad (12.4469°) | The same 538,034 rows / 76 events per its run log | PR-AUC 0.709 [0.668, 0.746]; events 76/76; median lead 2.08 s; 23.44 false alarms/h. Margin-trend rule: PR-AUC 0.688. | E1 (the script requires a locally generated dataset; that dataset's provenance and hash are **not recorded** in the files I inspected) |
| `outputs/ml_v03/metrics/common_subset_ablation*.csv` | Model A (8 instantaneous features, **retrained**) | **2 s common subset**: 492,618 test rows, 452 trajectories | PR-AUC 0.9027; ROC-AUC 0.9780; events 74/76; median lead 4.585 s | E0 or E1 — dataset provenance of that run is not separately recorded; models were retrained and not saved |
| same file | Model B (A + 5 derivatives) | 2 s common subset | PR-AUC 0.9189 | as above |
| same file | Model D at 1 s (**retrained**, not the frozen model) | 2 s common subset | PR-AUC 0.9177; events 72/76 | as above |

**Do not compare rows of this table directly.** They differ in population (538,034 vs. 492,618 rows), in whether the temporal model is the frozen artifact or a retrained one, and in data provenance. The frozen model's PR-AUC (0.8903, 538,034 rows) and the retrained 1 s model's (0.9177, 492,618 rows) are not comparable.

## 3. Data source (Decision D1 — APPROVED, read-only, conditional on verification)

**[SPECIFIED] The original processed v0.3 dataset (`data/processed/processed_dataset_v3.parquet`) is absent from the working copy** (gitignored; only `data/metadata/` and `data/splits/` are tracked). It will not be regenerated.

**[SPECIFIED] The only available v0.3 data is a copy regenerated in Item 26** (RL-006), in this session's ephemeral scratch directory:

`/tmp/claude-0/-home-user-AeroGuard/1d37592f-2dfd-5c3e-8f4f-959f6d01ce75/scratchpad/item26x/aeroguard-eval/`

The researcher approved **read-only** use of this copy, **conditional** on verified availability, hashes, manifest and provenance. It is **not** the original dataset. Everything produced from it is labelled **"regenerated data"** and is never described as independent replication.

**Verification performed twice (at v0.1 and again at v0.2 preparation; hashes identical both times) (verified: artifact):**

| File (under the path above) | Size (bytes) | SHA-256 | Last modified (UTC) |
|---|---|---|---|
| `data/processed/processed_dataset_v3.parquet` | 449,345,877 | `a533f9e940c16ab8bfddf3a4ca98d4326a17655247274142d98280ed03b4a38e` | 2026-10-13 06:35:58 |
| `data/ml_temporal_v03/temporal_train.parquet` | 1,188,953,925 | `1a39472881280e084f3cab5d94fa4c80382d65a7075df59cd7a45fd4d5af4b43` | 2026-10-13 06:37:32 |
| `data/ml_temporal_v03/temporal_val.parquet` | 246,442,707 | `9416fc8005b206eefbcdbeeb0d043a45036e8b2d6251ae3850b176765565a0e0` | 2026-10-13 06:37:38 |
| `data/ml_temporal_v03/temporal_test.parquet` | 261,347,990 | `c03634b4cc793c57bbe065e710a4a98bfe2bf69fdf5a55beb56a1c0ba33241b8` | 2026-10-13 06:37:44 |

These hashes were first computed during protocol preparation; **no earlier record of them exists**. They identify the files; they do not show correctness. Correctness evidence comes from the Item 26 gate records in the same scratch tree (read, not re-run):

- `audit_out/gen_diag/gate_A.json`: `all_gate_A_pass = true`; 5,340,865 rows; 3,150 trajectories; split manifest identical to the tracked one; metadata maximum relative difference 8.93e-13.
- `audit_out/gate_B.json`: `all_gate_B_pass = true`; panel rows 3,749,572 / 771,995 / 819,298; usable test rows 538,034 (46,169 positive / 491,865 negative); 456 of 473 test trajectories with usable rows.
- The frozen model's metrics reproduced on this copy (RL-006).

The scratch copies of `data/splits/split_manifest_v3.csv`, `data/metadata/trajectory_metadata_v3.csv`, `data/metadata/generation_config_v3.json` and `data/metadata/feature_schema_v3.json` are byte-identical to the tracked files (`cmp`, verified twice). Being byte-identical to the tracked copies, they are *not* independent evidence about the regenerated rows.

**Conditions enforced at every use (proposed mechanism):**

1. Re-hash all four files and compare with the table above **before** any step reads them (gates G4, G5, G6 and G7). Any difference, or a missing file, makes every data-dependent step **BLOCKED**: stop and report; do not reconstruct or regenerate.
2. Files are used read-only. The execution tree (§4) reaches the data through read-only links, not copies; the code only reads cached panels that already exist. The four hashes are re-checked after the last data-reading step to show the files were not modified.
3. Every Phase 3 table and report header states: "Computed on regenerated v0.3 data (Item 26 copy; hashes in the protocol lock). Not independent replication."
4. Three result categories are never combined: original v0.3 results (E0), earlier regenerated-data results (E1) and newly generated results (E2).

**Risk.** The scratch directory is ephemeral. If it is lost, the data-dependent experiments are BLOCKED; they are not rebuilt.

## 4. Environment (Decision D2 — APPROVED for preparation; NOT created)

**Researcher decision.** Prepare an isolated virtual environment from the pinned requirements. Do not modify dependency files; do not install globally; if a pin cannot be installed, stop and report the exact issue; no silent substitution.

**Current state (verified: artifact):** neither interpreter on this machine has `pyarrow`, so Parquet files cannot be read. `/usr/bin/python3.12` (3.12.3, the version used in Item 26) has no `pandas`, but has `venv` and `ensurepip` importable and `pip 24.0`. The system `python3` (3.13) has `numpy` and `pandas` but is not the tested version and is not used.

**Pins (verified: source, `requirements-pinned.txt`, 23 `==` pins):** scikit-learn 1.9.0 (the only version embedded in the original evidence), numpy 2.5.4, pandas 3.0.6, pyarrow 26.0.0, scipy 1.18.1, joblib 1.6.0, matplotlib 3.11.2, pytest 9.1.1, plus transitive pins. Its header says these are tested pins and not a reconstruction of the original research environment; `REPRODUCIBILITY.md` (line 30) describes it as a full `pip freeze` of the tested environment, which is the basis for installing without dependency resolution.

**The project's own documented install command** is `pip install -r requirements-pinned.txt` (verified: source, `README.md` line 185, `REPRODUCIBILITY.md` line 18; "needs Python >= 3.12").

**Exact command sequence (proposed; none of it has been run):**

```
SCRATCH=/tmp/claude-0/-home-user-AeroGuard/1d37592f-2dfd-5c3e-8f4f-959f6d01ce75/scratchpad
/usr/bin/python3.12 -m venv "$SCRATCH/phase3-venv"
export PIP_REQUIRE_VIRTUALENV=1 PIP_DISABLE_PIP_VERSION_CHECK=1
"$SCRATCH/phase3-venv/bin/python" -m pip install --only-binary=:all: --no-deps -r /home/user/AeroGuard/requirements-pinned.txt
"$SCRATCH/phase3-venv/bin/python" -m pip check
"$SCRATCH/phase3-venv/bin/python" -m pip freeze    # recorded in the protocol lock
"$SCRATCH/phase3-venv/bin/python" -V               # recorded in the protocol lock
```

Why the flags: the venv is called by absolute path and `PIP_REQUIRE_VIRTUALENV=1` makes `pip` refuse a global install; `--only-binary=:all:` avoids building from source; `--no-deps` removes any resolver freedom, so only the listed versions can be installed (the pin file is a full freeze, and `pip check` then fails loudly if anything is missing). `requirements.txt`, `requirements-pinned.txt` and any lockfile are only read.

**Stop rule.** If the network is unavailable, if any pinned version has no installable wheel for CPython 3.12 on this platform, or if `pip check` reports a problem: **stop and report** the package, the version and the exact `pip` error. Do not substitute versions, relax a pin or switch to `requirements.txt`.

**[UNRESOLVED] Not verified offline:** that every pin has a compatible wheel on the package index. This can only be learned by running the install, which is not authorized yet.

**Recording.** The protocol lock records `python -V`, `pip freeze`, the installed `scikit-learn`, `numpy`, `pandas`, `pyarrow`, `scipy` and `joblib` versions, the platform and the CPU count. The pins carry no hashes, so wheel integrity rests on the package index and TLS; this is noted as a limitation.

**Execution tree (proposed).** The code hard-codes data paths relative to its project root (`ml/temporal_config_v03.py`) and would cache panels under `data/ml_temporal_v03/`. To avoid writing into the repository's `data/` or leaving bytecode in the tree, experiments run from a scratch copy built with `git archive` of the approved commit (plus the approved Phase 3 files), with `PYTHONDONTWRITEBYTECODE=1`, and with `data/processed/` and `data/ml_temporal_v03/` linked read-only to the Item 26 files (§3). Only reviewed result files are copied back, and only into the Phase 3 output directory (§14).

## 5. Item 28 — Angle-of-attack baseline

### 5.1 Verified definitions

| Item | Fact | Source |
|---|---|---|
| Quantity | `alpha`: angle of attack, **radians**, `alpha = theta - gamma`; a raw observed state recorded at each row | `data/metadata/feature_schema_v3.json` (verified: source) |
| Availability at prediction time | Current-row value; no future information | same; `aeroguard_dataset/features.py` |
| Stall boundary | `alpha_at_cl_peak = 0.28044009791924895 rad = 16.068034017008504°` (numerically located CL peak; not the parameter `alpha_stall = 0.2793`) | `data/metadata/generation_config_v3.json` (`resolved_stall_boundary`) |
| Event flag | `is_unsafe = |alpha| > alpha_at_cl_peak` — **two-sided** | `aeroguard_dataset/events.py` |
| Target | `future_stall_5s` = 1 if `is_unsafe` is true at any sample in (t, t+5 s]; the current sample is excluded; NaN where fewer than 5 s remain; computed by index with `dt = 0.01 s` | `aeroguard_dataset/labeling.py` |
| Target meaning | A **future-event** label ("an unsafe sample occurs within the next 5 s"). Not stall onset, not the ongoing-stall state. | same |
| Existing rule | `ml/baselines.py` `AoAThresholdRule`: `predict` returns `(alpha > threshold_rad)` as int — **signed alpha, strict `>`** | `ml/baselines.py` |
| Existing selection | `fit(train_alpha, y_train, val_alpha, y_val)`: candidates are the top `top_k = 10` thresholds by train F1 from the train precision–recall curve (alpha as the score); the candidate with the best validation F1 is frozen as `threshold_rad`. The signature has no test argument (guarded by `tests/test_ml_pipeline.py::test_calibration_functions_do_not_accept_test_arguments`). | `ml/baselines.py`, `ml/calibration.py` |
| Units | Threshold stored in radians (`threshold_rad`); degrees (`np.degrees`) appear only in `calibration_info` | `ml/baselines.py` |
| Prior fit (historical, E1) | In the `credibility-v1.1` run the fitted threshold was 0.21723935451615506 rad (12.4469°), fitted on the 1 s-usable train and validation rows; the 10 candidates spanned 0.21723897–0.21724784 rad with validation F1 0.6092–0.6093 | `credibility-v1.1:outputs/analysis_v11/baselines_and_ci.json` |

The selection procedure is compatible with the experimental design: it fits on train and validation only, takes no test argument, and the same top-10 train F1 then best validation F1 helper selected the frozen model's own threshold (verified: source, `ml/temporal_experiment.py::fit_rf_and_threshold`).

### 5.2 What the rule is and is not

- **[SPECIFIED]** The primary AoA baseline is the existing signed `AoAThresholdRule`, **reproduced** by running its unchanged `fit` on the Phase 3 train and validation rows (the same 1 s-usable rows the frozen model used). The threshold is an **output** of the procedure, not an input.
- **[SPECIFIED]** The threshold is **not** a validated physical stall limit and not an externally established safety threshold. The repository contains no externally sourced numeric AoA warning threshold. The paper cites an FAA handbook [10] for "a fixed margin ahead of the critical angle" without a number; I did not read that source. (The paper's 8° starts the *physical precursor* analysis; it is not a warning rule.)
- **[SPECIFIED]** Operator: **strict `alpha > threshold_rad`**, the canonical operator (`ml/temporal_experiment.py::evaluate_on_test` uses `>`).
- **[SPECIFIED]** A positive prediction means "warn: an unsafe sample is predicted within the next 5 s". Prediction is **pointwise**, from the current `alpha` only, with no cross-row or cross-trajectory state. Event-level results (§8) derive from the pointwise flags using the existing episode logic, unchanged.
- **[SPECIFIED]** Trajectory boundaries: no state crosses a trajectory boundary; event construction groups by `trajectory_id`.

### 5.3 Observations about the existing code (recorded, not fixed)

- **Tie conventions differ between calibration and prediction.** `top_k_thresholds_by_train_f1` takes thresholds from `sklearn.metrics.precision_recall_curve`, whose documented convention counts a row as positive when `score >= threshold` (documented scikit-learn behavior; not executed here), while `fit` scores validation F1 with `>` and `predict` uses `>`. The difference affects only rows whose score equals the selected threshold exactly. The same helper selected the frozen model's threshold. No change is made; at execution the number of rows where `>` and `>=` differ is counted and reported (Item 26 found none for the frozen model).
- **Missing and non-finite alpha are not rejected by `predict`.** `(np.asarray(alpha) > thr)` is False for NaN, so a missing alpha is silently predicted safe (verified: source). What `fit` does with NaN scores inside `precision_recall_curve` is **[UNRESOLVED]**: it cannot be run without the environment. **[SPECIFIED]** The Phase 3 wrapper raises on any non-finite `alpha` before calling `fit` or `predict`, and never treats an invalid value as safe. `ml/baselines.py` is not edited.
- `credibility-v1.1` scored the frozen model with `>=` (`pred = (proba >= thr)`); the canonical pipeline uses `>`. Phase 3 uses strict `>` for every method.

### 5.4 Signed vs. two-sided alpha; train-only investigation (Decisions D4 and D16 — APPROVED)

**[SPECIFIED] Primary:** the existing signed rule. It is not replaced. The label is two-sided (`|alpha| > alpha_peak`) and the `stall_margin` docstring notes the negative-alpha caveat, but **the number of unsafe cases with `alpha < 0` is unknown** (not verified). I do not infer that the signed rule captures every unsafe event.

**[SPECIFIED] Train-only investigation (read-only; runs after the environment exists; nothing has been run).** Input: only `data/ml_temporal_v03/temporal_train.parquet`, which contains train-split rows only (verified: source, `ml/temporal_data_v03.py` writes one file per split). Validation and test files are not opened. Quantities, all on train rows:

| # | Quantity |
|---|---|
| Q1 | Unsafe rows with `alpha > 0` and with `alpha < 0` (all train rows) |
| Q2 | Train trajectories containing at least one unsafe row with `alpha < 0` |
| Q3 | Label-positive train rows (1 s-usable) whose future window `(t, t+5 s]` contains negative-side unsafe samples and **no** positive-side unsafe sample ("negative-only positives") |
| Q4 | After the AoA threshold τ is fitted on train and validation: usable train rows with `alpha < -τ`, split by label |

**Decision rule, fixed before any test scoring:** the two-sided sensitivity analysis is run **if and only if Q3 > 0**, because only then are there label-positive rows that a signed `alpha > τ` rule cannot flag through the negative side. If Q3 = 0 it is not run. The Q1–Q4 counts are reported either way. **[UNRESOLVED, confirm]** The criterion "Q3 > 0" is my proposal for the researcher's condition "establishes a reason to investigate"; it is stated here so it exists before any test evaluation.

**Two-sided variant, defined now (so it exists before test evaluation):** score `|alpha|`; threshold selected by the identical procedure (`AoAThresholdRule.fit` called on `|alpha|` arrays of the same train and validation rows); warn iff `|alpha| > τ₂`, strict `>`; the same population and metrics. It is a **separately labelled sensitivity analysis**. Test results are never used to choose between the signed and two-sided variants, and the signed rule remains the primary reproduction regardless of the outcome.

### 5.5 Required tests for the AoA rule (not yet written)

Proposed file: `tests/test_phase3_aoa_rule.py` (synthetic data only).

1. `alpha` just below, exactly at and just above the threshold → 0, 0, 1 (strict `>`).
2. The prediction equals a manual `alpha > threshold_rad` on random data.
3. `np.nan`, `+inf`, `-inf` in `alpha` → the Phase 3 wrapper raises; none is predicted 0.
4. Unit conversion: 0.21723935451615506 rad equals 12.4469° (`np.degrees`); the rule consumes radians and a degrees-scale input is rejected or detectably wrong.
5. Future-event semantics: for a trajectory whose `is_unsafe` first turns on at step k, the label is 1 for rows `k-500 … k-1` and 0 for earlier rows, and the unsafe sample does not label its own row (consistent with `labeling.py` and `tests/test_audit_labels_features_splits.py`).
6. `fit` accepts no test-set argument (reuse the signature check).
7. The selected threshold changes when only validation data change, and does not change when only a "test" array changes.
8. Two-sided variant: the score is `|alpha|`, a negative `alpha` below `-τ₂` is flagged, and the signed rule does not flag it.

## 6. Item 30 — Stall-margin baseline: mathematically equivalent to the AoA rule

**[SPECIFIED] Item 30 is documented as mathematically equivalent to the existing AoA rule. It is not an independent baseline and is never counted as separate evidence.**

**Verified definition (verified: source).** `stall_margin = alpha_at_cl_peak - alpha` (`aeroguard_dataset/features.py`), with a single constant `a_p = 0.28044009791924895 rad` for the one generic aircraft. `ml/baselines.py` `StallMarginThresholdRule` warns when `stall_margin <= threshold_rad` (non-strict).

**Algebra.** Write `m = a_p - α`.

- Margin rule: warn ⇔ `m ≤ τ_m` ⇔ `a_p - α ≤ τ_m` ⇔ `α ≥ a_p - τ_m`.
- AoA rule: warn ⇔ `α > τ_α`.
- Same decision rule when `τ_α = a_p - τ_m`, **except** (i) the margin rule is non-strict and the AoA rule is strict, so they differ only on rows exactly at the threshold, and (ii) `a_p - α` is evaluated in floating point, so decisions can differ at ulp level near the threshold.
- The map `α → -m` is strictly monotone, so any threshold-free metric (PR-AUC, ROC-AUC) computed from `-stall_margin` equals that computed from `α` in exact arithmetic. In floating point, rounding in `a_p − α` can merge nearly equal values into ties, so the two can differ at rounding level; any such difference is measured and reported at the data check below, not assumed to be zero.

**Further observation (verified: source).** `StallMarginThresholdRule.fit` calibrates on the score `-stall_margin` with a strict `>` (equivalent to `m < τ`), but `predict` uses `m <= τ`; calibration and prediction operators differ on rows exactly at the threshold.

**What is not available.** Stall speed, dynamic pressure and a critical-AoA parameter are not columns in the data. (A stall-speed value, `v_stall_m_s = 26.140289984056395`, exists in `generation_config_v3.json` as part of the generation validity envelope; it is not a data column and is **not** used.) No normalized or aircraft-independent margin is defined or claimed. The margin is a simulator-specific distance to the model's own CL peak, with the same negative-alpha caveat as §5.4.

**What will be done once implementation is authorized:**

1. A synthetic test (`tests/test_phase3_equivalence.py`): for random `α` and `τ`, the margin rule and the AoA rule with `τ_α = a_p - τ_m` agree except exactly at the threshold, and agree everywhere when no value is at the threshold.
2. A data check, **not a performance evaluation**: with `τ_α` set to the AoA rule's fitted value, count rows in train, validation and test on which the two rules' decisions differ, and report the count. No metric is reported for the margin rule as a separate method.
3. The report states: "Item 30: mathematically equivalent to Item 28; not evaluated as a separate method."

The stall-margin **trend** rule (margin and `dalpha_dt`; `TrendRule`) is a different method, outside Item 30, and not in the primary comparison without separate authorization.

## 7. Item 31 — Instantaneous-state model

### 7.1 Feature manifest (verified: source — `ml/temporal_config.py::INSTANTANEOUS_STATE_FEATURES`, `outputs/ml_v03/experiment_config.json`, `data/metadata/feature_schema_v3.json`)

| # | Feature | Unit | Origin |
|---|---|---|---|
| 1 | `V` | m/s | raw observation (airspeed) |
| 2 | `alpha` | rad | raw observation (`θ − γ`) |
| 3 | `gamma` | rad | raw observation (flight-path angle) |
| 4 | `pitch_rate` | rad/s | raw observation |
| 5 | `altitude` | m | raw observation |
| 6 | `elevator` | rad | raw **control command** |
| 7 | `throttle` | dimensionless, nominally 0–1 | raw **control command** |
| 8 | `stall_margin` | rad | derived: `a_p − alpha`; exactly redundant with `alpha` |

**[SPECIFIED] Excluded:**

- All windowed temporal features: the ten 1.0 s columns (`alpha_mean_1s`, `alpha_min_1s`, `alpha_max_1s`, `alpha_range_1s`, `alpha_slope_1s`, `alpha_trend_1s`, `V_slope_1s`, `gamma_slope_1s`, `pitch_rate_slope_1s`, `elevator_change_1s`).
- All backward-difference derivatives: `dV_dt`, `dalpha_dt`, `dgamma_dt`, `dq_dt`, `d2alpha_dt2` (each uses the previous sample, so a model with them is not purely instantaneous; that is Model B, a separate question).
- Labels and proxies: `future_stall_5s`, `future_stall_5s_available`, `is_unsafe`, `time_to_stall`.
- Identifiers: `trajectory_id`, `time`, `split`.
- Also not used: `theta`, `vertical_speed`, `thrust` (not in the existing Model A set).

`ml/temporal_experiment.py::get_xy` already raises if a forbidden column is requested and refuses NaN inputs (verified: source).

**Decisions recorded.**

- **Control inputs (`elevator`, `throttle`) stay in**, consistent with the frozen model's inputs. Control-input ablation is Item 33 and is not done here.
- **`stall_margin` stays in** although it is redundant with `alpha`; a monotone transform of an included feature adds no information to a tree model, and keeping it makes the manifest equal the existing Model A.
- `altitude`, `gamma` and `pitch_rate` are current-state variables. They could indirectly encode regime or history. That is a simulator property, not a leak of future labels; it is documented as a confounder (§12), not removed.
- **[ASSUMPTION]** All eight columns exist in the regenerated train, validation and test panels. Checked at G5 by column-name equality with the schema files.

### 7.2 Model and training (D13: no hyperparameter search)

| Item | Value | Status |
|---|---|---|
| Algorithm | `sklearn.ensemble.RandomForestClassifier` via `ml/models.py::build_random_forest` | verified: source |
| Hyperparameters | `n_estimators=200`, `max_depth=12`, `min_samples_leaf=5`, `class_weight="balanced_subsample"` — the existing `FROZEN_RF_PARAMS` (`ml/temporal_config_v03.py`) | verified: source. **No search is performed.** |
| Seed | `random_state = 20260817` | verified: source (`ml/config.py::ML_SEED`, used by `build_random_forest`) |
| Parallelism | `n_jobs=-1`, as in the builder and the saved frozen model | verified: source. Item 26 observed last-bit score differences (max 4.4e-16) between runs of the saved frozen model (historical); this nondeterminism is expected and recorded. |
| Preprocessing | None learned; raw features go to the forest. No scaler is fitted, so no train-only preprocessing is needed. | A test asserts the fitted estimator has no preprocessing step. |
| Train rows | `usable_mask_for_window(train, 1.0)`: 2,443,881 rows (historical) | specified |
| Validation rows | `usable_mask_for_window(val, 1.0)`: 491,322 rows (historical) | specified |
| Threshold | Existing `fit_rf_and_threshold` procedure: top 10 by train F1, best validation F1, applied with strict `>` | specified; verified: source |
| Test access | None during fitting or threshold selection | specified |
| Frozen model | Never retrained or modified | specified |

**Check of the "concrete validity problem" clause (D13).** The shared hyperparameters came from one tuning pass (`tune_rf_hyperparameters`, verified: source) that picked among a two-configuration grid by **validation** PR-AUC on Model D features at the 2.0 s window on the common-subset population; the test split was not touched. Applying them to the 8-feature model therefore carries **no test leakage and no invalid reuse**. They were optimized for the temporal feature set, which may favor the temporal model slightly. That is a documented confounder (§12), not a validity problem requiring a decision. No search is added.

The training population is the **same** rows the frozen model was trained on, which removes unequal training data as a confounder for the primary contrast. The stored Model A (E1) was trained on a 2 s mask and is **not reused** as if it were this protocol's model.

### 7.3 Differences from the frozen temporal model (unavoidable, documented)

- 8 inputs vs. 23: the forest settings match but the learned structure and capacity differ.
- The frozen model was fitted once in the original environment (partly recorded, scikit-learn 1.9.0); the instantaneous model is fitted in the Phase 3 environment.
- The shared hyperparameters were chosen with temporal features (§7.2).

### 7.4 Artifacts and records

New artifacts go to the dedicated Phase 3 output directory (§14), never into `outputs/ml_v03/`. Recorded: feature manifest, hyperparameters, seed, scikit-learn and other versions, data hashes (§3), train/validation row counts, fit duration and peak memory, the threshold-candidate list with train and validation F1 (the original pipeline discarded it), and the model file hash.

### 7.5 Required tests (not yet written)

Proposed file: `tests/test_phase3_instantaneous.py`.

1. The feature list equals the manifest above exactly (8 names, fixed order).
2. The list contains no derivative pattern (`d*_dt*`, `d2alpha_dt2`), no `_0.5s/_1s/_2s` suffix and none of the forbidden columns.
3. Future perturbation: replacing every sample after row `k` of a trajectory leaves the model inputs at rows `≤ k` unchanged.
4. The fitted model has `n_features_in_ == 8` and `feature_names_in_` equal to the manifest.
5. No preprocessing object is part of the fitted estimator.
6. Training uses only train rows; validation rows are used only to choose the threshold; a perturbed "test" array changes neither the model nor the threshold.
7. Output paths are outside `outputs/ml_v03/` and cannot collide with the frozen model path; the frozen model hash is the same before and after.
8. Same seed and data give the same predictions in a single-thread run (determinism of the fit; `n_jobs=-1` last-bit variation is documented separately).

## 8. Item 29 — Common evaluation population, metrics and event semantics

### 8.1 Population construction (Decision D6 — APPROVED; S1 removed)

**[SPECIFIED] Primary population:** the frozen model's own 1 s usable test rows — test-split rows with `future_stall_5s_available == True` **and** all ten 1.0 s window columns non-null (`ml/temporal_features.py::usable_mask_for_window(test, 1.0)`, verified: source). **There is no sensitivity analysis on a larger population in this phase.**

Counts, to be re-derived and reconciled at G5. Sources: the stored metric files (historical, E0), and the Item 26 gate-B record on the regenerated data (verified: artifact, as a record):

| Quantity | Value |
|---|---|
| Dataset rows / trajectories | 5,340,865 / 3,150 |
| Trajectories train / validation / test | 2,205 / 472 / 473 |
| Panel rows train / validation / test | 3,749,572 / 771,995 / 819,298 |
| Usable rows train / validation / **test** | 2,443,881 / 491,322 / **538,034** |
| Eligible test trajectories (≥1 usable row) | 456 (17 test trajectories have none) |
| Test positive rows (`future_stall_5s = 1`) / negative rows | 46,169 / 491,865 |
| Events (maximal runs of `is_unsafe` with a visible row) | 76 (57 first events, 19 later events); the 76 events lie in 57 trajectories (derived from RL-006: no trajectory whose first crossing was excluded has a further unsafe run) |
| Test trajectories containing any unsafe run | 67 (ten have a first crossing with no visible row and contribute no event) |

**Warm-up rule.** The first 100 rows of each trajectory (1.0 s at `dt = 0.01 s`) lack a full history window and are excluded for the temporal model. The AoA rule and the instantaneous model could score those rows but are **not** scored on them, so every method sees the same rows. A test trajectory with no usable row (17 of 473, historical; cause not verified) is out of the population for all methods alike. The population is fixed here and must not be changed after seeing results.

**Row identity.** Each row is identified by `(trajectory_id, step)` with `step = round(time / 0.01)`. The protocol requires, and a test asserts, that: the key is unique; the ordered key arrays for the labels and for every method's scores are exactly equal; no score is missing or NaN for any method (an unavailable prediction is an error, never imputed, dropped or counted as safe); the labels array is exactly equal across methods; and the key array equals the Item 26 `audit_out/score/row_keys.parquet` and `labels.npy` (a cross-check against a prior E1 artifact, not a validation).

**Consecutive-step check (new).** Episodes and event spans are formed by array adjacency, not by time gaps (verified: source, `ml/events.py::group_boolean_into_episodes` — it takes `np.diff` of the flag array and never looks at `times`). The eligible rows of each trajectory must therefore be consecutive steps. **[ASSUMPTION]** This holds because the masks remove only the first 100 rows and the last 500 rows; it is checked at G5 (`diff(step) == 1` within every trajectory), and a violation stops the work.

**No performance-based exclusion.** No row, trajectory or event is added or removed after seeing any score.

### 8.2 Event semantics (verified: source, `ml/events.py`; unchanged)

- A **stall event** is a maximal contiguous run of `is_unsafe` among the rows passed in; its crossing time is the run's first visible row. An event whose rows are all masked out is not counted; an event that began before the first visible row is dated at that row (covered by `tests/test_audit_event_metrics.py`). Events in the last 5 s of a trajectory are masked for every method alike.
- A **warning episode** is a maximal contiguous run of predicted-positive rows, built on the pointwise flags.
- An event is **warned** if a qualifying episode (starting before the crossing and active at some time ≥ crossing − 5 s) exists; the earliest-starting qualifying episode sets the **lead time** = crossing − max(episode start, crossing − 5 s), **capped at 5 s**. One long episode can be credited to several events (16 of the 19 later events share their trajectory's first-event episode, per RL-006, historical), so **events are not independent**.
- A **false-alarm episode** is a warning episode whose first row has `future_stall_5s == 0`; an episode whose first row has an NaN label is "undetermined" and excluded from the rate (expected to be zero on the eligible rows; the count is reported at G7).
- No new merging rule is introduced.

### 8.3 Metrics (Decision D8 — APPROVED)

| Role | Metric | Unit of analysis | Notes |
|---|---|---|---|
| **Primary** | PR-AUC (`sklearn.metrics.average_precision_score`, the function in `ml/evaluation.py`, verified: source) | rows | Threshold-free. AoA score = `alpha`; the instantaneous and frozen models score by predicted probability. |
| Secondary | ROC-AUC (`roc_auc_score`) | rows | Defined for these continuous scores; not computed for any constant-score rule (none is used). |
| Secondary | Precision, recall, F1 and the confusion matrix | rows | At each method's own validation-selected threshold, strict `>`. |
| Secondary | Event detection rate (warned / 76) | events | Events are not independent. |
| Secondary | Lead time (median, mean, minimum, maximum, count at the 5 s cap) among warned events | events | Capped at 5 s; median among warned events only. |
| Secondary | False-alarm episodes per eligible simulated hour; false-alarm and true-warning episode counts | episodes | Denominator below. |

PR-AUC and ROC-AUC do not depend on a threshold. The AoA and instantaneous-model thresholds affect **only** the threshold-dependent secondary rows. Positive rows are about 8.6% (46,169 / 538,034), so accuracy is not a headline metric. Row, trajectory and event counts are always reported separately; rows within a trajectory are strongly correlated and are not treated as independent observations.

### 8.4 Denominator for "per simulated hour" (verified: source and arithmetic)

`ml/temporal_experiment.py::run_false_alarm_analysis` computes `total_test_trajectory_seconds` as the sum over trajectories of (max time − min time) of the **evaluated rows**, and `false_alarms_per_minute = false_alarm_episodes / (total_seconds / 60)`.

The stored value is 5,375.78 s (historical). Row count × `dt` would be 538,034 × 0.01 = 5,380.34 s. The 4.56 s difference equals **456 trajectories × 0.01 s**, because a span has one fewer interval than it has samples: (538,034 − 456) × 0.01 = 5,375.78 s exactly. This agrees with the stored value; it assumes the evaluated rows of each trajectory are consecutive at `dt`, confirmed at G5 (§8.1).

**[SPECIFIED]** The primary denominator is the existing one (sum of per-trajectory spans of the evaluated rows; 5,375.78 s ≈ 1.493 h if the counts reconcile). The row-count × `dt` value is reported alongside it. These are **eligible simulated time**, not trajectory durations and not operational flight hours; they exclude the first 1 s and the last 5 s of every trajectory.

### 8.5 Matched operating point (Decision D12 — not included; dormant template)

**Finding.** I searched `README.md`, `REPRODUCIBILITY.md`, `PROVENANCE.md`, `paper/AeroGuard_Research_Paper.md`, `experiments/EXPERIMENT_LOG.md` and `outputs/ml_v03/v03_temporal_ml_report.md` for an operational requirement (false-alarm budget, minimum recall, acceptable alarm rate) and found none (verified: source, keyword search). **No defensible operational target is established, so no matched-operating-point analysis is included.** I will not invent a target.

**What is done instead.** The primary PR-AUC comparison is retained. Threshold-dependent operational metrics (precision, recall, F1, event detection, lead time, false-alarm rate) are reported **separately**, each at that method's own validation-selected operating point, under the heading "not matched across methods; do not rank". Two methods at different operating points are not comparable on these numbers (a lax threshold gives high event detection and many false alarms).

**Dormant template, to be used only if the researcher supplies a target** (nothing below is active):

- **Target:** one researcher-stated metric and value on the **validation** split, e.g. "validation false-alarm episodes per eligible hour ≤ T" or "validation event recall ≥ R". The target is not chosen by me and is fixed before any test scoring.
- **Threshold selection:** for each method, the threshold is chosen from **validation scores only**: among thresholds that meet the target, the one that maximizes a single pre-stated secondary metric (ties broken by the larger threshold); the test split is never used.
- **Feasibility check:** before any test scoring, compute on validation the range of the target metric each method can reach. If a method cannot meet the target, record "target not attainable" with its best attainable value; **do not change the target** and do not substitute a different threshold rule.
- **Handling of methods that cannot meet the target:** they are excluded from the matched comparison and reported as not attainable; the other methods are still reported.
- A target defined **relative to the frozen model's own validation operating point** is a comparative design choice, not an operational target. It is **not** included without separate explicit approval.

## 9. Item 32 — Temporal vs. instantaneous comparison

### 9.1 Methods compared

1. AoA rule (§5), reproduced on the Phase 3 train and validation rows.
2. Instantaneous Model A (§7), newly trained.
3. Frozen temporal AeroGuard model, `outputs/ml_v03/models/primary_model_D_1s.joblib` (SHA-256 `707d4c61a791af940549f81520a0c8429edaa8ef8d67eb0f02c3174c5fe603f3`; verified at preparation time, as are 79/79 baseline hashes), loaded and scored **as saved, never refitted**, with the stored feature list and threshold 0.8585534589255494, strict `>`.

Stall margin appears only as an equivalence result (§6). Model B and the trend rule are not part of the comparison.

### 9.2 Primary contrast

**[SPECIFIED]** Primary contrast: **ΔPR-AUC = PR-AUC(frozen temporal) − PR-AUC(instantaneous Model A)** on the primary population. Secondary contrasts: temporal − AoA, and Model A − AoA. All differences carry paired intervals (§9.3); there is no multiplicity adjustment, and the three are labelled one primary and two secondary.

### 9.3 Uncertainty (Decisions D8 and D15 — APPROVED)

**[SPECIFIED] Bootstrap:** **B = 1000** paired trajectory-bootstrap resamples, **seed 20261013**, percentile intervals (2.5th and 97.5th percentiles of the replicate values). The seed was chosen on 2026-10-13 before any Phase 3 scoring; it is not chosen or changed based on results. `git grep` finds 20261013 nowhere in `HEAD`; the `credibility-v1.1` script used 20261011, which is deliberately not reused (verified: source).

**Verification that the trajectory is the appropriate resampling unit (verified: source):**

- Trajectories are generated one at a time from a single master random stream; each draws its own initial airspeed and altitude and its own control profile (`aeroguard_dataset/dataset_builder_v3.py`: `rng.uniform(...)` for `V0` and `h0`, a fresh `build_*_profile(rng, ...)` per trajectory). No two trajectories share a drawn profile, and `tests/test_audit_labels_features_splits.py::test_v03_has_no_duplicate_initial_conditions_across_trajectories` checks for duplicate initial conditions.
- Regime labels are assigned from fixed global counts and shuffled (`assign_regime_list`), and the train/validation/test split is a random permutation of trajectory IDs that is **not** stratified by regime (`aeroguard_dataset/splitting.py`). The test regime mix is therefore a random draw, not a designed mixture.
- Rows within a trajectory form one continuous physical flight and are strongly dependent; events and warning episodes are constructed within a trajectory. The trajectory is therefore the smallest unit that is plausibly independent of the others, and is the unit the split already treats as atomic.
- Caveats: the global regime counts are fixed rather than i.i.d., the pseudo-random draws are deterministic, and a bootstrap that resamples test trajectories conditions on the one realized test set. These limit the interval to test-sampling uncertainty (below).

**Procedure.** Resample the 456 eligible trajectory IDs **with replacement**, keeping all rows of a drawn trajectory together. Within one replicate the **same** drawn set is used for every method, and each difference is computed per replicate (paired). A replicate with no positive rows has undefined PR-AUC; such replicates are counted and reported, not silently dropped.

**Event-level metrics** are bootstrapped through their trajectories. All 76 events lie in only 57 of the 456 trajectories, and 16 of the 19 later events share an episode with a first event, so the effective number of independent units for event metrics is far below 76; percentile intervals for proportions near 100% (e.g. 76/76) are degenerate and uninformative.

**Limitations of the interval.** It reflects test-set sampling only, not training-set or seed variability (the frozen model was fitted once; the instantaneous model is fitted once); it treats the 456 trajectories as exchangeable although the dataset is a mixture of regimes (500 normal, 250 stall, 2,400 `gradual_approach_v3` over all splits); and an interval excluding zero is statistical evidence under this resampling model, not a p-value and not proof of a causal effect.

### 9.4 Interpretation rules, fixed in advance

1. Report the point estimate, the interval and the absolute values for every method.
2. Report **statistical evidence** (does the paired interval for ΔPR-AUC include 0?), **magnitude** (the size of ΔPR-AUC), **practical significance** and **scientific significance** separately.
3. A higher score for the temporal model is **not** described as proof that temporal reasoning caused it. At most: "the frozen temporal model scored higher/lower than this instantaneous model under this protocol".
4. If the interval for ΔPR-AUC includes 0, the report says no difference was demonstrated; it does not say the models are equivalent.

### 9.5 Meaningful-improvement criterion (Decision D10 — APPROVED as "do not invent")

**[SPECIFIED] No minimum meaningful improvement is defined, and none will be invented.** The repository contains no operational requirement or domain evidence from which a margin could be derived. The report presents observed differences and uncertainty and **makes no claim of practical superiority**. A margin δ may be supplied by the researcher with a stated rationale **before scoring**; a margin chosen after seeing results is invalid and will not be used.

## 10. Prior test exposure (Decision D9)

The planned evaluation is a **controlled re-evaluation of previously exposed data**, not a blind or untouched test.

Test trajectories and labels have already been used, and test results examined, in these places:

1. The original v0.3 frozen-model evaluation (E0): `outputs/ml_v03/metrics/*`.
2. The v0.3 ablation (E0/E1): Models A, B and D_w scored on the test split at the 2 s common subset (`common_subset_ablation*.csv`).
3. The `credibility-v1.1` run (E1): the AoA rule, the margin-trend rule and the frozen model scored on the same 538,034 test rows, with trajectory-bootstrap intervals.
4. Item 26 (E1): the frozen model re-scored on the regenerated test split, with the row-level scores saved in scratch.
5. The protocol author (this assistant) read the stored numbers in §2.1 before writing the design, so the choice of population, comparator and metrics was not made blind to the earlier results.

- The same test trajectory IDs (from the unchanged tracked split manifest) and the same label definition are reused; the rows come from the regenerated copy.
- **Can establish:** a pre-registered, controlled comparison of three methods on one common population, with traceable provenance and trajectory-level uncertainty.
- **Cannot establish:** performance on untouched data; independent confirmation of earlier results; generalization to real aircraft.
- Historical results are not erased, replaced or rewritten.
- Safeguards that remain valid: thresholds and models are fixed from train and validation before test scoring; each method's test scores are computed once (§11); the primary contrast, metrics, population and seed are written here before any new scoring.

## 11. Randomness and single-shot rule

- Seeds are fixed in advance: forest `random_state = 20260817`; bootstrap seed 20261013. No seed is chosen or changed after seeing results; no seed sweep is run.
- **Single-shot rule.** After G6 (rules and model frozen), each method's test scores are computed once. A bug found afterwards is recorded as a dated deviation, and **both** the original and the corrected outputs are retained and reported. Nothing is tuned against test metrics.

## 12. Confounders to be documented in the report

| Confounder | Handling |
|---|---|
| Unequal training data | The same 2,443,881 train rows (historical) for the instantaneous model and (by construction) the frozen model; the AoA rule is fitted on the same rows. |
| Unequal model capacity / inputs | Same forest settings; 8 vs 23 inputs; documented, not removable. |
| Frozen model fitted once in the original environment; instantaneous model fitted in the new one | Documented. Run-to-run variance is not measured (a seed sweep is out of scope). |
| Hyperparameters tuned (on validation, with temporal features) for the temporal model, reused unchanged for 8 features | Documented in §7.2; may favor the temporal model; no search is added. |
| Population / warm-up | One fixed population (§8.1); no larger-population analysis. |
| Operating-point mismatch for threshold-dependent metrics | §8.5: reported separately and labelled not matched. |
| Scenario/regime imbalance | The dataset is dominated by `gradual_approach_v3` (2,400 of 3,150 trajectories). Per-regime results are descriptive only. |
| Instantaneous variables that encode regime (`altitude`, `V`, controls) | Documented as a simulator property. |
| Label leakage | The label is computed from future samples and excluded from all inputs; tests in §5.5, §7.5 and the existing audit tests. |
| Threshold-selection bias | F1-based selection on one train/validation split; tie-convention note in §5.3. |
| Non-independent events within a trajectory | §9.3. |
| Prior test exposure | §10. |
| Regenerated data | §3. |
| Floating-point non-determinism | `n_jobs=-1` last-bit differences (Item 26). The 1e-9 PR-AUC band seen there is documented, not corrected. |

## 13. Required tests and validation (synthetic or metadata-only until G5)

Proposed new files, **none created**. They follow the existing pytest conventions (`tests/test_audit_*.py`).

| File | Content |
|---|---|
| `tests/test_phase3_aoa_rule.py` | §5.5 |
| `tests/test_phase3_equivalence.py` | §6 synthetic equivalence and operator-at-tie behavior |
| `tests/test_phase3_instantaneous.py` | §7.5 |
| `tests/test_phase3_population.py` | Row-identity key uniqueness and equality across methods; identical labels; same eligible timestamps; unavailable predictions raise; reconciliation of row, trajectory and event counts against the §8.1 values; consecutive steps within each trajectory; the hours denominator equals Σ(nᵢ−1)·dt; trajectory-boundary handling; no train/validation/test trajectory overlap (reuse `verify_no_overlap`) |
| `tests/test_phase3_negative_alpha.py` | The Q1–Q4 investigation reads only the train panel; its counts are correct on a small synthetic example; the §5.4 decision rule is applied mechanically; the investigation code cannot reference the validation or test files |
| `tests/test_phase3_bootstrap.py` | Resampling unit is the trajectory; paired replicates share the draw; seed 20261013 and B = 1000 are the configured values; a fixed seed gives identical intervals; replicates without positives are counted; PR-AUC and ROC-AUC match a direct computation on a small example |
| `tests/test_phase3_integrity.py` | Frozen model hash and the 79 baseline hashes unchanged; the four data-file hashes are re-checked; no write to `outputs/ml_v03/`; test arrays never reach `fit` |

**Commands (after the environment exists; run only these files, not the full suite):**

```
<venv>/bin/python -m pytest tests/test_phase3_*.py -q
sha256sum -c baselines/v0.3.sha256
sha256sum outputs/ml_v03/models/primary_model_D_1s.joblib   # expect 707d4c61a791af940549f81520a0c8429edaa8ef8d67eb0f02c3174c5fe603f3
```

Unit tests establish implementation behavior only; they cannot validate an aerodynamic assumption or the scientific adequacy of the design.

## 14. Outputs (Decision D14 — APPROVED: dedicated directory; no overwrite; no commit)

**Verified now:** `outputs/phase3/` does not exist, no tracked path contains "phase3" other than this protocol, and `git check-ignore` does not ignore `outputs/phase3/` (so new files there would appear as untracked).

- **Location:** a dedicated `outputs/phase3/`, separate from `outputs/ml_v03/`, `outputs/analysis_v11/`, `outputs/ml_baseline/` and every historical or frozen artifact.
- **No overwrite:** every output file is created exclusively (an existing path is an error), and each run writes into its own subdirectory `outputs/phase3/run_<UTC timestamp>/`. Nothing is replaced.
- **Contents (proposed):** `protocol_lock.json` (SHA-256 of the approved protocol, seeds, data hashes, `pip freeze`, git commit), `population.json`, `negative_alpha_train.json`, `aoa_rule.json` (with the full candidate list and their train and validation F1), `model_a_config.json`, `feature_manifest.json`, `model_a_fit_record.json` (runtime, memory), `metrics_primary.json` and `.csv`, `bootstrap.json`, `equivalence_check.json`, `sensitivity_two_sided.json` (only if §5.4 triggers), `REPORT.md` and the final audit record.
- **Where produced:** in the scratch execution tree (§4). Reviewed files are copied into the repository's `outputs/phase3/` only after review, and **they are not committed or pushed without separate authorization**.
- Row-level scores (about 4 MB per method as `float64`) and the instantaneous model file are produced in scratch; whether they are retained in the repository is a later decision.
- Tables and plots are generated from the machine-readable results only; plots will not imply significance.

## 15. Execution gates

No gate may be passed without the stated approval. Nothing in this protocol authorizes passing any gate.

| Gate | Step | Needs |
|---|---|---|
| G0 | Review of this revised protocol; its SHA-256 is recorded as the lock | Researcher approval of v0.2 (or edits) |
| G1 | Create the isolated environment and install the pins exactly as in §4; stop on any failure | D2 is approved in principle; run only after G0 and an explicit go-ahead |
| G2 | Write the tests and thin Phase 3 code in new files | Approval of the file list (§13, §14) |
| G3 | Synthetic and metadata-only tests; no data access | — |
| G4 | Re-hash the four data files (§3); read the schema; run the train-only negative-alpha investigation (§5.4; D16 approved) | G1 done; protocol lock recorded |
| G5 | Population and count reconciliation against §8.1 (reads labels and keys, **no predictions or scores**), including the consecutive-step check; stop on any mismatch | — |
| G6 | Fit the AoA rule and the instantaneous model on train and validation only; record thresholds; freeze; hash the artifacts | Approval to train |
| G7 | **Score the test population once per method** and compute metrics | **Separate explicit approval of the final evaluation** |
| G8 | Paired bootstrap (B = 1000, seed 20261013), report, diff audit, protected-artifact check | — |

Stop conditions at any gate: any protected-artifact mismatch, a count that does not reconcile, a missing or changed data file, an unavailable dependency version, or an unexplained working-tree change.

## 16. Protected artifacts and prohibitions

Never modified, regenerated, retrained, replaced, merged or published by Phase 3: the frozen model and its metrics; `outputs/ml_v03/`; the original v0.3 artifacts and historical results; the paper and PDF; the Zenodo record; `main`; `credibility-v1.1` (read only, never checked out, merged or cherry-picked). No dataset regeneration. No retraining of the frozen model. No tag, release, deployment or publication. No commit or push without separate authorization. Existing scientific source files (`ml/`, `aeroguard/`, `aeroguard_dataset/`, `scripts/`) are not edited; new code goes into new files.

## 17. Decision register (researcher decisions received 2026-10-13)

| ID | Decision | Status |
|---|---|---|
| D1 | Data source | **APPROVED:** read-only use of the existing regenerated copy, conditional on verified availability, hashes, manifest and provenance (§3); never regenerate; BLOCKED if missing or invalid. |
| D2 | Environment | **APPROVED for preparation** (§4): isolated venv from the pins; no dependency-file changes; no global install; stop on any pin failure. **Not created.** |
| D3 | AoA threshold | **SPECIFIED:** existing train-then-validation procedure; external option unsupported by repository evidence. |
| D4 | Signed vs. two-sided α | **APPROVED:** signed primary; two-sided only as a labelled sensitivity analysis if the train-only investigation gives a reason (§5.4). |
| D5 | Item 30 | **SPECIFIED:** equivalence only (§6). |
| D6 | Common population | **APPROVED:** the frozen model's 538,034 rows; **S1 (warm-up sensitivity) is not part of this phase.** |
| D7 | Instantaneous manifest | **SPECIFIED:** the eight features (§7.1), subject to the column check at G5. |
| D8 | Metrics and statistics | **APPROVED:** PR-AUC primary; secondary and event-level measures; paired trajectory bootstrap with 1,000 resamples; the trajectory unit, event semantics and hours denominator are verified (§8, §9.3). |
| D9 | Prior test exposure | **SPECIFIED:** disclosed (§10). |
| D10 | Meaningful improvement | **APPROVED:** none invented; no claim of practical superiority without a defensible criterion (§9.5). |
| D11 | Re-run AoA here | **SPECIFIED:** yes, reproduced on the Phase 3 rows. |
| D12 | Matched operating point | **APPROVED as conditional:** no defensible operational target exists, so it is not included; dormant template in §8.5. |
| D13 | Hyperparameter check | **APPROVED as "not added":** the existing Model A configuration is used; the validity check found no concrete problem (§7.2). |
| D14 | Outputs | **APPROVED:** dedicated `outputs/phase3/`; no overwrite; no commit or push without separate authorization (§14). |
| D15 | Bootstrap | **APPROVED:** B = 1000, seed 20261013 (§9.3). |
| D16 | Train-only negative-alpha count | **APPROVED:** train data only (§5.4); not yet run. |

## 18. Source-code recheck performed for this revision

All entries were re-read in the current repository source or artifact on 2026-10-13. "Verified" means I read it; nothing was executed except hashing and file comparison.

| Claim | Where checked | Result |
|---|---|---|
| `AoAThresholdRule` uses signed α, strict `>`, top-10 train F1 then best validation F1, radians | `ml/baselines.py` | Verified |
| Calibration helper takes thresholds from `precision_recall_curve`; validation F1 uses `>` | `ml/calibration.py` | Verified (the `>=` convention of `precision_recall_curve` is documented scikit-learn behavior, not executed here) |
| `StallMarginThresholdRule`: calibrates on `-margin` with `>`, predicts `margin <= threshold` | `ml/baselines.py` | Verified |
| `stall_margin = alpha_at_cl_peak − alpha`; `is_unsafe = |alpha| > alpha_at_cl_peak` | `aeroguard_dataset/features.py`, `events.py` | Verified |
| `alpha_at_cl_peak = 0.28044009791924895 rad (16.068034017008504°)`; `alpha_stall = 0.2793`; `v_stall_m_s = 26.140289984056395` | `data/metadata/generation_config_v3.json` | Verified |
| Label window `(t, t+5 s]`, NaN where the future is incomplete, horizon 500 steps at `dt = 0.01` | `aeroguard_dataset/labeling.py`; generation config | Verified |
| Instantaneous features (8 names) and the ten 1.0 s window columns | `ml/temporal_config.py` | Verified |
| `FROZEN_RF_PARAMS`, `ML_SEED = 20260817`, `n_jobs=-1`, `random_state = ML_SEED` | `ml/temporal_config_v03.py`, `ml/config.py`, `ml/models.py` | Verified |
| Tuning picked from a 2-configuration grid by validation PR-AUC on Model D at 2.0 s | `ml/temporal_experiment.py::tune_rf_hyperparameters` | Verified |
| `evaluate_on_test` uses strict `>`; `fit_rf_and_threshold` never references test | `ml/temporal_experiment.py` | Verified |
| `usable_mask_for_window` = label available and all window columns non-null | `ml/temporal_features.py` | Verified |
| Episodes formed by array adjacency (`np.diff`), not by time gaps | `ml/events.py::group_boolean_into_episodes` | Verified (new check, §8.1) |
| Event lead-time rule, 5 s cap, false-alarm rule | `ml/events.py` | Verified |
| Hours denominator = Σ per-trajectory (max time − min time) of evaluated rows | `ml/temporal_experiment.py::run_false_alarm_analysis` | Verified; 5,375.78 s = (538,034 − 456) × 0.01 |
| Trajectories drawn independently from one master RNG; regime counts fixed and shuffled | `aeroguard_dataset/dataset_builder_v3.py` | Verified |
| Split is a random permutation of IDs, not stratified | `aeroguard_dataset/splitting.py` | Verified |
| `temporal_data_v03.py` writes one panel file per split | `ml/temporal_data_v03.py` | Verified |
| No operational false-alarm/recall target in the project documents | keyword search of six documents | Verified (absence of evidence for the patterns searched) |
| Pinned requirements: 23 `==` pins; documented install command | `requirements-pinned.txt`, `README.md`, `REPRODUCIBILITY.md` | Verified |
| Four data-file hashes and sizes unchanged | `sha256sum` / `stat` | Verified twice |
| Scratch manifests and metadata byte-identical to tracked files | `cmp` | Verified twice |
| Item 26 gate A and B records pass | `audit_out/gen_diag/gate_A.json`, `audit_out/gate_B.json` | Read, not re-run |
| Frozen model hash and 79/79 baseline hashes | `sha256sum` | Verified |
| `outputs/phase3/` absent and not git-ignored | `ls`, `git check-ignore` | Verified |

## 19. Remaining blockers and unresolved items

**Blockers (nothing can proceed until these are cleared):**

1. **G0 — approval of this revised protocol (v0.2)**, or edits to it.
2. **G1 — explicit go-ahead to create the environment.** D2 is approved in principle only; no environment exists.

**Unresolved facts (cannot be settled without the environment or data):**

3. That every pinned package has an installable wheel for CPython 3.12 on this platform (needs the network).
4. What `AoAThresholdRule.fit` does with NaN scores (not run).
5. The negative-alpha counts Q1–Q4 (D16 approved; not run).
6. All counts marked (historical), including 538,034 rows, 456 trajectories and 76 events, until G5.
7. That the evaluated rows of every trajectory are consecutive steps (G5).
8. That all eight instantaneous columns exist in the regenerated panels (G5).
9. The cause of the 17 test trajectories with no usable row (not needed for the design).

**Researcher choices still open:**

10. Confirmation of the criterion "Q3 > 0" for running the two-sided sensitivity analysis (§5.4).
11. Optional: a margin δ for a practical-significance claim (D10), to be stated before scoring.
12. Optional: an operational target for a matched-operating-point analysis (D12); without one it stays excluded.

**Later approval gates:** G2 (file list), G6 (approval to train), G7 (separate approval of the final evaluation), and any commit or push of the protocol or outputs.

## 20. Known limitations of this protocol

- All counts marked (historical) come from earlier records and have not been re-derived because no environment is available; they are verified at G5, and a mismatch stops the work.
- The regenerated copy's identity is supported by the Item 26 gates and by file hashes first recorded at protocol preparation; the original dataset is unavailable for a direct comparison, and the original model's row-level scores were never saved.
- The original research environment is only partially recorded (scikit-learn 1.9.0); other versions are tested pins without package hashes.
- The scratch tree, and this untracked protocol file, are ephemeral until committed.
- The design depends on a single simulated aircraft and a synthetic trajectory generator.
- The eligible simulated time is about 1.5 h, and the independent units (456 trajectories, 57 with events) are few for event-level inference.

## 21. Approval record

| | |
|---|---|
| Protocol status | DRAFT v0.2 (decisions incorporated; awaiting approval) |
| Approved by | *(pending)* |
| Approval date | *(pending)* |
| SHA-256 of approved file | *(to be recorded at approval)* |
| Amendments after approval | *(none; any amendment must be dated and justified here before the affected step)* |

*No experiment, environment creation, package installation, training run, scoring of the held-out population, commit, push, merge, release or deployment has been performed under this protocol.*
