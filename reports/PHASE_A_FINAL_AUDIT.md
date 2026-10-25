# Phase A — Scientific Audit and Evidence Closure (Phase 4, Items 43–53)

| | |
|---|---|
| **Date** | 2026-10-24 |
| **Scope** | The Phase 4 generalisation study (`outputs/phase4/run_20261015T152932Z/`) and every active document that reports it. Earlier phases are covered only where Phase 4 reuses their code. |
| **Method** | Reading code, stored outputs and Git history; read-only cross-checks of stored aggregates; the repository's own website parity check and Phase 4 unit tests; small synthetic checks of metric code. Extra packages, scratch copies and synthetic checks lived outside the repository; checks run from the repository root wrote nothing to it (bytecode and pytest caches disabled). No experiment, training run, dataset generation or threshold selection was done. |
| **Branch** | `claude/gallant-babbage-m4l0wa`. Changes are uncommitted working-tree edits; nothing was committed, pushed, tagged or published. |
| **Earlier passes** | Pass 1 and Pass 2 of this audit, given in conversation and not saved to the repository. This report supersedes them. |

## 1. Executive summary

- **Traceability.** Every Phase 4 number on the website and in the README matches the stored aggregate outputs. The repository's parity check passes 176 of 176. Example: SEEN PR-AUC 0.8800 and median lead 2.345 s in `primary.json`.
- **Correct code is not a reproduced result.**
  - The metric code works as documented. Its custom weighted average precision matches scikit-learn to about 2e-16.
  - The 23-configuration design and its unfamiliarity table regenerate exactly from the committed code.
  - However, **no Phase 4 metric can be recomputed from data.** The datasets, per-trajectory metadata, fitted models and score arrays were never archived, and none was found in any accessible location (§2).
- **Five issues.**
  - **A (in-stall rows in PR-AUC):** confirmed from code. The size of the effect is unknown.
  - **B (event population):** confirmed from code and stored counts. About a quarter of counted events are repeat crossings. Stalls followed by less than 5 s of trajectory are excluded. The excluded count is unknown.
  - **C (lead-time comparison):** the false-warning ratios are verified from stored aggregates (3.15, 1.67, 4.15, 2.36). The comparison is confounded by operating point.
  - **D (uncertainty):** configuration counts and the bootstrap implementation are verified. The intervals do not describe unseen aircraft.
  - **E (reproducibility):** gaps confirmed. None can be closed without the missing artifacts.
- **Corrections.** Active documents overstated "independent simulator" and "20 of 20 runs", and left the event and PR-AUC scope unstated. These were qualified in the README, its public copy, the website section and `REPRODUCIBILITY.md` (§6). Frozen research outputs were not edited; corrections to them are listed in §5 and §6.
- **Decision.** The current study can be released honestly with qualified claims (§11). One item blocks release: since `30e7732` rebuilt the paper PDF, the frozen baseline check fails, and with it one CI test (`test_all_79_baseline_hashes_pass`). CI on `main` has been red since then. Fixing it needs an author decision (§12).

## 2. Artifact inventory and provenance

### Locations searched
- The working tree (including ignored files).
- The whole local filesystem, for `item50_final*`, `envelopes.json`, `*_meta.csv`, `*.parquet`, `*.npy` / `*.npz` and `*phase4*`.
- All five remote branches (`main`, `credibility-v1.1`, `claude/aeroguard-launch-audit-a8kfa9`, `claude/loving-fermi-ql3cyo`, `pre-clean-history-backup`), fetched read-only and searched by file tree.
- GitHub releases (none exist).
- Git tags, local and remote (none exist).

This search covers what is accessible from this environment. **It does not establish that the artifacts do not exist elsewhere.**

### 1 — Located and inspected
| Artifact | Location | Contents / state | Supports |
|---|---|---|---|
| Protocol | `experiments/phase4/PROTOCOL.md` | Pre-specified design. SHA-256 `54fd8d54…035f2f` matches `primary.json` and `phase4/__init__.py:24`. | Design, decision rules |
| Deviations, status, ranges, assumptions | `experiments/phase4/{DEVIATIONS,STATUS,PARAMETER_RANGES,SIMULATOR_ASSUMPTIONS}.md`, `published_reference.json` | P4-D1–D5 cover the JSBSim harness only. `STATUS.md` is marked superseded. | Context |
| Run report | `outputs/phase4/run_20261015T152932Z/REPORT.md` | Narrative and tables. | Claims |
| Aggregates | `primary.json`, `jsbsim.json`, `robustness.json`, `robustness_runs.csv`, `per_config.csv` (same directory) | Point estimates, 95% bootstrap intervals, counts, thresholds, false-warning rates, paired differences, partition, JSBSim terminations. No row, score or event records. | Aggregate verification only |
| Code | `phase4/{__init__,metrics,models,panel,uncertainty}.py` (in full); `phase4/sim.py` (split, generation); `phase4/configs.py` (executed); `scripts/run_phase4.py`; `scripts/phase4_generate*.py`; `ml/events.py`; `ml/calibration.py`; `experiments/items33_42/items37_39/src/items37_39.py`; `aeroguard_dataset/labeling.py`; `ml/temporal_features.py` (usable mask) | Identical to the results commit (`git diff edf768c HEAD` is empty for all of these paths). | Metric definitions |
| Tests | `tests/test_phase4_core.py` | 20 synthetic tests. | Component behaviour |
| Website | `dashboard/src/components/sections/Phase4.tsx`, `dashboard/src/data/phase4.json`, `dashboard/parity/check_metrics.mjs` | Values exported from the run directory. | Public claims |
| Frozen model | `outputs/ml_v03/models/primary_model_D_1s.joblib` | SHA-256 `707d4c61…03f3`, unchanged. | `F_v03` provenance |
| v0.3 metadata (indirect evidence) | `data/metadata/trajectory_metadata_v3.csv` | Trajectory durations and crossing times for the v0.3 aircraft (a different seed from Phase 4). | Plausibility for Issue B only |
| Records | `README.md`, `RESEARCH_LOG.md` (RL-002, RL-008), `CHANGELOG.md`, `CONTRIBUTING.md`, `REPRODUCIBILITY.md`, `baselines/` | — | Provenance, rules |

