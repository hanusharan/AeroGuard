# AeroGuard Item 33 — Control-Input Ablation

**Status: INCOMPLETE - one gate remains, G33-8 (preservation of the results and of the post-commit code changes), which needs its own authorization. The protocol is locked (SHA-256 `742f55a9cc4e5da0474de84bf40cc6ffcb63a4ed46f12c3d2536ac57b21c4dc7`). Gates G33-1, G33-2, G33-4a, G33-4b, G33-5a, G33-5b and G33-6 were executed on the real panels and passed (run `run_20261013T162344038252Z`, 25 of 25 fits, no failed fit), and the G33-7 audit was performed. Commit `c6ad770d77d5d9ba2378aaaeb18df701bc3c0a74` holds the protocol and the implementation as first written; the run records and five later code/document changes are in the working tree, not committed.**

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

## Result summary (full detail and qualifications in the run's `REPORT.md` and `REPORT_ADDENDUM.md`)

Seed-mean PR-AUC differences on the 538,034-row test population, with 95% trajectory-bootstrap intervals (B = 1000): D1 = C0 - C1 = 0.000193 [-0.00390, 0.00355]; D2 = C0 - C2 = 0.000519 [-0.00360, 0.00409]. Both intervals include 0 and per-seed deltas have mixed signs: no difference was demonstrated under the protocol. No meaningful-effect margin was specified, so no equivalence or negligible effect is claimed. Exploratory: C0 - C3 = 0.00212 [-0.00180, 0.00573]; C0 - X1 = 0.000102 [-0.00101, 0.00105]. Frozen-model input masking (a separate analysis) lowered the frozen model's PR-AUC by 0.010 to 0.105 depending on the masked set and method. Reproduction level R1: the retrained C0 is not bit-identical to the frozen model, and their PR-AUC difference interval includes 0.

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
| `src/item33/` | implementation (conditions, guards, population, fitting, bootstrap, summary, operating point, masking, register, report, gated driver) | committed in `c6ad770`; `bootstrap.py` and `driver.py` were modified afterwards (ISSUES I-33, I-34) and used for the run |
| `tests/` | synthetic-fixture tests | 162 pass, 6 `synthetic_fit` tests skipped (excluded, not run) |

| `../../../outputs/items33_42/item33/run_20261013T162344038252Z/` | small run records, `REPORT.md`, `REPORT_ADDENDUM.md`, `ACCEPTANCE_CHECKLIST.md`, `REPRODUCIBILITY.md`, `audit.json`, logs (copied from the scratch execution tree; **untracked**) | written; models, score arrays and replicate arrays are scratch only |

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

See `PROTOCOL.md` §17. Each gate needs its own explicit authorization. Gates G33-0 to G33-7 are done (G33-1, G33-2, G33-4a/4b, G33-5a/5b, G33-6 executed; G33-7 audit performed). **Remaining: G33-8** - commit the small run records and the five post-commit file changes. Until then the exact code that produced the results exists only in the working tree and in the scratch execution tree.
