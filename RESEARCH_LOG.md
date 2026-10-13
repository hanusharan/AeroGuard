# AeroGuard Research Log

A running record of research hypotheses, experiment decisions, failures,
findings, limitations and future decisions.

- **Software and repository changes** go in [`CHANGELOG.md`](CHANGELOG.md).
- **Exact reproduction commands** are in [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md).
- **File status** (canonical, historical, rejected) is in [`PROVENANCE.md`](PROVENANCE.md).
- **The results of the frozen v1.0 research** are summarized chronologically in
  [`experiments/EXPERIMENT_LOG.md`](experiments/EXPERIMENT_LOG.md) and in full in
  [`outputs/final/AEROGUARD_FINAL_RESEARCH_REPORT.md`](outputs/final/AEROGUARD_FINAL_RESEARCH_REPORT.md).
  This log does not repeat them; it records the reasoning and decision trail
  around them and everything that comes after.

AeroGuard is a simulation study of a simplified 2D longitudinal flight model. No
entry here is a statement about real aircraft.

## 1. Rules

1. **Separate the kinds of statement.** Every entry labels what is a
   *hypothesis*, what was *done* (experiment, method, configuration), what was
   *observed* (measured results), what is *interpretation*, what is *uncertain*,
   what was *decided and why*, and what is *planned*. Never present a hypothesis,
   interpretation or plan as a result.
2. **Dates are real or absent.** Use the date something actually happened. If it
   is not known, write `undocumented`. Do not back-fill dates from memory or
   infer them from file timestamps.
3. **Cite the artifact.** Every result links to the report, metrics file, script
   or seed that produced it. A number with no source is not an observation.
4. **No result counts as independently validated** unless someone other than the
   original experimenter has reproduced it. Passing tests, an LLM-assisted review
   or a re-run by the same author do not qualify.
5. **Record failures and null results.** An experiment that did not work, a
   hypothesis that was not supported, and a calibration that was rejected get an
   entry with the same detail as a success. Do not delete or soften them.
6. **Never rewrite history.** Do not edit an old entry's result, configuration or
   decision. If something was wrong, add a new entry (or a dated *Correction* under
   the old one) that says what changed and why. If a later experiment changes a
   method, model, dataset, threshold or evaluation procedure, record that as its
   own decision and keep the earlier configuration visible.
7. **Preregister when possible.** Write the hypothesis and expected outcome
   *before* running the experiment, and note the date. If it was written
   afterwards, say so.
8. **Frozen artifacts stay frozen.** The v0.1–v0.3 datasets, the model
   `outputs/ml_v03/models/primary_model_D_1s.joblib`, and the existing reports are
   not modified; new work gets new files and new entries.