### 2 — Located but not fully inspected
- `outputs/phase4/run_20261015T152932Z/item50.json` and `scripts/phase4_item50.py` (Item 50 values were checked only as they appear in the report).
- `phase4/jsbsim_sim.py`: only the trim-failure path and the metadata fields were read.
- The `item45`–`item52` blocks of `primary.json`, beyond the fields cited here.
- `paper/AeroGuard_Research_Paper.md`: searched only; it has no Phase 4 content.

### 3 — Referenced but not found
| Artifact | Referenced at | Consequence |
|---|---|---|
| `outputs/phase4/item50_final_20261016T081001Z/` (final Item 50 report) | `dashboard/LAUNCH_AUDIT_20261016.md:171` (as `item50_final_*`, "not in this repository") | Item 50 rests only on `item50.json` and `REPORT.md` §9. `STATUS.md` still says "partly done". |
| `<data_dir>/D0`, `<data_dir>/D1`: `configs.json`, `C00…O06.parquet`, `*_meta.csv`, `envelopes.json` | `scripts/phase4_generate.py:30-52`; `REPORT.md:158` | No row-level recomputation is possible. The counts in Issue B cannot be broken down. |
| `<data_dir>/JSB/c172p.parquet`, `c172p_meta.csv`, `envelope.json`, `feasibility.json` | `scripts/phase4_generate_jsbsim.py:4` | Same, for JSBSim. |
| Fitted models, score arrays, event tables | `REPORT.md:158` | Issues A and B, and part of C, cannot be quantified. |
| `tests/test_phase4_sim.py` | `phase4/sim.py:12-13` | The docstring cites a nonexistent file. The sea-level identity test lives in `test_phase4_core.py:74-84`. |
| `scripts/run_phase4_jsbsim.py` | `PROTOCOL.md:192` | The `jsbsim` stage of `run_phase4.py` does this job. |
| Module `phase4.published` | `phase4/__init__.py:18` | Item 50 code is in `scripts/phase4_item50.py`. |
| Git tag / release `v1.1.0` | `CHANGELOG.md:6`, `CITATION.cff` | No tag exists locally or on `origin`, and there are no GitHub releases. The wording was corrected in the pre-release review (§6): v1.1.0 is described as prepared, not released, and `version` and `date-released` were removed from `CITATION.cff`. |

### 4 — May exist elsewhere but inaccessible
- The original session's scratch `<data_dir>` (about 3 GB; `STATUS.md:12`, `REPORT.md:158`).
- Any local copy of the final Item 50 report on the author's machine.
- The Zenodo record (not Phase 4; not checked).

## 3. Results of the five audit issues

### Issue A — Row-level PR-AUC and rows already unsafe
- **Labels and population:**
  - Label: `future_stall_5s`, meaning any unsafe sample in `(t, t+5 s]` (`aeroguard_dataset/labeling.py:39-52`).
  - Population: every *usable* row, meaning the label is available and the 1 s window is full (`ml/temporal_features.py:187-194`, `phase4/panel.py:164`).
  - Rows: every 0.01 s row for the headline groups. Robustness runs use a 0.05 s stride (`run_phase4.py:387`).
  - PR-AUC is `sklearn.average_precision_score` over those rows (`phase4/metrics.py:62`, `:138-140`).
- **Already-unsafe rows:** included. No mask on `is_unsafe` is applied (`metrics.py:138-140`). A row inside an unsafe run is positive whenever another unsafe sample follows within 5 s. RL-002 recorded the same fact for v0.3 (`RESEARCH_LOG.md:287`).
- **Recalculation:** not possible. The rows, labels and scores were not archived (§2). **The effect size is unknown.**
- **Is the exclusion justified?** For the stated question, warning *before* a stall, an analysis without post-crossing rows is the more relevant secondary analysis. The protocol (§3) does not define one, so it would be exploratory and must not replace the primary metric.
- **Disposition:** documented. The headline values are retained, with the scope stated in the README and on the website. **Unresolved for this release** because data are missing.

