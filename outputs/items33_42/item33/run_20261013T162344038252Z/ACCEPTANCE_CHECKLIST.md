# Item 33 acceptance checklist (PROTOCOL.md section 18)

Run `run_20261013T162344038252Z`. Overall: **INCOMPLETE (pending G33-8)**. A good PR-AUC is not an acceptance criterion; neither is a script running.

| # | Criterion | Status | Evidence | Note |
|---|---|---|---|---|
| 1 | Protocol finalized before data-dependent experimentation | MET | lock 2026-10-13T15:58:58Z < G33-1 2026-10-13T16:24:05Z |  |
| 2 | Feature schema and conditions verified | MET | conditions_manifest.json counts 23/21/20/16/22; frozen model feature_names_in_ equals C0 (frozen_model_check.json); G33-1/G33-2 PASS |  |
| 3 | Approved conditions and seeds executed | MET | 25 of 25 fit records FITTED; failures.json is empty; G33-4b was interrupted once and resumed with identical settings (ISSUES I-34) |  |
| 4 | Same eligible population for comparable conditions | MET | G33-5a asserts one key set and finite scores for all 25 models; test_keys.npz; population id test_usable_1s:806ab81b786ec704 |  |
| 5 | Trajectory-disjoint splits | MET | G33-1: assert_no_trajectory_overlap and split-manifest equality passed; counts reconcile with the record |  |
| 6 | Threshold selection uses no test labels | MET | all 25 thresholds were written before the test-scoring gate; fitting gates load only the train and validation panels; fit function has no test argument (tested) |  |
| 7 | Primary contrasts computed correctly | MET | independent scikit-learn recomputation: point estimates and per-seed deltas differ by 0.0; 40 real bootstrap replicates of 25 score vectors differ by 3.3e-16 |  |
| 8 | Uncertainty reported and interpreted correctly | MET | seed variability and bootstrap intervals in separate blocks; wording rules applied by code; D1 and D2: no difference demonstrated; no equivalence or negligible claim |  |
| 9 | Failures and undefined metrics preserved and disclosed | MET | failures.json []; undefined replicates {}; interruption disclosed (I-34) |  |
| 10 | Frozen model and historical results unchanged | MET | frozen model 707d4c61a791..., Phase 3 protocol, Item 33 protocol, 79/79 baseline hashes; main, credibility-v1.1, pre-clean-history-backup refs unchanged |  |
| 11 | Tests pass with their actual scope reported | MET | 162 passed, 6 skipped (synthetic_fit group excluded) in the repository and in the execution tree; synthetic data only; no real-data path of the driver is covered by tests |  |
| 12 | Provenance sufficient to understand what ran | MET | environment.json, freeze.json, protocol_lock.json, data_provenance.json, audit.json; code that ran = commit c6ad770 plus 6 modified files recorded with hashes | caveat: the modified files are not committed |
| 13 | Exposure and simulation limitations described | MET | REPORT.md sections 0 and 10; REPORT_ADDENDUM.md section D |  |
| 14 | Final consistency audit passes | MET | all programmatic checks above are MET | performed by the assistant that ran the experiment, using an independent code path (scikit-learn) for the numbers; it is not an external review |
| 15 | Final files preserved in the intended repository location | PENDING G33-8 | 6 working-tree changes are uncommitted (run records, 6 changed files); copying into outputs/items33_42/item33/ is done in the working tree only | requires G33-8 authorization |

Minimum remaining work: G33-8 - authorize the commit of the run's small records and of the modified files listed in `audit.json` (`code_provenance`, entries with `committed_in_c6ad770: false`).
