# AeroGuard Item 33 — Control-Input Ablation

**Status: protocol v0.3 LOCKED (SHA-256 `742f55a9cc4e5da0474de84bf40cc6ffcb63a4ed46f12c3d2536ac57b21c4dc7`; lock record `PROTOCOL_LOCK.json`). Gate G33-3 (implementation and synthetic tests) is done. No data was read, no model loaded, trained or scored, and no bootstrap was run on test results. Every later gate (G33-1 onward) is still unauthorized.**

This directory holds the locked protocol, the implementation and the synthetic tests of Item 33. Run outputs go to `outputs/items33_42/item33/run_<UTC>/`, never into historical output locations.

## Question

How much predictive performance (PR-AUC) is lost when current control inputs (`elevator`, `throttle`), and then explicit recent control history (`elevator_change_1s`), are removed from the 23-feature temporal feature set, under the same predefined trajectory-level split?

This is a predictive-information question. It does not establish causal effects, causal independence, or performance on real aircraft. Controls in the simulator are scripted and open-loop.

## Conditions (details and verification in `PROTOCOL.md`)

| Condition | Features | Status |
|---|---|---|
| C0 | all 23 | retrained baseline |
| C1 | C0 minus `elevator`, `throttle` (21) | primary |
| C2 | C1 minus `elevator_change_1s` (20) | primary |
| C3 | C2 minus `dq_dt`, `dV_dt`, `pitch_rate_slope_1s`, `V_slope_1s` (16) | exploratory |
| X1 | C0 minus `elevator_change_1s` (22) | exploratory |

Primary contrasts: Δ1 = PR-AUC(C0) − PR-AUC(C1), Δ2 = PR-AUC(C0) − PR-AUC(C2); secondary C1 − C2 (= Δ2 − Δ1). Primary estimand: the mean over five fixed training seeds (20260817, 20261101, 20261102, 20261103, 20261104) of the paired PR-AUC difference. Uncertainty: paired trajectory bootstrap (B = 1000, seed 20261013, 95% percentile intervals), plus a pre-specified Bonferroni-adjusted sensitivity (m = 2, 1.25th/98.75th percentiles) for the two primary contrasts only. C3 and X1 contrasts are exploratory and unadjusted.

## Uncertainty, dependence and data honesty

- Seed variability (per-seed deltas, mean, median, range, SD) and trajectory-bootstrap uncertainty are different sources of variation. They are reported separately and never merged into one interval; five seeds do not establish generalisation across training randomness.
- The trajectory bootstrap treats test trajectories as exchangeable. Trajectories generated under shared simulator regimes may be more alike than that assumes, so the interval could understate uncertainty. A regime-stratified resampling is run as a pre-specified sensitivity, not as a replacement. A narrow interval is not evidence of generalisation beyond this simulation.
- All data are a regenerated copy (Item 26) with a fixed trajectory split from the tracked manifest and four recorded file hashes. The original v0.3 dataset is absent and no hash of it was found. The test split has been exposed by earlier analyses. Results are neither blind nor independent replication.
- Frozen-model input masking is a separate, descriptive analysis (`analysis_family = frozen_model_masking`). It perturbs the frozen model's inputs and does not measure the same quantity as retrained feature ablation.

## Files

| Path | Content | State |
|---|---|---|
| `PROTOCOL.md` | the protocol (hash-locked; never edited after the lock) | locked |
| `PROTOCOL_LOCK.json` | approval and lock record (hash, UTC time, decisions D1-D5, authorizations granted and not granted) | written |
| `README.md` | this file | current |
| `ISSUES.md` | known issues, risks, resolved inconsistencies | current |
| `src/item33/` | implementation (conditions, guards, population, fitting, bootstrap, summary, operating point, masking, register, report, gated driver) | implemented; exercised only on synthetic data |
| `tests/` | synthetic-fixture tests | 155 pass, 6 `synthetic_fit` tests skipped (excluded, not run) |

PROTOCOL.md section 19 (Approval record) is intentionally left blank so the approved hash is preserved; `PROTOCOL_LOCK.json` is the approval record.

## Running the synthetic tests

From the repository root, with the Phase 3 environment (scikit-learn 1.9.0, pytest):

```
PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -p no:cacheprovider experiments/items33_42/item33/tests
```

Run only this directory. The tests load no research data and no model (an autouse guard makes any such attempt raise), train nothing, and run no bootstrap on test results; the dry run of the gates uses an injected reader, a stand-in forest that does no learning and a stand-in for the frozen model. The `synthetic_fit` group is skipped unless `ITEM33_ALLOW_SYNTHETIC_FIT=1` is set, which requires the researcher's approval.

## What this work does not do

It does not modify the frozen model (`outputs/ml_v03/models/primary_model_D_1s.joblib`), historical results, the paper, Zenodo records, `main` or `credibility-v1.1`. It does not claim independent replication or blind testing: the test split has been exposed by earlier analyses, and all data are a regenerated copy because the original v0.3 dataset is absent.

## Reproducibility notes

- The four data panels, fitted models and score arrays live in temporary scratch storage and are not in Git. Git alone cannot reproduce a run. Their SHA-256 identifiers are in `PROTOCOL.md` §7 and will be recorded in each run's `audit.json`.
- Step-by-step reproduction instructions (`REPRODUCIBILITY.md`) will be generated with the run, from the recorded provenance. They do not exist yet.

## Approval gates

See `PROTOCOL.md` §17. Each gate needs its own explicit authorization; approval of one never implies the next. G33-0 (protocol lock) and G33-3 (implementation and synthetic tests) are done. The next authorization needed is **G33-1**, the data-dependent checks (hash the four panels, read schemas, reconcile population and counts, regime strata sizes, throttle and trim structure, MS1 training medians, and load the frozen model to check its feature names). After that, each of these is separate: freezing (G33-2), the first fit alone (G33-4a), the remaining 24 fits (G33-4b, after cost reconfirmation), test scoring (G33-5a), masking scoring (G33-5b), the test-set bootstrap and analyses (G33-6) and any commit (G33-8).