### Issue B — Stall-event definitions and event-level performance
- **Events.** A stall event is a maximal run of `is_unsafe` inside the usable rows of one trajectory. Its crossing time is the first row of that run (`ml/events.py:88-102`, `items37_39.py:73-93`). Event detection sees **usable rows only**. The `ml/events.py:83-87` docstring says it should see the whole trajectory; Phase 4 passes usable rows (`metrics.py:78-80`, `:141`).
- **Fewer than 5 s remaining.** Labels exist only up to `n − 500` rows (`labeling.py:39`). A crossing followed by less than 5 s of trajectory is therefore not in the usable rows and is **not counted**. A trajectory with roughly 6 s or less of simulation (1 s window plus 5 s horizon) contributes no rows at all.
- **Repeated crossings** count as separate events. From `primary.json`, `n_events` vs `n_first_events`:

  | Group | Events | First events | Repeat crossings |
  |---|---|---|---|
  | SEEN | 105 | 78 | 27 (25.7%) |
  | IDH | 202 | 152 | 50 (24.8%) |
  | OOD | 276 | 211 | 65 (23.6%) |
  | C00 | 54 | 38 | 16 (29.6%) |

  One warning episode can be credited to several events (synthetic check S6).
- **Left-censored events.**
  - The `left_censored` flag is recorded (`items37_39.py:91`) but never used by any Phase 4 code. Such events stay in the event count and cannot be warned (check S3).
  - Their number was not stored. In the indirect v0.3 evidence, no first crossing occurred before t = 1 s.
- **Trajectories that end early or have no usable rows.**
  - All 300 trajectories per configuration are generated and kept in metadata (`phase4/sim.py:196-207`). The validity envelope truncates trajectories; it does not reject them. The parquet keeps only usable rows (`scripts/phase4_generate.py:30-32`), and populations are counted from it (`run_phase4.py:81-89`).
  - So the only way a trajectory disappears is having zero usable rows. This is established from code. Non-finite features raise an error rather than being dropped (`panel.py:166-168`).

  | Population | Design | Evaluated | Missing |
  |---|---|---|---|
  | SEEN | 540 | 505 | 35 |
  | IDH | 1,200 | 1,107 | 93 |
  | OOD | 1,800 | 1,650 | 150 |
  | C00 | 300 | 268 | 32 |
  | Fitting (train / val) | 2,520 / 540 | 2,323 / 502 | 197 / 38 |
  | JSBSim | 1,000 | 906 | 94 |

  - JSBSim: 3 trajectories failed to trim (zero steps), 430 completed normally (20 s), 556 ended on the flight-path-angle limit and 11 on the bank limit (`jsbsim.json`). So 91 early-terminated trajectories had no usable rows.
  - **By regime and termination reason, per trajectory:** not verifiable without the `*_meta.csv` files.
  - Indirect evidence from v0.3 (not Phase 4): 115 of 250 stall-regime trajectories lasted 6.0 s or less, and 86 of 470 trajectories that stalled (18.3%) had their first crossing with less than 5 s remaining. This makes it plausible that the excluded Phase 4 trajectories are mostly abrupt stalls. It does not prove it.
  - The JSBSim crossing rates in `REPORT.md:93` are computed over all generated trajectories (`run_phase4.py:340`), while event metrics count only usable rows.
- **Lead time.**
  - Lead = crossing time minus the start of the earliest warning episode that overlaps the 5 s before the crossing, capped at 5 s (`ml/events.py:92-99`).
  - Truncated history caps the lead at the history available (check S4).
  - The median and mean use warned events only (`metrics.py:84-88`).
  - Coverage at L counts only events with at least L s of history, so the 2 s and 4 s coverage figures use different denominators (`metrics.py:90-93`, check S5). That explains coverage at ≥4 s exceeding coverage at ≥2 s in `REPORT.md:24-31`. The eligible counts were not stored.
- **Lead credit plus false warning: yes, both can happen.** An episode that starts 7 s before a crossing earns a 5.0 s lead and is also counted as a false-warning episode, because its start row's label is 0 (check S2).
- **Conclusion.** Reported recall (0.96–1.00) and lead times describe a **selected subset**: crossings followed by at least 5 s of trajectory, inside trajectories with usable rows, about a quarter of them repeat crossings. The excluded crossings, the left-censored events and the share of lead credited through early "false" episodes cannot be counted without data. **Unresolved for this release**, and documented in active documents.

### Issue C — Lead-time comparison and false-warning rates

**Verified from stored aggregates** (`primary.json` → `group_metrics.*.false_warning`):

| Group | M_A false warnings / sim. h | M_D false warnings / sim. h | Ratio | Median lead M_A | Median lead M_D |
|---|---|---|---|---|---|
| SEEN | 98.8 | 31.3 | 3.15 | 4.44 s | 2.35 s |
| IDH | 61.5 | 36.9 | 1.67 | 3.66 s | 1.98 s |
| OOD | 96.8 | 23.3 | 4.15 | 2.20 s | 1.38 s |
| C00 | 74.2 | 31.5 | 2.36 | 4.30 s | 4.01 s |

- These are reproduced arithmetically from the stored rates, not from the underlying data.
- **Paired median-lead difference, M_D − M_A:** IDH −1.68 s [−2.42, −0.45]; OOD −0.82 s [−2.24, −0.34] (`item53_primary_paired`).
- **Thresholds.** Each model uses its own threshold: top 10 by training-row F1, then the best validation F1, on validation rows from the training configurations only (`ml/calibration.py:27-49`, `phase4/models.py:69-76`). No test data were involved.
- **Consistency of the false-warning measurements.** False warnings are measured with the same definition and population in the primary run. They are not computed at all in the 15 robustness runs at 0.05 s resolution (`metrics.py:143`).
- **Why the comparison is not fair:**
  - The two models run at different false-warning rates (1.7–4.2× apart).
  - A model that warns more often and longer earns earlier credited warnings, including via episodes that are themselves counted as false (Issue B).
  - Median lead is taken over the warned events of each model.