9. **Authorship.** Entries record who decided and who ran what only where that is
   actually known. The project's research idea is the author's; Claude Code
   assisted with implementation (see the README's "AI assistance"). Do not
   attribute a decision to a person or tool unless the record shows it.

## 2. Entry template

Copy this block, give it the next ID, and add it at the end of §4 (newest last).
Leave unknown fields as `unknown` or `pending`; do not fill them with guesses.

```markdown
### RL-NNN — <short title>

- **Date:** <YYYY-MM-DD, or `undocumented`>   **Status:** <planned | running | complete | abandoned>
- **Research question / hypothesis:** <the claim being tested, written before the experiment>
- **Motivation and prior evidence:** <what led here; link earlier entries and reports>
- **Experiment or investigation:** <what will be / was done>
- **Data and configuration:** <dataset version, seeds, split, model, features, thresholds, commit>
- **Expected outcome:** <what would support / contradict the hypothesis, stated in advance>
- **Observation or result:** <measured outcomes only, with numbers and sample sizes, or `pending`>
- **Interpretation:** <what the authors think it means; clearly marked as interpretation>
- **Limitations and uncertainty:** <sample sizes, simulation scope, confounds, what was not tested>
- **Decision and rationale:** <what was decided next and why, or `pending`>
- **Follow-up work:** <open questions and next steps>
- **Supporting artifacts:** <links to reports, metrics, scripts, plots>
```

## 3. Historical baseline (incomplete)

The entries below are a **retrospective** index of the research recorded in
the repository before this log existed. They were assembled from existing
reports, not written at the time, so *Interpretation* lines restate what those
reports conclude and are not new analysis. The repository's first commit is
2026-08-18, but it is a snapshot of already-completed v0.1–v0.3 work, and none
of the reports below carry dates: **the dates of these experiments are
undocumented.** Where the reasoning behind a choice is not in the reports, it is
marked as such rather than reconstructed.

### RL-H01 — v0.1/v0.2 datasets and the first temporal model

- **Date:** undocumented. **Status:** complete (frozen).
- **Recorded:** v0.1 had 1,000 trajectories, 187 of which crossed the stall
  boundary. v0.2 (1,000 trajectories, 1,753,615 rows) fixed ground-contact
  handling and renamed/recalibrated the boundary regime. On v0.2, the baseline
  instantaneous RandomForest scored test PR-AUC 0.742; the temporal model (23
  features) scored PR-AUC 0.813 with 100% event recall (14/14) but a median
  credited lead time of only **0.53 s**, with no event warned 4 s ahead.
- **Interpretation (as the reports state it):** the model behaved mainly as an
  imminent-event detector. The first sub-second precursor was the problem to
  explain.
- **Limitations:** 14 events is a small sample.
- **Undocumented:** why the v0.2 control profiles were chosen as they were.
- **Artifacts:** [`experiments/EXPERIMENT_LOG.md`](experiments/EXPERIMENT_LOG.md),
  [`outputs/ml_temporal/temporal_experiment_report.md`](outputs/ml_temporal/temporal_experiment_report.md),
  [`outputs/dataset_audit_v2/audit_report_v2.md`](outputs/dataset_audit_v2/audit_report_v2.md).

### RL-H02 — Precursor diagnosis

- **Date:** undocumented. **Status:** complete.
- **Hypothesis (as stated in the final report §3):** the short precursor came
  from how control inputs were generated (fast elevator pulses aimed past the
  boundary), not from the flight dynamics, so re-timing the inputs without
  touching the physics could produce a real multi-second precursor. Whether this
  was written before the diagnosis or afterwards is undocumented.
- **Method:** read-only, trajectory-aligned analysis of v0.2 (angle of attack,
  elevator, stall margin) plus a 150-trajectory calibration of five candidate
  control profiles; no physics or v0.1/v0.2 data were modified.
- **Recorded result:** the fast control profiles moved through the precursor
  region quickly; the report diagnoses a control-profile timing artifact rather
  than a hard physics limit.
- **Limitations:** this was a diagnosis on v0.2 trajectories, not a test on
  real aircraft.
- **Artifacts:** [`outputs/precursor_diagnosis/FINAL_REPORT.md`](outputs/precursor_diagnosis/FINAL_REPORT.md),
  [`outputs/precursor_diagnosis/precursor_diagnosis_report.md`](outputs/precursor_diagnosis/precursor_diagnosis_report.md).

### RL-H03 — v0.3 control-profile calibration (conflicting results, then reconciled)

- **Date:** undocumented. **Status:** complete; decision trail retained.
- **Investigation:** two concurrent Claude Code sessions ("RUN A" and "RUN B")
  independently worked on the same calibration task and reached different
  verdicts. This is documented in the reports and in `PROVENANCE.md` §3; the
  conflicting code and results were kept, not deleted.
- **Recorded results:**
  - *RUN B* (five single-pulse candidates, seeds 20260818–20260822, 150
    trajectories): **NO-GO** — 57–80% of trajectories ended on the flight-path
    angle limit and no candidate produced a ≥3 s precursor event.
  - *RUN A* (a sweep including a two-stage, two-pulse "Candidate D", seed
    20260817, 175 trajectories): **GO** on Candidate D (22.9% crossed, 31.4%
    ended on the flight-path angle limit, headline 87.5% of crossings with ≥3 s
    precursor).
  - *Reconciliation:* same physics, stall boundary and crossing definitions; the
    verdicts differed because of the candidate design and the precursor metric
    (RUN A counted from the first touch of 8°, RUN B from the last sample below 8°
    before the final approach). Reproducing RUN A's call reproduced its aggregate
    numbers exactly (22.9% / 31.4%). With the direction-aligned metric the ≥3 s
    figure was 33.3% (6 of 8 usable crossings). Tracing all 8 crossings showed 3
    were genuinely gradual and at least 5 had an inflated precursor (a metric
    artifact, a dive-then-zoom manoeuvre, or both).
  - *Candidate D v2* (same-sign pulses, zero gap): per-crossing quality improved
    but flight-path-angle termination rose from 31.4% to 57.7%: **CASE B**.
  - *Candidate D v3* (duration cap): 21/21 clean crossings, termination 28.6%,
    ≥3 s coverage 53.8%, crossing rate down to 12.0%: **CASE A — ready for full
    generation**, with a sizing caveat.
- **Interpretation (reconciliation report):** RUN A's "every crossing verified
  clean" claim was not supported, and RUN B's blanket NO-GO was not fully
  supported; the two-stage design was a genuine improvement.
- **Limitations:** calibration batches were small (8 to 40 crossings per batch).
- **Decision recorded:** iterate on Candidate D, then freeze the v3 profile for
  the full dataset. The follow-up report says the next iteration "requires your
  approval"; the approval itself is not recorded.
- **Undocumented:** why the specific pulse magnitudes and timings were chosen,
  and which gate decisions were made by the author versus proposed by the
  sessions.
- **Artifacts:** [`outputs/v03_calibration/reconciliation_report.md`](outputs/v03_calibration/reconciliation_report.md),
  [`decision_gate_report.md`](outputs/v03_calibration/decision_gate_report.md),
  [`candidate_d_followup_report.md`](outputs/v03_calibration/candidate_d_followup_report.md),
  [`candidate_d_final_gate_report.md`](outputs/v03_calibration/candidate_d_final_gate_report.md),
  [`PROVENANCE.md`](PROVENANCE.md) §3.

### RL-H04 — v0.3 dataset and temporal model (the frozen primary result)

- **Date:** undocumented. **Status:** complete (frozen).
- **Recorded:** 3,150 trajectories, 5,340,865 rows, with 194 usable crossings
  giving a median physical precursor of **4.38 s**. The temporal RandomForest
  (23 features, 1 s causal window, evaluated once on a held-out trajectory-level
  test split) reached PR-AUC **0.890**, event recall **96.1% (73/76)** and a median
  credited lead time of **4.72 s**.
- **Interpretation:** the 4.38 s precursor is a property of the dataset; the
  4.72 s lead is an event-level model metric. Do not conflate them.
- **Limitations:** per-event lead-time calibration is moderate (Pearson r = 0.337,
  n = 22); the `stall` regime remains an imminent-warning case; event counts are
  small (76).
- **Artifacts:** [`outputs/dataset_audit_v3/v03_generation_report.md`](outputs/dataset_audit_v3/v03_generation_report.md),
  [`outputs/ml_v03/v03_temporal_ml_report.md`](outputs/ml_v03/v03_temporal_ml_report.md),
  [`outputs/final/AEROGUARD_FINAL_RESEARCH_REPORT.md`](outputs/final/AEROGUARD_FINAL_RESEARCH_REPORT.md) §15–16, §20.

### RL-H05 — Zero-exposure regime exclusion

- **Date:** undocumented. **Status:** complete.
- **Recorded:** retraining without the `gradual_approach_v3` regime: PR-AUC 0.552,
  event recall 64.5%, median credited lead 0.73 s (versus 0.890 / 96.1% / 4.72 s).
- **Interpretation (as reported):** multi-second warning does not emerge without
  training exposure to the slow-approach class, so some of the skill could have
  been shape memorization; this motivated RL-H06. The report labels this verdict
  CASE B at that stage.
- **Artifacts:** [`outputs/ml_v03/v03_temporal_ml_report.md`](outputs/ml_v03/v03_temporal_ml_report.md) §11,
  `outputs/ml_v03/metrics/generalization_check.json`.

### RL-H06 — Cross-mechanism transfer and the final decision

- **Date:** undocumented. **Status:** complete (frozen).
- **Question:** is the learned warning specific to Candidate D's two-pulse shape,
  or does it transfer to a structurally different slow-approach mechanism?
- **Recorded:** forward test (frozen v0.3 model, novel single-pulse mechanism,
  46 events): PR-AUC 0.835, recall 100% (46/46), median lead 2.96 s. Reverse test
  (model trained only on the new mechanism, tested on v0.3 gradual approach, 54
  events): PR-AUC 0.708, recall 87.0% (47/54), median lead 5.00 s (horizon cap).
- **Decision recorded:** CASE A — the evidence supports family-level transfer
  across control-input mechanisms within one slow-approach phenomenon.
- **Not established:** universal zero-shot stall prediction, real-aircraft
  behavior, or any independent validation.
- **Artifacts:** [`outputs/ml_v03_generalization/generalization_experiment_report.md`](outputs/ml_v03_generalization/generalization_experiment_report.md),
  final report §17–19.

### RL-H07 — Proposed v0.4 stage (not started)

- **Date:** the proposal appears in the dashboard's "Next Research Stage"
  section, first committed 2026-09-12. **Status:** planned; no experiment run.
- **Proposed question:** does the frozen warning generalize when the simulated
  aircraft parameters change (mass, wing area, aerodynamic coefficients, air
  density, initial airspeed and altitude)? The plan is to train on one aircraft
  family, freeze the model, and test on a different family without refitting.
- **Undocumented:** a written hypothesis, an expected outcome, a configuration
  and seeds. These should be recorded as RL-001 *before* any run.
- **Artifacts:** `dashboard/src/components/sections/FutureWork.tsx`.

### Carried-forward open questions (from the final report §20 and §24)

Transfer to a stall mechanism not driven by elevator timing; better per-event
lead-time calibration; physics beyond 2D/longitudinal and constant density; a
longer precursor for the `stall` regime; and reconciling the duplicate Stage-3 ML
implementation. None has been started.

## 4. Entries

### RL-001 — Reproduction check of the v0.3 pipeline on regenerated data

- **Date:** 2026-10-12 (written after the run, not preregistered).   **Status:** complete
- **Research question:** can the documented v0.3 pipeline be re-run from the
  tracked code and seeds on a clean machine, and does the frozen model then give
  the published TEST results?
- **Motivation and prior evidence:** the data tables are gitignored and the
  historical "190/190 passing" claim could not be reproduced on a clean checkout
  (155 passed, 24 skipped, 11 deselected in CI). See RL-H04.
- **Experiment or investigation:** in a scratch copy of the repository, regenerate
  the v0.2 and v0.3 datasets, rebuild the ML inputs and temporal caches, run the
  full test suite, and score the frozen model on the regenerated v0.3 TEST panel.
  The model was not retrained and no tracked file was modified.
- **Data and configuration:** `generate_dataset_v2.py` (seed 20260817) and
  `generate_dataset_v3.py` (seed 20260823); CPython 3.12.3, Linux x86_64, the
  packages in `requirements-pinned.txt`. Commands and snippet in
  [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md#reproduction-evidence-2026-10-12).
- **Expected outcome:** not stated in advance.
- **Observation or result:** row counts match the documented values (1,753,615
  and 5,340,865). Split manifests, generation configs and feature schemas are
  byte-identical to the tracked files; trajectory metadata and audit JSON agree
  except for float last digits (max relative difference 8.9e-13). `pytest tests/`:
  190 passed, 0 skipped. The frozen model on the regenerated TEST panel: event
  recall 73/76, median lead 4.72 s, 538,034 rows (all equal to published);
  PR-AUC 0.8902774777010881 (equal to published) or 0.8902774777849808 depending
  on the run.
- **Interpretation:** the v0.3 data generation and the frozen model's published
  TEST metrics reproduce on a second machine, to numerical tolerance, with the
  tracked code.
- **Limitations and uncertainty:** the same code and author, so this is not an
  independent replication. The original data files cannot be compared byte for
  byte because no hash of them exists. The model was not retrained, and the
  calibration scripts, v0.1 dataset and generalization stage were not rerun. The
  cause of the PR-AUC last-digit variation was not investigated.
- **Decision and rationale:** keep the frozen artifacts as the reference and
  document the reproduction levels and tolerances (done in `REPRODUCIBILITY.md`).
  Record a hash manifest of the tracked baseline files (`baselines/v0.3.sha256`).
- **Follow-up work:** retrain the temporal model in a scratch copy and compare
  metrics with the frozen model; investigate the PR-AUC variation; consider an
  independent reproduction.
- **Supporting artifacts:** [`baselines/README.md`](baselines/README.md),
  [`baselines/v0.3.sha256`](baselines/v0.3.sha256).

### RL-002 — Audit of splits, temporal features, labels, event metrics and lead time (v0.3)

- **Date:** 2026-10-12 (written after the checks, not preregistered).   **Status:** complete for what could be checked without datasets
- **Research question:** do the v0.3 split, feature, label, event-metric and lead-time code paths do what the paper and reports say, and can any of them leak future information or misstate event-level results?
- **Experiment or investigation:** read-only tracing of `aeroguard_dataset/{splitting,labeling,events,features}.py`, `ml/{temporal_features,temporal_data_v03,temporal_experiment,events,temporal_config*}.py` and `scripts/prepare_ml_dataset.py`; arithmetic on the tracked v0.3 metadata and split manifest; loading the frozen model (read-only); 36 new small tests. No dataset was generated or loaded, nothing was retrained, no frozen artifact changed.
- **Data and configuration:** tracked `data/splits/*.csv`, `data/metadata/*`, the frozen model, `outputs/ml_v03/v03_temporal_ml_report.md`, `tests/test_audit_labels_features_splits.py`, `tests/test_audit_event_metrics.py`. Environment: `requirements-pinned.txt`, CPython 3.12.3.
- **Previously documented facts (not new):** the reports already state the label window `(t, t+5 s]`, trajectory-level splits, causal windows, the lead-time cap at 5 s, and a table of crossings per regime versus crossings usable for ML (final report §14–16, v0.3 report).
- **Observations (checked in this audit):**
  - *Splits.* All three tracked manifests (v0.1, v0.2, v0.3) put every trajectory in exactly one split, cover every trajectory in the metadata, have 70/15/15 sizes (v0.3: 2,205 / 472 / 473), and regenerate **exactly** from the trajectory IDs and the recorded seed with `split_trajectory_ids`. No two v0.3 trajectories share initial conditions. Splitting is a seeded random shuffle, not stratified by regime. The model is a bare RandomForest; there is no scaler, imputer or feature selection fitted on any split, and threshold selection takes only train and validation data.
  - *Features.* The frozen model's 23 inputs equal `model_d_features(1.0)` exactly and include no label, event, time or regime column. All windows are trailing and grouped by trajectory. A new whole-pipeline test perturbs a future sample in every raw channel and finds no change in any of the 23 inputs at earlier rows (a non-causal control is detected).
  - *Labels.* The code matches the written definition: unsafe samples in `(t, t+5 s]`, current sample excluded, rows without a full window unlabeled. New boundary tests pass: exactly at the horizon is positive, one step beyond is not. Rows already inside an unsafe run are labeled positive while a later unsafe sample is within 5 s.
  - *Event metrics.* Event detection sees only the rows that pass the evaluation mask (a label must exist, and a full feature window). From the tracked metadata, 10 of the 67 test crossing trajectories (8 `stall`, 2 `gradual_approach_v3`) have their first crossing in the last 5 s of the trajectory and are therefore excluded from the event population. This matches the report's table (42 and 25 crossings, 40 and 17 usable). The 8 stall cases ended on the flight-path-angle limit 0.07–0.94 s after the crossing. The 76 reported events equal 57 usable trajectories plus 19 re-entry episodes (re-entry count from the report, not recomputed). An excluded event is neither detected nor counted as missed.
  - *Lead time.* An episode qualifies if it starts before the crossing and ends no earlier than crossing minus 5 s (closed comparison); the earliest such start sets min(crossing − start, 5 s). There is no persistence or hysteresis requirement, so a one-sample warning earns full credit and a warning one sample before the crossing counts as a detection with 0.01 s of lead. One long episode can be credited to several events. The median and mean lead times use warned events only; missed events are not given a sentinel value, while event recall counts them.
- **New tests and results:** 36 tests across the two new files, all passing; the CI selection is now 191 passed, 24 skipped, 11 deselected (was 155 passed). No existing test or scientific file was modified.
- **Interpretation:** no code defect and no feature, label or split leakage was found in the paths examined, and the 76-event and 4.72 s figures follow the stated definitions. The main issue is scope, not arithmetic. The headline event recall (96.1%, 73/76) and median credited lead (4.72 s) apply to events with a complete 5 s post-prediction window and, for lead time, to warned events only. Neither the README nor the paper states this, although the v0.3 report's table shows the exclusion. If the 10 excluded first crossings were all missed, recall would be 73/86 = 84.9%; if all warned, 83/86 = 96.5% (bounds from first crossings only, not results). The exclusion falls mostly on the fastest stall departures (8 of 25 stall crossings versus 2 of 42 gradual).
- **Limitations and uncertainty:** no row-level data were loaded, so the share of PR-AUC positives that are already inside an unsafe run, the cause of near-zero-lead detections, and how often brief warnings earn credit are not quantified. The 19 re-entry episodes and the lead-time statistics were not recomputed. Leakage through near-duplicate trajectories is bounded only by the unique initial conditions; trajectories within a regime share a control-profile family by design. The audit checked these code paths and none other.
- **Proposed corrections (none made; need author approval):** (1) state the event population and the "warned events only" condition wherever 96.1% and 4.72 s appear, and give the exclusion counts; (2) add an unconditional companion statistic, such as warning coverage ≥ τ (already in the paper's Table 1) or recall with the excluded events counted; (3) when the data are available, report row-level PR-AUC with post-crossing rows removed and recall with persistence required. No historical result would change; (1) and (2) change wording only, and (3) is a new analysis.
- **Author decisions required:** whether to revise the README and paper wording, and whether to run the additional analyses in (3).
- **Supporting artifacts:** [`tests/test_audit_labels_features_splits.py`](tests/test_audit_labels_features_splits.py), [`tests/test_audit_event_metrics.py`](tests/test_audit_event_metrics.py), `outputs/ml_v03/v03_temporal_ml_report.md`.

### RL-003 — Reporting scope of the headline event metrics

- **Date:** 2026-10-12 (written after the checks).   **Status:** README wording applied; paper amendment drafted, not applied
- **Research question:** which events do the reported 96.1% event recall and 4.72 s median lead time include?
- **Motivation and prior evidence:** RL-002 found that events are scored only within the evaluated rows and that the median lead time is over warned events.
- **Experiment or investigation:** compared the frozen metrics JSON files, the v0.3 report, `ml/events.py` and the tracked trajectory metadata. No data were generated or loaded.
- **Observation or result:** the figures agree across sources. `primary_model_metrics.json`: 76 events, 73 warned, 3 missed, 456 of 473 test trajectories evaluated, and the 73 stored lead times have median 4.72 s, mean 3.42 s, range 0.14–5.0 s, with 29 at the 5 s cap (29/76 = 38.2% equals the stored ≥5 s coverage). `physics_vs_ml_summary.json`: 67 test crossings, 57 evaluated (gradual 42/40, stall 25/17), 54 of the 57 first crossings warned (37/40 and 17/17). The tracked metadata gives 67 crossing trajectories, 57 with the first crossing at least 5 s before the trajectory ends, 10 without, and 17 trajectories with no evaluated rows (473 − 456). By subtraction, all 3 misses are `gradual_approach_v3` first crossings and all 19 second episodes (76 − 57) were warned. The paper mentions 456 test trajectories but not the 473, the 10 outside crossings, or that the median is over warned events.
- **Interpretation:** the headline numbers are correct for the stated definitions but describe only the evaluated events. Pooling 19 second episodes with 57 first crossings may flatter recall slightly (first-crossing recall is 54/57); whether second episodes were credited by a continuing earlier warning is not shown by the stored results.
- **Limitations and uncertainty:** later episodes in the ten excluded trajectories cannot be counted from the metadata. No measured recall exists for the excluded crossings, and none was estimated. The per-regime counts come from the frozen summary, which uses the first model episode per trajectory.
- **Decision and rationale:** state the scope in the README (done) and propose the same in the paper (drafted in `paper/PROPOSED_AMENDMENT_event_metrics_scope.md`), without changing any result or definition.
- **Follow-up work:** author decision on the paper amendment and any republication; the dashboard and `dashboard/public/docs/AEROGUARD_README.md` still show the headline numbers without the scope note; an optional measured analysis of the excluded events would need regenerated data.
- **Supporting artifacts:** [`README.md`](README.md#what-the-event-metrics-cover), [`paper/PROPOSED_AMENDMENT_event_metrics_scope.md`](paper/PROPOSED_AMENDMENT_event_metrics_scope.md), `outputs/ml_v03/metrics/primary_model_metrics.json`, `outputs/ml_v03/metrics/physics_vs_ml_summary.json`.


### RL-004 — Retrospective audit of the v0.3 threshold selection (code and artifacts)

- **Date:** 2026-10-12 (written after the checks, not preregistered).   **Status:** complete for the code path and stored artifacts; historical verification not possible from the repository
- **Kind of entry:** retrospective code and artifact audit. It does not claim preregistration, complete historical verification, or proof that no one ever used test results to inform a decision.
- **Research question:** how was the frozen v0.3 warning threshold selected, can the inspected selector receive test data, and is the threshold applied consistently?
- **Experiment or investigation:** read-only tracing of `ml/calibration.py`, `ml/temporal_experiment.py`, `ml/temporal_experiment_v03.py`, `scripts/run_temporal_experiment_v03.py`, `scripts/run_alt_generalization_experiment.py`, `scripts/analyze_v03_physics_vs_ml.py`, `dashboard/data_export/export_flight_replay.py`, the frozen metrics and config JSON, the tracked v0.2 and v0.3 metadata, and the git history (including a read-only listing of the remote `pre-clean-history-backup` branch). No dataset was generated or loaded and nothing was retrained.
- **Data and configuration:** the threshold is **0.8585534589255494** (reported as 0.8586; the dashboard's 0.8586 is that value rounded to four places). Model: frozen `outputs/ml_v03/models/primary_model_D_1s.joblib` (random forest, 23 features, 1 s window; 200 trees, depth 12, min leaf 5, balanced_subsample, seed 20260817).
- **Procedure inspected (observation from code):** `run_primary_model_v03` calls `fit_rf_and_threshold(Xtr, ytr, Xv, yv, …)`, which fits on train, scores train and validation, and calls `select_threshold_train_then_val`. That function takes the 10 thresholds with the highest TRAIN F1 on the precision-recall curve, scores each on VALIDATION F1, and keeps the best. Only afterwards does `evaluate_on_test(model, thr, …)` apply the fixed threshold to test rows. The TRAIN ranking uses the forest's scores on its own training rows (in-sample), so validation is the only out-of-sample step and it chooses among 10 candidates. In the v0.1 baseline's saved list (`outputs/ml_baseline/model_metrics.json`) those candidates fall in two tight clusters (about 0.8220–0.8222 and 0.8082–0.8084); the v0.3 list is not available (below).
- **Evidence that the inspected selector receives no test data:** the selector and `fit_rf_and_threshold` take only train and validation arguments (`ml/calibration.py:27-31`, `ml/temporal_experiment.py:79`); an existing test asserts that the calibration functions have no test-like parameter (`tests/test_ml_pipeline.py`, `test_calibration_functions_do_not_accept_test_arguments`); in `run_primary_model_v03` the test arrays are built before the fit but are used only after the threshold is returned. The random-forest hyperparameters were chosen on **v0.2 validation** PR-AUC from a two-configuration grid (0.9264 vs 0.9006, `outputs/ml_temporal/metrics/hyperparameter_tuning.json`) and reused unchanged. The v0.2 and v0.3 metadata share no trajectory ID and no identical (airspeed, altitude, alpha) triple (checked on the tracked CSVs, 1,000 vs 3,150 trajectories).
- **Matching stored values:** 0.8585534589255494 appears identically in `outputs/ml_v03/metrics/primary_model_metrics.json`, `outputs/ml_v03/experiment_config.json` (`primary_model_threshold`) and `outputs/ml_v03_generalization/metrics/forward_check_frozen_model_on_alt_mechanism.json`. The forward check and `scripts/analyze_v03_physics_vs_ml.py` read this stored value rather than re-selecting it. The common-subset D_1s ablation model has its own threshold, 0.8585388009091853, from its own train-then-validation fit. The stored confusion matrix is internally consistent (tn+fp = 491,865; tp+fn = 46,169; total 538,034; precision 0.93481; recall 0.73610).
- **Not saved:** the v0.3 candidate thresholds and their validation F1 values. `fit_rf_and_threshold` returns them as `thr_info`, but every v0.3 caller discards it (`ml/temporal_experiment_v03.py:60, 109, 122, 158, 219`), so no v0.3 artifact contains them. From the repository alone it cannot be shown that 0.8585… was the best validation candidate, and the stored threshold was not recomputed (that needs the datasets and a retrain, neither done here).
- **Chronology not established:** the repository's history begins with one snapshot commit on 2026-08-18 (the remote `pre-clean-history-backup` branch is the same lineage, with no earlier commits). Git therefore does not show the order of the threshold, window or model decisions. Code comments call the 1 s primary window "chosen a priori" and the v0.3 settings "pre-registered", but no dated record exists in the repository to check that. The v0.3 run also printed test metrics for the 0.5, 1 and 2 s windows, and the same v0.3 test split was later used for further analyses (generalization checks, physics-vs-ML, the dashboard replay). Those later uses did not re-select the primary threshold, as far as the code shows. The dashboard replay trajectory `traj_00413` was picked after seeing test results, for display only.
- **Row-level F1 versus event-level evaluation:** the threshold optimizes row-level F1 of the `future_stall_5s` label (train ranking, validation choice). It was not tuned for event recall, lead time or false-alarm rate, so the event-level figures (96.1% recall, 4.72 s median credited lead time; see RL-003 for their scope) are consequences of a row-level operating point, not optimized targets.
- **Comparison operators (observation).** The primary evaluation applies the threshold with a strict `>`. Other occurrences:
  - Primary v0.3 evaluation, `>`: `ml/temporal_experiment.py:109` (`evaluate_on_test`, used by the primary model, the ablation, both generalization checks and the alt-mechanism forward check) and `scripts/analyze_v03_physics_vs_ml.py:43` (re-applies the primary predictions for a post-hoc join). These define the published numbers.
  - Selection, `>` on validation: `ml/calibration.py:37`. The train ranking comes from scikit-learn's `precision_recall_curve`, which scores a sample as positive when its score is at least the threshold (documented scikit-learn behavior; scikit-learn was not installed for this check, so it was not re-verified here). So train F1 is ranked with `>=` semantics while validation and test use `>`.
  - Other `>` uses in the same family (v0.1 and baseline code, not the v0.3 headline): `ml/training.py:31`, `ml/ablation.py:46`, `ml/train_baseline.py:131, 181`, `ml/evaluate_baseline.py:58, 110, 185`, `scripts/run_ml_experiment.py:210`, `ml/baselines.py` (the rule baselines, which mix `>`, `<=` and `>=` by rule).
  - `>=`, reporting helper: `ml/metrics.py:40` (`threshold_sweep`, documented as validation-only and fixed-grid; covered by `tests/test_ml_baseline.py`). Not part of the primary evaluation.
  - `>=`, dashboard export: `dashboard/data_export/export_flight_replay.py:71`. It displays one trajectory (`traj_00413`) at 0.1 s resolution after down-sampling and trimming, and reports first-warning time minus crossing time (crossing there is `alpha >= boundary`, not `is_unsafe`), uncapped and without the episode rules, giving 4.7 s. It is an illustration, not a reproduction of the event metrics; the script gives no reason for `>=`, so whether the operator was deliberate is undocumented. In the stored `flightReplay.json`, the probability goes 0.6119, 0.7956, 0.9228 at t = 6.2, 6.3, 6.4 s, so the first warning point is clearly above the threshold and `>` would give the same result. The script was not changed.
  - `>=`, REPRODUCIBILITY.md: the Level 4 snippet used `>=`, and the 2026-10-12 reproduction run (RL-001) used that expression. That was an inconsistency with the primary evaluation. The event metrics (73/76, 4.72 s, 538,034 rows) matched the published values anyway; row-level confusion counts were not compared and PR-AUC does not depend on the threshold.
  - `>=`, unmerged branch: `scripts/analysis_v11_baselines_and_ci.py:102` on `origin/credibility-v1.1` also uses `>=` (listed for reconciliation; not part of this baseline).
- **Disposition of the inconsistency:** `REPRODUCIBILITY.md` was corrected to `>` with a note and with a note on the earlier run. Scientific code, the dashboard export, `flightReplay.json` and all frozen outputs were not changed. The effect of `>` versus `>=` on row-level counts is **unresolved and unmeasured**: the two differ only for scores exactly equal to the threshold, and forest scores are discrete, so such ties are possible. Measuring it needs the regenerated test panel and was not done.
- **Interpretation:** nothing inspected contradicts the stated TRAIN-then-VALIDATION procedure, and the code gives the selector no route to test data. The audit cannot show how the original run was carried out or what anyone saw or decided at the time.
- **Limitations and uncertainty:** no data were loaded; the stored threshold was not recomputed; the saved candidate list is missing; the scikit-learn threshold semantics were taken from its documentation; other repeated uses of the v0.3 test split mean it is not a one-look holdout. Only the paths named above were examined.
- **Decision and rationale:** accept the code-path audit; keep the missing-record limitation visible; do not claim historical verification. Correct the documentation operator only.
- **Follow-up work (author decisions):** whether to save the candidate list in future runs; whether to measure the `>` versus `>=` effect and to retrain with the fixed seed in a storage-gated scratch run to see whether the same threshold results; whether the dashboard export should be aligned or its operator documented; item 26 not started.
- **Supporting artifacts:** `ml/calibration.py`, `ml/temporal_experiment.py`, `ml/temporal_experiment_v03.py`, `outputs/ml_v03/metrics/primary_model_metrics.json`, `outputs/ml_v03/experiment_config.json`, `outputs/ml_v03_generalization/metrics/forward_check_frozen_model_on_alt_mechanism.json`, `outputs/ml_temporal/metrics/hyperparameter_tuning.json`, [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md).

### RL-005 — Recomputation of the v0.3 metrics from stored artifacts (roadmap Item 26, partial)

- **Date:** the audit ran on 2026-10-12 and this entry was written on 2026-10-13, after the checks (not preregistered).   **Status:** partial; stronger reproduction is blocked on unavailable data
- **Kind of entry:** retrospective recomputation from stored artifacts. It does **not** claim that the original predictions, PR-AUC, ROC-AUC or row-level counts were independently reproduced.
- **Levels used in this entry:** (1) *arithmetic verification*: recomputing ratios and totals from stored metric components. (2) *Metadata reconstruction*: recomputing populations from the tracked metadata and split manifest. (3) *Record-level recomputation*: recomputing statistics from stored per-crossing records and the stored list of 73 lead times. (4) *Prediction-level recomputation*: recomputing metrics from row scores and labels; **not done**. (5) *Full evaluation reproduction*: regenerating the data, scoring the frozen model and comparing; **not done in this audit** (the 2026-10-12 run in RL-001 is a separate, earlier check with the limits stated there).
- **Inputs actually available:** the frozen model (not loaded; scikit-learn and joblib were not installed in that interpreter), `outputs/ml_v03/metrics/*`, `outputs/ml_v03/experiment_config.json`, `dashboard/src/data/metrics.json` and `flightReplay.json`, `data/metadata/trajectory_metadata_v3.csv`, `data/splits/split_manifest_v3.csv`. **Not available:** the datasets and feature panels, row-level scores or predictions, row-level labels, and per-episode event records. No such arrays were ever saved in the repository.
- **Observations (level 1, arithmetic, from stored components):** 101 checks were run and 98 matched with zero difference (tolerance 1e-15 for ratios, 1e-12 for derived rates). They cover: confusion-matrix totals (538,034 rows, 46,169 positives, 491,865 negatives); precision, row recall, F1, accuracy and row false-positive rate from tn/fp/fn/tp; the six lead-time bucket recalls; the false-alarm file (36,355 warned rows equal tp+fp; 121 episodes = 93 + 28; episode precision, per-trajectory and per-minute rates); event recall 73/76; median, mean, population standard deviation, minimum and maximum of the 73 stored lead times; the 29 leads at the 5 s cap; the six coverage fractions (70, 55, 49, 45, 42, 29 of 76); the dashboard's 4-decimal values; and the regime and airspeed tables (row, positive and true-positive sums). The 3 differing checks are the bucket totals below. These checks use the stored lead times and counts as given, so they verify the arithmetic and internal consistency of the stored values, not the model's predictions.
- **Observations (level 2, metadata reconstruction):** `sum(max(0, n_steps − 600))` over each split reproduces the reported evaluated rows exactly: train 2,443,881, validation 491,322, test 538,034 (600 = the 500-step label horizon plus the first 100 rows without a full 1 s window), and 456 of 473 test trajectories with at least one evaluated row. The tracked metadata also give 67 test crossing trajectories (42 `gradual_approach_v3`, 25 `stall`), 57 with the first crossing inside the evaluated rows (40 and 17), and 10 whose first crossing falls in the last 5 s (2 and 8; none before row 100); 6 of those 10 have no evaluated rows. This used only the tracked metadata and no model.
- **Observations (level 3, record-level):** `physics_vs_ml_lead_time.csv` (67 first-crossing records) gives 57 usable, 54 warned (37 of 40 gradual, 17 of 17 stall); its usable flag matches the metadata reconstruction for all 67 trajectories; its 20 per-regime summary statistics recompute from it within 4e-16; and each of its 54 warned lead times is found in the stored list of 73. That leaves 19 lead times, which by count (76 − 57 = 19 events, 73 − 54 = 19 warned) correspond to the second episodes; they are identified by subtraction, not from per-episode records.
- **Not recomputable from the available artifacts:** PR-AUC (0.8902774777010881) and ROC-AUC (0.9775387048062552), which need the full score distribution; the row-level confusion matrix under the strict threshold; the bucket row counts; the event list itself (the 73 stored lead times were taken as given); calibration; and everything about the second episodes beyond their lead times. Nothing in this list was checked, and none of it should be read as having passed.
- **Discrepancy — five positive rows:** the six lead-time buckets sum to 46,164 positive rows, 33,982 warned and 12,182 missed, against 46,169, 33,985 and 12,184 in the confusion matrix, a gap of 5 positive rows (3 warned, 2 missed; 0.011% of positive rows). The false-alarm file agrees with the gap: its `>5s_or_no_future_crossing` bucket holds 2,373 warned rows, which is the 2,370 false positives plus those 3. So five positive rows have a `time_to_stall` outside every bucket `(lo, hi]` over `(0, 5]`. **Suspected explanation, unverified:** `time_to_stall` is computed as a difference of two floating-point times, so a value such as 5.000000000000001 s could fall outside `(4, 5]` while the integer-step label includes the row. This was not checked, because it needs the row-level `time_to_stall` values. No historical explanation is claimed. The gap does not change any stored headline metric.
- **Pooled median versus first-crossing median (derived from stored records; not independently reproduced model output):** the headline median credited lead time of 4.72 s pools 54 first crossings and 19 second episodes. Recomputed from the stored records, the 54 warned first crossings have median **3.15 s** (mean 2.94 s), whereas the 19 second episodes, all warned, have median 5.00 s (mean 4.79 s), with 16 of them at the 5 s cap. The first-crossing figure of 3.15 s is not a published number; it is derived here. First-crossing recall is 54/57 = 94.7% against 96.1% pooled, and coverage at least 3 s is 27/57 = 47.4% for first crossings against 59.2% pooled (at least 5 s: 22.8% against 38.2%; at least 1 s: 63.2% against 72.4%). The group counts add up to the stored pooled counts at every threshold.

  | | First crossings | Second episodes | Pooled |
  |---|---|---|---|
  | Events | 57 | 19 | 76 |
  | Warned | 54 (94.7%) | 19 (100%) | 73 (96.1%) |
  | Median lead, warned (s) | 3.15 | 5.00 | 4.72 |
  | Mean lead, warned (s) | 2.94 | 4.79 | 3.42 |
  | Coverage ≥ 3 s | 27/57 | 18/19 | 45/76 |
  | Coverage ≥ 5 s | 13/57 | 16/19 | 29/76 |

  **Influence of second episodes:** adding 19 mostly capped values to the 54 first-crossing values raises the pooled median from 3.15 s to 4.72 s. The pooled figure is correct under its stated definition (RL-002, RL-003) and is left unchanged here. Why the second episodes have long credited leads is not shown by the stored results; a continuing earlier warning being credited to a later event (RL-002) is one possibility, and it has not been tested.
- **Threshold operator:** the original v0.3 evaluation uses the strict `proba > threshold` (RL-004). The 2026-10-12 reproduction (RL-001) applied `>=`. Its matching event metrics are therefore **not** evidence that row-level predictions are identical between the two operators, and the effect of `>` versus `>=` on row-level counts is still unmeasured. Nothing in this audit applied a threshold to scores, so it does not settle that question either.
- **Interpretation:** every stored value that could be tested from the stored components and the tracked metadata is internally consistent, and the evaluated population is independently reconstructed. That supports the *arithmetic and population* of the reported numbers. It does not support a claim that the model's predictions were reproduced.
- **Limitations and uncertainty:** no predictions, labels or datasets were available; the stored lead-time list and per-crossing records were taken as given; the 19 second-episode leads are identified by subtraction; the floating-point explanation is a hypothesis; the dashboard replay trajectory is a single illustrative case and was used only as a consistency check on one episode start.
- **Decision and rationale:** Item 26 stays **partial**. Keep the pooled headline metric unchanged. Do not describe the audit as a reproduction.
- **Missing prerequisites for stronger reproduction:** the regenerated v0.3 test panel (and its `time_to_stall` and `is_unsafe` columns); the frozen model run in an environment with scikit-learn 1.9.0 and joblib; a small scoring script, not currently in the repository, that writes row scores, labels and event records to a scratch directory and applies both `>` and `>=`; and, only for the historical threshold record, the regenerated train and validation panels and a retrain. The original score arrays do not exist, so even full regeneration reproduces the pipeline on regenerated data, not the original run's arrays (see the limits in RL-001).

#### RL-005 addendum A — Reporting implications (recommendation, not applied)

- **Recommendation:** add a first-crossing breakdown to future reporting (README, dashboard and, if the author agrees, the paper amendment proposal), **alongside** the pooled metric and not instead of it. Keep 96.1% and 4.72 s exactly as they are, labelled as pooled over 76 evaluated events.
- **Why it helps readers:** a reader seeing "median 4.72 s" is likely to take it as the typical first warning before a stall. The stored records show it is pulled up by 19 second episodes, 16 of them at the 5 s cap, and that the first-crossing median is 3.15 s with 94.7% recall. The breakdown shows both numbers and lets readers judge which question matters to them. Coverage at least 3 s and at least 5 s show the same effect.
- **Conditions on its use:** it must be labelled as derived from stored per-crossing records and the stored lead-time list, not as independently reproduced model output, and not as a new result of the model. Report the sample sizes (57 and 19), because small groups make the medians unstable. State that the second-episode leads are identified by subtraction and that why they are long has not been tested. The recommendation changes wording and presentation only, and no definition or stored value.
- **Not done:** `README.md`, the dashboard, the paper, its HTML copies and PDFs, and `paper/PROPOSED_AMENDMENT_event_metrics_scope.md` were not edited. Whether to adopt this is the author's decision.

#### RL-005 addendum B — Reproduction feasibility (analysis only; nothing was run)

- **Rule for all three operations:** run in a scratch copy of the repository (the method in `REPRODUCIBILITY.md`), never in the working checkout. `scripts/generate_dataset_v3.py` and `scripts/run_temporal_experiment_v03.py` write to tracked paths (`data/metadata/*_v3*`, `data/splits/split_manifest_v3.csv`, `outputs/dataset_audit_v3/`, `outputs/ml_v03/`) and would overwrite frozen files. Environment: `requirements-pinned.txt` (CPython 3.12). Pinned virtual environments with scikit-learn 1.9.0 and joblib 1.6.0, and CPython 3.12.3, exist in this session's scratch directory (`vpin`, `v312`); they are session-local and may not persist.
- **Operation 1 — panel generation.** Inputs: tracked code, `data/metadata/generation_config_v3.json` and seed 20260823. Commands: `python scripts/generate_dataset_v3.py` (writes `data/raw/raw_telemetry_v3.parquet`, `data/processed/processed_dataset_v3.parquet`, the metadata, manifest, config, schema, audit report and plots; recorded run time about 520 s on 2026-10-12), then `load_temporal_splits(force=False)` from `ml/temporal_data_v03.py`, which reads the full processed table and builds and caches all three panels (`data/ml_temporal_v03/temporal_{train,val,test}.parquet`; there is no test-only option without a code change). Check afterwards that the regenerated manifest and config are byte-identical to the tracked files (as on 2026-10-12). No model is involved.
- **Operation 2 — frozen-model scoring.** Inputs: the test panel; `outputs/ml_v03/models/primary_model_D_1s.joblib` (SHA-256 `707d4c61…`); the threshold and `feature_columns` in `primary_model_metrics.json`; the mask `usable_mask_for_window(test, 1.0)`; `get_xy`. The pipeline's own scoring call is `evaluate_on_test(model, thr, X, y, sub)` (`ml/temporal_experiment.py`), which applies the strict `>`. The snippet in `REPRODUCIBILITY.md` prints only four numbers and does not save scores. A new scratch-only script would need to be written and approved: it would save scores and labels, evaluate both `>` and `>=`, and compute the confusion matrix, buckets, PR-AUC/ROC-AUC, events and coverage. No retraining.
- **Operation 3 — full retraining.** Commands: `python scripts/run_temporal_experiment_v03.py` (all stages; original recorded run time 1,324.8 s, about 22 minutes; overwrites `outputs/ml_v03/` unless run in the scratch copy). It produces a new model, a new threshold and new metrics, which are new artifacts and not the frozen model. `thr_info` (the candidate list and validation F1 values) is discarded by the v0.3 callers, so recovering a candidate list would need a small scratch script that calls `fit_rf_and_threshold` and keeps what it returns, without editing the frozen code. Even a matching threshold would not show what the original run did.
- **Disk space — evidence only:** the tracked-file copy is about 77 MB (measured now, excluding `.git`, `dashboard/node_modules` and `dashboard/dist`). During the 2026-10-12 run, `du -sh` on the scratch copy's `data/` directory gave **3.5 GB**, after regenerating v0.2 and v0.3 and building the ML tables and temporal caches (the listing shown included the processed v0.2 and v0.3 parquet files and the three v0.3 panels; per-file sizes were not recorded). `.gitignore` states about 3.6 GB for the original v1/v2/v3 data. No defensible figure exists for v0.3 alone, so none is given. Memory use and the cache-build time were not recorded. This entry makes no statement about how much storage the author has.
- **What each operation could resolve:**
  - *Panel only (1):* the 5-row bucket gap (positive rows whose `time_to_stall` is outside `(0, 5]`, which would test the float-boundary hypothesis); later episodes in the 10 excluded trajectories (runs of `is_unsafe` in the last 5 s); row-level label counts (n_positive).
  - *Panel plus scoring (1 + 2):* PR-AUC and ROC-AUC; the confusion matrix under the strict `>` and under `>=` (the operator question); the bucket warned/missed split of the 5 rows; the full event list, so second-episode crossing times and whether their credit comes from a continuing earlier warning; first-crossing versus pooled results from predictions instead of stored records.
  - *Retraining (1 + 3):* only the saved-candidate-list limitation from RL-004 (whether a fixed-seed retrain gives threshold 0.8585534589255494), and only as a consistency check.
- **Limit that remains after every operation:** the original score arrays are not available. Regenerated trajectories agreed with the tracked ones to about 1e-12 and PR-AUC varied at the 1e-10 level between runs (RL-001), so scoring regenerated data demonstrates the pipeline on regenerated data and cannot show what the original run predicted. A `>` versus `>=` comparison would likewise describe the regenerated data.
- **Follow-up (author decisions):** whether to approve a scratch-only run of operations 1 and 2 and a storage plan for it; whether to approve the new scoring script; whether to adopt the reporting recommendation; item 27 not started.

### RL-006 — Reproduction of the frozen-model v0.3 evaluation on regenerated data (roadmap Item 26 closure)

- **Date:** 2026-10-13. **Status:** planned (this block was written **before** any data were generated or scored; results are appended below under *Results*, and this planned text is not to be edited afterwards).
- **Kind of entry:** a reproduction check on **regenerated data** by the same code and author on a different machine state. It is **not** an independent replication, and it cannot show that the original predictions were bit-for-bit identical, because the original score arrays were never saved (RL-004, RL-005).
- **Questions:** (1) Does regenerating v0.3 from the tracked code and seed give the documented dataset and evaluation population? (2) Does scoring the unchanged frozen model with the strict `proba > threshold` give the stored confusion counts, PR-AUC, ROC-AUC and event metrics? (3) Do any scores equal the threshold exactly, and does `>=` change any row-level prediction? (4) What are the five positive rows missing from the lead-time buckets? (5) What does the full event list show about first-crossing versus second-episode attribution and about one long warning being credited to several events?
- **Method (fixed in advance):**
  1. Scratch copy outside the repository from `git archive HEAD` (code, tracked metadata and split manifests, `outputs/ml_v03`). The real working tree is never an input and is never written to.
  2. Preflight assertions before any generation: `ml` and `aeroguard_dataset.paths.PROJECT_ROOT` resolve inside the scratch copy; no editable installation; the scratch frozen model has SHA-256 `707d4c61a791af940549f81520a0c8429edaa8ef8d67eb0f02c3174c5fe603f3`; dependency versions recorded; free space at least 4 GB on the scratch filesystem (a conservative operational margin, not a measured minimum).
  3. Generation by a scratch-only wrapper that imports the unchanged generator constants and `build_dataset_v3` and writes only `data/processed/processed_dataset_v3.parquet`. It will be inspected before running. If it cannot reproduce the dataset, the run stops and the unchanged `generate_dataset_v3.py` is not substituted without being recorded as a deviation.
  4. Panels built with the unchanged `ml.temporal_data_v03.load_temporal_splits`.
  5. Scoring by a scratch-only script that loads the frozen model and the stored threshold (0.8585534589255494), uses the existing `get_xy` and `usable_mask_for_window`, and applies strict `>`. No retraining, no threshold selection or sweep. Scores are computed with `n_jobs=1` and with the saved `n_jobs=-1` setting (three runs) to measure scoring variation, because scikit-learn accumulates tree outputs in thread-completion order when `n_jobs>1`.
  6. Outputs only in a scratch output directory. The stored metric files are read, never overwritten.
- **Acceptance gates (preregistered):**
  - *A. Dataset:* 5,340,865 rows; 3,150 trajectories; the regenerated split manifest identical to the tracked `split_manifest_v3.csv`; regenerated metadata equal to the tracked metadata within 1e-12 where numeric (non-numeric columns exactly).
  - *B. Panels:* train 3,749,572 rows, validation 771,995, test 819,298 (counts from the `credibility-v1.1` run log); usable test rows for the 1.0 s window 538,034; usable test positives 46,169; negatives 491,865.
  - *C. Metrics:* confusion counts exactly equal to the stored tn/fp/fn/tp (489,495 / 2,370 / 12,184 / 33,985); PR-AUC and ROC-AUC within 1e-9 of 0.8902774777010881 and 0.9775387048062552; event counts (76 events, 73 warned, 3 missed), the number of leads at the 5 s cap (29) and the six coverage counts exactly equal; the 73 lead times, median, mean and standard deviation within 1e-9; false-alarm episode counts exactly equal (121, 93, 28), derived rates within 1e-9; regime and airspeed table counts exactly equal, derived values within 1e-9. The first-crossing/second-episode decomposition is reported and compared with RL-005 (54 of 57 first crossings warned; 19 of 19 second episodes warned; first-crossing median 3.15 s; second-episode median 5.00 s).
  - Tolerances are **not** to be relaxed after seeing results. Any failed gate is documented as failed.
- **Operator and five-row questions (procedure fixed in advance):** count rows with `score == threshold` first. If zero, `>` and `>=` give identical predictions on the regenerated scores and no second metric set is needed. If above zero, report exactly which rows change and recompute the affected metrics under `>=` in scratch only. For the five rows, list the positive rows whose `time_to_stall` lies outside every bucket `(lo, hi]` over `(0, 5]`, with exact values. The floating-point explanation counts as supported only if those rows' `time_to_stall` exceed an upper bucket edge by a floating-point amount while the integer-step label includes them; otherwise it stays unverified.
- **Outcome rule (fixed in advance):** *A, check passed*: every gate above passes. *B, partially passed*: the dataset or some metrics reproduce, but specific gates fail or questions stay unresolved. *C, blocked*: a documented environment, storage, dependency or integrity constraint prevents a safe run. *D, failed*: the run completes but differences or failed gates remain unexplained. Passing the gates means agreement on regenerated data only.
- **Not authorised or done:** retraining, threshold selection, any change to the frozen model, scientific code, stored metrics, paper, PDF or Zenodo record, and any commit or push.

#### RL-006 results (appended 2026-10-13 after the run; the planned text above is unchanged)

- **Status:** complete. **Outcome: A, reproduction check passed** (every preregistered gate passed and every comparable metric matched within the preregistered tolerance), **on regenerated data only**. This is the same code and author, so it is not an independent replication. It does not show that the original predictions were bit-for-bit identical, because the original score arrays were never saved. The audit (Item 26) is complete; the historical items listed under *Not answerable* remain open.
- **Environment (scratch copy built from `git archive HEAD`, outside the repository):** CPython 3.12.3; scikit-learn 1.9.0; joblib 1.6.0; numpy 2.5.4; pandas 3.0.6; pyarrow 26.0.0; scipy 1.18.1; no editable installs; `ml` and `aeroguard_dataset.paths.PROJECT_ROOT` resolved inside the scratch copy. Frozen model SHA-256 `707d4c61a791af940549f81520a0c8429edaa8ef8d67eb0f02c3174c5fe603f3` before and after the run. Scientific directories in scratch were identical to the working tree (`diff -r`). The real repository was never written to by the run.
- **Steps executed:** (1) a scratch-only wrapper `gen_v3_min.py` (reuses the unchanged `generate_dataset_v3.py` constants and `build_dataset_v3`; writes only `data/processed/processed_dataset_v3.parquet`; compares metadata and manifest in memory) — 465.7 s, peak 2.5 GB RAM; (2) the unchanged `ml.temporal_data_v03.load_temporal_splits` — 95.1 s, peak 5.5 GB RAM; (3) `gate_B.py`; (4) `score_v03.py`, which scores the frozen model with the stored threshold 0.8585534589255494 from `experiment_config.json` and the repository's own `evaluate_on_test` (strict `>`), four times (three with the saved `n_jobs=-1`, one with `n_jobs=1` set on the in-memory object only); (5) `compare_v03.py` and `extra_checks.py`. No retraining, no threshold selection, no sweep.
- **Gate A (dataset): passed.** 5,340,865 rows; 3,150 trajectories; split manifest text-identical to the tracked file; metadata equal to the tracked file with a maximum relative difference of 8.93e-13 (maximum absolute 4.55e-13, column `minimum_alpha`), no non-matching column. The tolerance was applied as a relative difference, the form measured on 2026-10-12.
- **Gate B (panels): passed.** Train 3,749,572, validation 771,995, test 819,298 rows (52 columns each); usable test rows 538,034 with 46,169 positives and 491,865 negatives; 456 of 473 test trajectories have usable rows.
- **Gate C (metrics): passed in all four variants.** 444 gate-C comparisons, 0 differences. Including the dashboard export and the RL-003/RL-005 cross-checks, 514 comparisons: 512 exact, 2 within tolerance, 0 differing. Confusion matrix tn/fp/fn/tp = 489,495 / 2,370 / 12,184 / 33,985 in every variant. ROC-AUC 0.9775387048062552 exactly in every variant. PR-AUC 0.8902774777010881 (equal to the stored value) in three variants and 0.8902774777849808 in saved-setting run 1 (difference 8.39e-11, within 1e-9). Events: 76 events, 73 warned, 3 missed, 29 leads at the 5 s cap, the six coverage counts (70, 55, 49, 45, 42, 29 of 76), the 73 lead times, false-alarm episodes (121, 93, 28), and the regime, airspeed, bucket and dashboard values all matched (exact in every case). The 67 stored first-crossing records matched the regenerated first events in usable flag, warned flag, crossing time and lead time.
- **Scoring variation (observation):** scores from different runs differ in the last bits: 28,328 to 50,320 rows differ from run 1 (maximum absolute difference 4.4e-16), and run 1 has 132,489 distinct scores against 132,490 in the other three. This matches the PR-AUC change in run 1 only. The cause is not proven; reading scikit-learn's code, forest `predict_proba` with `n_jobs>1` adds tree outputs in thread-completion order, which is a plausible mechanism, but `n_jobs=1` also differed from run 1 at the last bit, so the mechanism is untested. Row-level predictions were identical in all four variants.
- **Strict `>` versus `>=`:** exact score ties at the threshold: **0** in every variant; the nearest scores are 0.85848739223472 (below) and 0.858583256634222 (above), 2.98e-5 from the threshold. Rows where `>` and `>=` differ: **0**. On the regenerated scores the two operators give identical row-level predictions, so no second metric set was needed. This says nothing about the original score arrays beyond the fact that the stored confusion matrix is reproduced exactly under the strict `>`. The 2026-10-12 `>=` run (RL-001) is therefore consistent with this result, but it is not by itself evidence of row-level equality.
- **Five-row bucket discrepancy: resolved on the regenerated data.** Exactly five positive rows (`future_stall_5s = 1`, `is_unsafe = False`) have `time_to_stall = 5.000000000000001` s (5 + 8.88e-16): `traj_00824` at 3.29 s, `traj_01165` at 4.55 s, `traj_02121` at 4.63 s, `traj_02187` at 3.37 s, `traj_02891` at 5.70 s. They are labelled positive by the integer-step label but fall outside the bucket `(4, 5]`. Three are warned (scores 0.9669, 0.9402, 0.9098) and two are missed (0.4087, 0.7748), the same 3/2 split as in the stored files. `time_to_stall` is computed as a difference of floating-point times in `scripts/prepare_ml_dataset.py`, which fits this. This met the preregistered criterion for the explanation to count as supported. It is shown on regenerated data, not on the original arrays.
- **Events and attribution (derived from regenerated evaluation records):** 76 events = 57 first events (54 warned, 3 missed: `traj_00314`, `traj_00593`, `traj_02024`, all `gradual_approach_v3`) + 19 later events (all warned). First events: median lead 3.15 s, 13 at the 5 s cap, recall 54/57. Later events: median 5.00 s, 16 at the cap. Pooled median 4.72 s. These match RL-005. **16 of the 19 later events are credited to the same warning episode as the first event of their trajectory** (16 episodes each credited to two events, none to more than two); of the 16 capped later events, 14 share that episode and 2 come from a different episode; 2 events share an episode without being capped (4.98 s and 3.27 s); the remaining later event (`traj_00593`) follows a missed first event.
- **Events outside the evaluated rows (regenerated data):** 90 unsafe runs in 67 trajectories; 76 have evaluated rows (these are the events); 14 do not: the 10 first runs excluded by the five-second boundary (8 `stall`, 2 `gradual_approach_v3`) and 4 later runs (all `stall`, in trajectories whose first run was evaluated; they start 0.41 to 2.58 s before the end). **None of the ten excluded-first-crossing trajectories has any further unsafe run.** This answers the question RL-003 left open ("how many later episodes are outside the rows") on the regenerated data only.
- **Deviations and judgements, stated plainly:** (a) the minimal wrapper was used in place of the unchanged `generate_dataset_v3.py`, as planned; it also skipped the raw parquet, audit and plots; (b) the metadata tolerance was applied as a relative difference; (c) the comparison of the stored RL-005 figures (3.15 s and 5.00 s, stored to two decimals) used a tolerance of 0.005, fixed in the comparison script before it was run; (d) all four scoring variants were evaluated and a gate counted as passed only if it passed in every variant; no variant was designated primary in advance; (e) `extra_checks.py` was written after the main scores were seen and is diagnostic, not a gate; (f) the comparison script read `dashboard/src/data/metrics.json` from the real repository, read-only. No tolerance was changed after seeing results.
- **Not answerable (unchanged):** whether the original run's scores were bit-for-bit identical; the original v0.3 threshold candidate list and validation F1 values (RL-004); the historical chronology of decisions; independent replication.
- **Recommendations (not applied):** (1) the README sentence "the available metadata does not establish how many such episodes there are" can be replaced by the regenerated-data count (none in the ten excluded trajectories; four later episodes elsewhere), labelled as measured on regenerated data; (2) report the first-event versus later-event breakdown with the pooled metric, as recommended in RL-005; (3) compare PR-AUC with a tolerance, and consider recording scores and the threshold candidate list in future runs; (4) update the Level 4 evidence in `REPRODUCIBILITY.md` with the strict-`>` result. None of this changes a stored metric; the paper, PDFs and dashboard figures were not touched.
- **Scratch-only artifacts:** under the session scratch directory `item26x/`: `aeroguard-eval/` (code copy, regenerated data, panels, `audit_out/` with `comparison.csv`, `comparison.json`, `REPORT.md`, scores, event lists) and `tools/` (five scripts: `gen_v3_min.py` 0e0c8303…, `gate_B.py` 98fec555…, `score_v03.py` 6a0b4113…, `compare_v03.py` 164d3bb0…, `extra_checks.py` fd8258de…). Measured disk use of `item26x/`: 2.1 GB (processed v3 parquet 449,345,877 bytes; panels: train 1,188,953,925, validation 246,442,707, test 261,347,990 bytes).

### RL-007 — Consolidated reproducibility report (roadmap Item 27)

- **Date:** 2026-10-13 (written after the checks; not preregistered).   **Status:** complete (documentation only)
- **Purpose:** consolidate the verified v0.3 evidence (RL-001 to RL-006) into one self-contained report that separates the historical v0.3 evaluation (A), the Item 26 reproduction on regenerated data (B) and independent replication (C, not done). No experiment, dataset generation, scoring, retraining or threshold selection was run for this item, and no result, definition or stored artifact was changed.
- **Files changed:** new [`REPRODUCIBILITY_REPORT.md`](REPRODUCIBILITY_REPORT.md) (16 sections and three appendices: claim-to-evidence summary, older documents carrying less-qualified statements, Item 26 scratch tooling); this entry; a concise *Unreleased* entry in [`CHANGELOG.md`](CHANGELOG.md) plus a clarification that the "no dataset generation was re-run" sentence refers to the repository (reproduction checks ran in scratch copies); one-sentence links to the report in [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) and [`README.md`](README.md). The public README copy under `dashboard/public/docs/` was not given the link.
- **Sources inspected:** RL-001 to RL-006; `README.md`, `REPRODUCIBILITY.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `CITATION.cff`, `baselines/README.md`; the stored v0.3 metric files, configuration, split manifest and metadata; `scripts/generate_dataset_v3.py`, `aeroguard_dataset/{labeling,splitting,events,dataset_builder_v3}.py`, `ml/{calibration,events,temporal_features,temporal_data_v03,temporal_experiment,temporal_experiment_v03,temporal_config,temporal_config_v03}.py`, `scripts/prepare_ml_dataset.py`; and, while it still existed, the Item 26 scratch outputs (read-only).
- **Verification performed:**
  1. 67 numeric and text cross-checks of stored artifacts, tracked metadata, `requirements-pinned.txt` and the RL-006 text against the figures to be cited (67 of 67 consistent); the Item 26 scratch outputs matched the RL-006 text in every compared figure.
  2. 44 report literals (metrics, bucket table, event table, regime slices, shared-episode and unsafe-run counts, score-variation counts, the five-row table) matched values recomputed from the artifacts (44 of 44).
  3. Every repository path and link in the report resolves, apart from the five scratch script names in Appendix C, which are intentionally not repository files, and three bare file names in one sentence that gives their directory.
  4. The 36 audit tests passed (`tests/test_audit_labels_features_splits.py`, `tests/test_audit_event_metrics.py`), run with bytecode and cache writing disabled; no new ignored files appeared.
  5. The report has balanced code fences, consistent table columns and no trailing whitespace; no Markdown linter is installed, and none was installed. A search of the report found no statement claiming independent replication, bit-for-bit identity with the original predictions, real-aircraft validity or certification.
  6. The AI-assistance and authorship text was compared with the README sections and keeps them: the research idea is the author's; Claude Code assisted with building and implementing the project; the record does not show which individual decisions were made with its help.
- **Results:** every figure in the report agrees with its source. The report's verdict is: *the v0.3 frozen-model evaluation was reproduced on regenerated data; the preregistered dataset, panel and metric gates passed; the saved confusion matrix and ROC-AUC matched exactly and PR-AUC within the preregistered tolerance; this check does not establish bit-for-bit identity with the original predictions or constitute independent replication.*
- **Limitations that remain:** no original score arrays; no original threshold candidate list or validation F1 values; no historical chronology; no independent replication; incomplete original environment record; shared warning episodes and the pooled-versus-first-event distinction; ten excluded first crossings; simulation-only scope. The Item 26 scratch tooling is temporary and no committed script reproduces the full scoring.
- **Deviations and judgements:** the report adds two small explanatory notes beyond RL-006 (the 16 shared episodes as the dominant pattern behind long later-event leads, and the statement that the corrected `REPRODUCIBILITY.md` snippet has not itself been executed); both are labelled as observation or limitation.
- **Deferred recommendations (not applied; need the author's decision):** update the README, dashboard text and `REPRODUCIBILITY.md` Level 4 evidence with the Item 26 findings; adopt the first-event versus pooled presentation; add a small reviewed scoring script to the repository; consider recording scores and the threshold candidate list in future runs; apply or drop `paper/PROPOSED_AMENDMENT_event_metrics_scope.md`; rebuild the PDF and publish a new Zenodo version for the repository URL. None of these was done.
- **Exact final verdict for Item 27: COMPLETE.** Integrity check after all edits: 79 of 79 baseline hashes pass; the frozen model SHA-256 is unchanged; the stored metric files, experiment config, split manifest, metadata, `dashboard/src/data/metrics.json`, `dashboard/src/data/flightReplay.json`, the scientific code, the tests, the paper PDFs and the other tracked research artifacts show no change against `HEAD`; the paper source and its two HTML copies carry only the one-line repository-URL fix from Item 1. Compared with the fingerprint taken before Item 27, the only files that differ are `REPRODUCIBILITY_REPORT.md` (new), `RESEARCH_LOG.md`, `CHANGELOG.md`, `REPRODUCIBILITY.md` and `README.md`. Nothing is staged; nothing has been committed, pushed, tagged, deployed or published; Item 28 has not been started. The accumulated work remains uncommitted.