- **What the pre-registered rule establishes.** Claim K2 ("M_D median lead > M_A") failed: the sign held in 9 of 20 runs and the primary interval is not in favour (`robustness.json`). At these operating points the opposite direction was observed.
- **What it does not establish.** Whether either model has a lead-time advantage at a matched false-warning rate.
- **Wording.** "3–4 times as many" (`REPORT.md:35`) is **contradicted** for IDH (1.67×) and C00 (2.36×). `REPORT.md` is a frozen run record and was not edited; the correction is recorded here, and the active README states 1.7–4.2×.
- **Future work (not done, not pre-registered).** Fix target false-warning rates in a dated protocol amendment. Choose each model's threshold on validation rows from the training configurations. Compare first-event recall and lead with a paired bootstrap, on a **new data seed** (D1 was already used in Item 53).

### Issue D — Generalisation and uncertainty
- **Counts, verified:**
  - `primary.json` → `partition`: TRAIN 12, IDH 4, OOD 6, C00 1.
  - `per_config.csv`: 23 rows.
  - `configs.design()`, re-executed, gives the same 23 configurations. The stored `d_ood` and `n_out` match exactly.
  - IDH configurations lie 0, 2, 2 and 3 parameters outside the training range (H01–H04).
  - Events per training-configuration test split are 3–21, so only T09 passes the 15-event gate. IDH has 36–64 per configuration and OOD 37–55.
  - JSBSim uses one aircraft model (`c172p`, `scripts/phase4_generate_jsbsim.py:16-22`).
- **Bootstrap, verified from code:**
  - It resamples whole trajectories uniformly within a pooled group (B = 1000 by default, `phase4/__init__.py:34`; `metrics.py:108-111`, `:158-166`).
  - Seeds differ by group (`run_phase4.py:155`).
  - Model, threshold and configurations stay fixed. Not stratified.
- **What the intervals describe:** sampling variation of new trajectories from **these specific** configurations, for this fitted model and threshold.
- **What they cannot establish:** performance on other aircraft configurations, because configurations are not resampled; variation from retraining or from the choice of training configurations; or anything about other simulators.
- **What a valid configuration-level analysis needs (specification only):**
  - IDH configurations are scrambled Sobol draws from the core box, so a population-level estimand is definable. But n = 4 is too small, and a valid estimate would need refitting over many 12/4 splits of the 16 core-box configurations.
  - OOD configurations are hand-designed stress cases, so no population-level interval is valid. They can only be reported one configuration at a time.
- **JSBSim.**
  - What the evidence shows: a model trained only in AeroGuard (`X_D`, 20 features with no control inputs) keeps partial skill on one JSBSim aircraft model (30 test events).
  - What it does not show: generalisation across simulators, across aircraft or to real flight. Labels, features, pulse profiles and the validity envelope are shared, and the elevator mapping is derived from AeroGuard (P4-D2).
  - "Independent simulator" in active documents was corrected to "second simulator model".
- **The 20 robustness runs** come from 6 distinct partition × data-seed combinations. The 5 primary runs share data. Ten of the 40 rows are at 0.01 s and 30 at 0.05 s (`robustness_runs.csv`). The OOD set is the same in every run. Active wording was corrected.

### Issue E — Reproducibility and provenance
| Concern | Result | Classification |
|---|---|---|
| Datasets, metadata, models and score arrays missing | Not in the repository, on any remote branch, in releases or on the local filesystem | **Confirmed** |
| `jsbsim==1.3.2` not pinned | Absent from `requirements-pinned.txt`; the omission is deliberate and documented (`CHANGELOG.md`, Phase 4 entry, "Dependency"; `REPORT.md:158`) | **Confirmed gap**, now documented in `REPRODUCIBILITY.md` |
| Python 3.12 vs 3.13 | The pins and CI use 3.12 (`requirements-pinned.txt:6`, `.github/workflows/tests.yml:26`); the Phase 4 report says 3.13 (`REPORT.md:158`). These are different runs, not a contradiction, but the Phase 4 package versions were never recorded. | **Clarified**; the version gap is confirmed |
| References to nonexistent files | `tests/test_phase4_sim.py`, `scripts/run_phase4_jsbsim.py`, `phase4.published` (§2) | **Confirmed.** Not edited, because editing would change frozen run-time code or the protocol. |
| Outputs lack commit, versions, B, checksums | No such fields in `primary.json`; the run directory has no environment file. The commit is recorded in RL-008 (`0eb47cd`). | **Confirmed** |
| Code drift since the run | `git diff edf768c HEAD` on all experiment paths is empty | Verified, no drift |
| Data generated with the committed code | Generation started at or before the 15:02 code commit (`STATUS.md:12`, commit `ab91bed`); there are no dataset checksums | **Not verifiable** |
| Full determinism | Small-scale generation determinism is tested (`test_phase4_core.py:102-110`); full scale and JSBSim are not | **Not verifiable** |
| Clean-machine reproduction | Not performed | **Not done** |
| Baseline integrity check | `sha256sum -c baselines/v0.3.sha256` gives 78 OK and 1 FAILED. The manifest records `c893914b…`, which is the PDF before `30e7732` (`git show 30e7732^:paper/AeroGuard_Research_Paper.pdf`). The current PDF and its identical copy in `dashboard/public/paper/` are `7ac9e2e9…`. The docs said to expect all OK (`baselines/README.md:31`, `REPRODUCIBILITY.md:94`). | **Confirmed.** Both hashes are documented in `baselines/README.md` and `REPRODUCIBILITY.md`; the manifest is unchanged. Release decision in §12. |
| CI test suite | `tests/test_phase3_integrity.py::test_all_79_baseline_hashes_pass` asserts 79/79, so it fails. Local run of the CI selection: 1 failed, 326 passed, 24 skipped, 11 deselected. The same failure occurs on a clean `git archive HEAD` copy, and GitHub CI on `main` shows the same counts (run 11, job 120900315869; red since run 8). The README and `REPRODUCIBILITY.md` still promised "191 passed". | **Confirmed, pre-existing.** Documentation corrected; the test was not edited (§12). |

## 4. Verified and unverified headline numbers

Evidence levels:
- **L1:** the website or README matches a stored aggregate.
- **L2:** the metric code is correct (code reading plus synthetic checks).
- **L3:** the stored result is reproduced from underlying data.
- **L4:** independently validated on independent data.

| Number | Stored source | L1 | L2 | L3 | L4 |
|---|---|---|---|---|---|
| SEEN PR-AUC 0.880 [0.847, 0.906], median lead 2.35 s [1.74, 4.64] | `primary.json` → `group_metrics.SEEN.M_D` (0.88004, 2.345) | Yes | Yes, with Issues A and B scope | No (data missing) | No |
| IDH PR-AUC 0.891 [0.869, 0.909], median lead 1.98 s | `…IDH.M_D` (0.89052, 1.980) | Yes | Yes, with scope | No | No |
| OOD PR-AUC 0.863 [0.842, 0.883], median lead 1.38 s | `…OOD.M_D` (0.86321, 1.380) | Yes | Yes, with scope | No | No |
| JSBSim PR-AUC 0.780 [0.708, 0.827], median lead 1.20 s, 30/30 warned | `jsbsim.json` → `cross\|X_D\|20260817\|JSB_test` | Yes | Yes, with scope | No | No (one simulator model; same author and code) |
| JSBSim native 0.937, 4.79 s | `native\|X_D\|20260817\|JSB_test` | Yes | Yes | No | No |
| Configuration design (23; 12/4/6/1), `d_ood`, `n_out` | `primary.json`, `per_config.csv` | Yes | Yes | **Yes** (regenerated from committed code) | n/a |
| False-warning ratios 3.15 / 1.67 / 4.15 / 2.36 | `primary.json` | Yes | Yes | Arithmetic only | No |

None of the Phase 4 test data were used before Phase 4 (new seeds and configurations). But this is a single-author, single-pipeline evaluation and must not be called independent or blind validation.

## 5. Claim-disposition table

| # | Claim / number | Current wording (before this audit) | Evidence inspected | Status | Scientific limitation | Action | Location |
|---|---|---|---|---|---|---|---|
| 1 | SEEN / IDH / OOD PR-AUC and lead (as in §4) | Cards and README numbers | Stored aggregates; metric code | Partially verified (L1–L2) | PR-AUC includes in-stall rows; events are a selected subset; no recomputation possible | **Qualify** (done) | `Phase4.tsx:96-100`; `README.md` Phase 4 note |
| 2 | "No loss detected" inside the envelope (Δ +0.010 [−0.022, +0.048]) | Pre-registered outcome | `item44` code (`run_phase4.py:190-200`), stored values | Verified as the pre-registered verdict | 4 configurations; intervals are trajectory-level | **Qualify** (done: interval scope) | `README.md:246`; `Phase4.tsx:27-30` (already says the interval is wide) |
| 3 | "Modest loss" on unfamiliar aircraft | — | Stored values | Partially verified | 6 designed configurations; no population inference | Retain + qualify (done via "some parameters outside the range") | `Phase4.tsx:19` |
| 4 | "Transfer to an independent simulator"; "the independent JSBSim Cessna 172 model" | Title, lede, README row | Code, `DEVIATIONS.md`, `jsbsim.json` | **Contradicted** as worded | Shared labels, features, profiles; one aircraft; 30 events | **Correct** (done) | `Phase4.tsx:45,70`; `README.md:247`; `dashboard/public/docs/AEROGUARD_README.md:247` |
| 5 | JSBSim card shown next to M_D results | "Different simulator" card | `run_phase4.py:323-360`, `panel.py:151-153` | Partially verified | It is `X_D` (20 features), not `M_D` | **Qualify** (done) | `Phase4.tsx:20`; README row 247 |
| 6 | "20 of 20 configuration × seed runs" | README row | `robustness_runs.csv` | Partially verified | 6 distinct data × partition combinations; not replications | **Correct** (done) | `README.md:248`; `Phase4.tsx:54` |
| 7 | Lead-time advantage "not supported" | Verdict | `robustness.json`, paired CIs | Verified as the pre-registered outcome | Operating-point confounded; at own thresholds M_A led | **Qualify** (done) | `Phase4.tsx:57-60`; `README.md:248` |
| 8 | "3–4 times as many false-warning episodes" | `REPORT.md:35` | `primary.json` | **Contradicted** (IDH 1.67×, C00 2.36×) | — | **Correct** by erratum in this report; frozen file not edited | `outputs/phase4/run_20261015T152932Z/REPORT.md:35` |
| 9 | "M_A 3–4× the false-warning rate on OOD" | `REPORT.md:139` | `primary.json` | Approximately right (4.15×) | — | Retain (note: 4.2×) | `REPORT.md:139` |
| 10 | Event recall 0.96–1.00, "stalls warned 201/202" | Cards, report | Code, `n_first_events` | Partially verified | Excludes crossings with less than 5 s remaining; about 25% repeats; left-censored events not reported | **Qualify** (done) | `Phase4.tsx:96-100`; README note |
| 11 | Coverage ≥2 s / ≥4 s | `REPORT.md:22-31` | `metrics.py:90-93` | Verified as code | Different denominators; counts not stored | Qualify (this report); website does not show it | `REPORT.md` §2 |
| 12 | Frozen model "ranked stalls" on OOD about as well (0.871 vs 0.863) | Website callout | `primary.json` | Verified (L1) | It ranks time steps, not stalls | **Correct** wording (done) | `Phase4.tsx:120` |
| 13 | "For comparison, the v0.3 model on its own aircraft: PR-AUC 0.890" | Website footnote | `outputs/ml_v03/metrics/primary_model_metrics.json:4` (0.89028) | Verified (L1) | The v0.3 test set had been used repeatedly in earlier work; not a blind result | Retain | `Phase4.tsx:100` |
| 14 | "Protocol committed before any of this data existed" | Lede | Git order: protocol `5f35269` (14:47) → code `ab91bed` (15:02) | Partially verified | Timestamps are set by the author; data generation is not in Git | Retain | `Phase4.tsx:70` |
| 15 | Regime gap (gradual 4.56 s vs abrupt 0.70 s) | Finding, README | `primary.json` `item52` (point values via export and parity) | Verified (L1) | Abrupt stalls are the regime most likely under-counted (Issue B) | Retain; the scope note covers it | `Phase4.tsx:39-42`; `README.md:246` |
| 16 | Item 50 published-evidence comparison | `REPORT.md` §9 | `item50.json` not fully inspected; final report not found | Unverifiable (final) | No primary source | Retain as is; not on website (correct) | `REPORT.md` §9; `STATUS.md` |
| 17 | Abstention and conformal results (Items 46–47) | `REPORT.md` §5–6, RL-008 | Code (`uncertainty.py`) only | Partially verified (L2 for code) | Row-level, same row population as Issue A | Retain (not on website) | `REPORT.md` §5–6 |
| 18 | "First tagged release is v1.1.0"; `CITATION.cff` version 1.1.0, released 2026-10-24 | `CHANGELOG.md:6`, `:25-27`, `:52`; `CITATION.cff:11-12` | `git tag`, `ls-remote`, GitHub releases | **Contradicted** (no tag or release) | — | **Corrected**: "prepared, not yet tagged"; `version` and `date-released` removed from `CITATION.cff` until the tag exists (`CONTRIBUTING.md:115-116`) | `CHANGELOG.md`, `CITATION.cff` |
| 19 | Baseline check "expect every line OK" | `baselines/README.md:31`, `REPRODUCIBILITY.md:94` | `sha256sum -c`; Git history of the PDF | **Contradicted** (PDF fails) | — | **Corrected**: both hashes stated; the current PDF does not match the baseline | `baselines/README.md`; `REPRODUCIBILITY.md:94` |
| 20 | CI "expected result is 191 passed, 24 skipped, 11 deselected" | `README.md:230`, public copy, `REPRODUCIBILITY.md:44,95,359` | GitHub CI log; local run | **Contradicted** (326 passed, 1 failed since `30e7732`) | — | **Corrected** with dated current result; the history is kept | same |

The paper (`paper/AeroGuard_Research_Paper.md`) makes no Phase 4 claims, so it needs no Phase 4 change.

## 6. Documentation changes made (uncommitted)

| File | Change |
|---|---|
| `dashboard/src/components/sections/Phase4.tsx` | Lede: "a second simulator, JSBSim's community Cessna 172 (c172p) model". JSBSim card subtitle names the model without control inputs. OOD card: "some parameters outside the range". JSBSim finding retitled "Transfer to a second simulator model" and scoped to one aircraft model. K1: runs are fits over 3 partitions × 2 data seeds. K2: at own thresholds the instantaneous model warned earlier with more false warnings; the question stays open. Footnote states the interval, PR-AUC and event scope. "ranked stalls" changed to "ranked time steps". No number changed; `phase4.json` untouched. |
| `README.md` and `dashboard/public/docs/AEROGUARD_README.md` | The three Phase 4 rows qualified identically (interval scope, second simulator model, `X_D`, 30 events, 20 fits / 6 combinations, 1.7–4.2× false warnings) plus one scope paragraph. |
| `REPRODUCIBILITY.md` | New section "Phase 4 — aircraft family and JSBSim (Items 43–53)": what is unarchived, the `jsbsim` dependency, the unrecorded environment, and what is unverified. |
| `baselines/README.md` | Dated note: since `30e7732` the check gives 78 OK / 1 FAILED. It gives the baseline PDF hash (`c893914b…`) and the current PDF hash (`7ac9e2e9…`), and says the current PDF does not match. The "still carries the older link" sentence is corrected. Manifest not regenerated. |
| `REPRODUCIBILITY.md` (levels 0 and 1; test policy; testing section), `README.md` and public copy (CI paragraph) | Expected baseline-check and CI results corrected to what is observed since `30e7732` (78/79; 326 passed, 1 failed, 24 skipped, 11 deselected), with the earlier 191-passed result kept as history. |
| `CHANGELOG.md` (header and `[1.1.0]` section), `CITATION.cff` | v1.1.0 described as prepared, not tagged or released. `version` and `date-released` removed from `CITATION.cff`. |
| `CHANGELOG.md` (*Unreleased*), `RESEARCH_LOG.md` (new RL-009) | Records of this audit. |
| `reports/PHASE_A_FINAL_AUDIT.md`, `reports/PHASE_A_STATUS.md` | New. |

**Proposed but not applied** (frozen or protected files; needs the author's decision or a new version):
1. `outputs/phase4/run_20261015T152932Z/REPORT.md:35`: "3–4 times" should read "1.7–4.2 times (SEEN 3.2×, IDH 1.7×, OOD 4.2×, C00 2.4×)". The frozen-record rule (`CONTRIBUTING.md:74-80`) says to correct this by a new entry, which this report is.
2. `REPORT.md` §2 coverage columns: note that the denominators differ between ≥2 s and ≥4 s.
3. `phase4/sim.py:12-13`, `phase4/__init__.py:18` and `PROTOCOL.md:192` cite nonexistent files or modules. Fixing them would change frozen code or a protocol that is never edited, so the references are recorded here instead.
4. `tests/test_phase3_integrity.py:58-60` (asserts 79/79 baseline hashes). It fails since the PDF rebuild. Not edited, because changing a failing integrity test to pass is the author's decision (§12).
5. When the v1.1.0 tag is created: restore `version` and `date-released` in `CITATION.cff` and date the `[1.1.0]` CHANGELOG heading.

## 7. Checks and calculations actually executed

Checks 1, 2, 9 and 13 ran from the repository root, with bytecode and pytest caches disabled; `git status --porcelain --ignored` showed no new files afterwards. The other checks ran in the scratch directory or on copies there. Scratch-only packages: scikit-learn 1.9.1, scipy 1.18.1, pytest, matplotlib, esbuild 0.24.0. System: CPython 3.13.17, numpy 2.5.4, pandas 3.0.5. These versions are newer than the pins.

| # | Check | Result |
|---|---|---|
| 1 | Website parity, `node dashboard/parity/check_metrics.mjs` (read-only), before and after edits | 176/176 passed both times |
| 2 | `pytest tests/test_phase4_core.py` | 20 passed |
| 3 | Custom weighted AP vs `sklearn.average_precision_score`: 300 random cases with many ties, weighted and unweighted, plus equality with physically duplicated rows | Largest difference 2.2e-16 |
| 4 | Synthetic event checks (S2–S7) with `phase4.metrics.evaluate` / `event_table` | S2: early episode → lead 5.0 s and 1 false episode. S3: left-censored event → recall 0. S4: 0.4 s history → lead 0.4 s, excluded from coverage. S5: coverage 0.667 at ≥2 s vs 1.0 at ≥4 s. S6: two crossings 0.3 s apart → 2 events, both credited by one episode. S7: weighted median = `np.median`. These show code behaviour only, not real results. |
| 5 | Cross-check of stored aggregates (`primary.json`, `jsbsim.json`, `robustness*.{json,csv}`, `per_config.csv`, `phase4.json`) | All headline values agree. Ratios, counts, events, terminations and robustness composition as reported above. |
| 6 | `configs.design()`, `partition("P0")` and `unfamiliarity()` vs `per_config.csv` | 23 configurations; 12/4/6/1; zero mismatches in `d_ood` / `n_out` |
| 7 | Protocol SHA-256 vs `primary.json`; frozen-model SHA-256 | Both match |
| 8 | `git diff edf768c HEAD` on experiment code | Empty |
| 9 | `sha256sum -c baselines/v0.3.sha256` | 78 OK, 1 FAILED (paper PDF, pre-existing) |
| 10 | Dashboard in a scratch copy of `dashboard/` (current working tree): `npm ci`, `npm run build` (`tsc -b && vite build`), `oxlint`, `node parity/check.mjs` | Build succeeds (only the existing chunk-size warning); lint exit 0; physics parity 420/420. The built bundle contains the new wording and no "independent simulator". |
| 11 | v0.3 metadata: durations and crossing times (indirect evidence, Issue B) | 115/250 stall-regime trajectories ≤6.0 s; 86/470 (18.3%) first crossings with less than 5 s remaining |
| 12 | Protected-file fingerprint (`outputs/phase4`, `experiments/phase4`, `paper`, `dashboard/src/data`, 27 files) before and after | See §9 |
| 13 | Full CI selection (`pytest tests` with the workflow's 11 deselections) | 1 failed, 326 passed, 24 skipped, 11 deselected. The failure, `test_all_79_baseline_hashes_pass`, reproduces on a clean `git archive HEAD` copy and matches GitHub CI on `main`, so it is pre-existing. |
| 14 | PDF history: `git show 30e7732^:paper/AeroGuard_Research_Paper.pdf` and `30e7732:…` hashed | The manifest hash equals the pre-`30e7732` PDF; `30e7732` and the current files (both copies) give `7ac9e2e9…` |

## 8. Missing evidence and its consequences

| Missing | Consequence |
|---|---|
| Phase 4 row data, labels, scores | Issue A's size is unknown. No PR-AUC can be recomputed (L3 impossible). |
| Event records, `*_meta.csv` | Excluded crossings, left-censored events, the per-trajectory causes of the count gaps, and lead credited through early false episodes are all unknown. |
| Fitted models | No re-scoring and no matched-threshold analysis without retraining. |
| Dataset checksums, environment record, B | The provenance chain from code to data to results cannot be verified. |
| Final Item 50 report | Item 50 stays "partial, secondary/U-level references only". |

## 9. Reproducibility status

- **Achieved:**
  - Stored aggregates are internally consistent and match the public documents.
  - The configuration design regenerates exactly.
  - The metric code behaves as documented.
  - Phase 4 unit tests pass (20/20). The full CI selection has one pre-existing failure, the baseline-hash test (§12).
  - The experiment code is unchanged since the run.
- **Not achieved:** reproduction of any Phase 4 metric from data; a clean-machine run; independent replication; verified determinism.
- **Protected artifacts:** the 27-file fingerprint of `outputs/phase4`, `experiments/phase4`, `paper` and `dashboard/src/data` is identical before and after this audit. The frozen model hash is unchanged. The baseline check result is unchanged (78/79, same failing file).

## 10. Remaining limitations

These are already stated in RL-008, `SIMULATOR_ASSUMPTIONS.md` and the report, and are restated briefly:
- Simulation only, one author and one code base.
- 2D surrogate simulator with optimistic assumptions: no sensor noise, turbulence or pilot in the loop.
- 4 IDH and 6 OOD configurations.
- 30 JSBSim test events on one aircraft model.
- Row-level metrics on autocorrelated rows.
- Event metrics on a selected subset.
- Lead time compared at unmatched operating points.
- Item 50 has no primary source.

## 11. Final decision — what can responsibly be claimed now

The following may be claimed **with the qualifications now present in the README and on the website**:
1. In this simulator, a temporal warning model trained on 12 configurations showed **no detected loss** on 4 held-out configurations inside the training envelope, and a **modest loss, mainly in lead time**, on 6 designed unfamiliar configurations. The intervals describe new flights from those configurations, not other aircraft.
2. Its **PR-AUC advantage** over the instantaneous model held in all 20 model fits (6 partition × data combinations).
3. A **lead-time advantage was not shown**. At the models' own thresholds the instantaneous model warned earlier with 1.7–4.2× more false warnings, so the lead question is open.
4. A model trained only in AeroGuard kept **partial skill on one JSBSim aircraft model** (PR-AUC 0.78 vs 0.94 native; 30 events). This is simulator-to-simulator transfer, not validation.
5. All Phase 4 figures are traceable to stored aggregates produced by code that is unchanged since the run. **They cannot currently be recomputed from data.**

**Must not be claimed:**
- independent replication or validation
- blind evaluation
- generalisation to unseen aircraft in general, across simulators, or to real flight
- that PR-AUC measures warning strictly before the stall
- that recall covers all stall crossings
- that the temporal model has no lead-time advantage.

## 12. Release-blocking issues

1. **Resolved (uncommitted): CI red on `main` because of the rebuilt paper PDF.** Option (a) was implemented without editing `v0.3.sha256`: recovered baseline PDF in `paper/archive/`, new `baselines/paper_pdf_v1.1.0.sha256`, stricter `test_all_79_baseline_hashes_pass`. Local CI selection: 327 passed, 24 skipped, 11 deselected. The original analysis follows.
   - `test_all_79_baseline_hashes_pass` fails (78/79), and has done since `30e7732` (GitHub CI runs 8–11).
   - The documentation now states this accurately, but a release from a red CI state is not advisable.
   - The author must choose one of:
     - (a) add a separate checksum record for the rebuilt PDF and change the test to check the 78 baseline files plus that record, as a recorded, reviewed change;
     - (b) restore the baseline PDF bytes and keep the rebuilt PDF under a new name;
     - (c) accept a known failing test, with the reason documented.
   - The frozen manifest must not be regenerated.
   - No experiment is needed.
2. **Resolved in this review:** the v1.1.0 statements no longer claim a tag or release. Creating the tag, then restoring `CITATION.cff` `version` and `date-released`, belongs to the release phase.

No scientific issue is release-blocking, **provided the qualified wording in §6 is kept**. Issues A and B affect interpretation, and they are now disclosed.

## 13. Completed, unresolved, and optional

**Completed in Phase A:**
- Evidence inventory (§2).
- Issues A–E investigated as far as the evidence allows.
- Ratios, counts and configuration design verified.
- Active-document corrections (§6).
- Reproducibility section.
- Baseline-check note.
- This report and the status summary.

**Unresolved evidence gaps (need archived artifacts, or regeneration as a new run):**
- The size of Issue A.
- Excluded crossings, left-censored events and the early-episode lead credit in Issue B.
- Per-trajectory reasons for the count gaps.
- Data checksums and determinism.
- The final Item 50 report.

**Optional future research (not needed to freeze this version):**
- A threshold-matched lead-time comparison on a fresh data seed under a new protocol.
- Configuration-level evaluation over many 12/4 splits.
- PR-AUC without post-crossing rows, and first-event recall, as labelled secondary analyses.
- More JSBSim aircraft models.
- Primary-source values for Item 50.
- Independent replication.
