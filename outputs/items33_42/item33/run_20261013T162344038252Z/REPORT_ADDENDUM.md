# Item 33 report addendum (generated from the run's machine-readable records)

Run: `run_20261013T162344038252Z`. Protocol SHA-256 `742f55a9cc4e5da0474de84bf40cc6ffcb63a4ed46f12c3d2536ac57b21c4dc7`. Specification hash (frozen at G33-2, before any scoring): `781d7c9e0130167fa4e68e9903621ba56000aaae4730b3143ec42cf9d66b5d46`.

> Evidence category E2: new results on a regenerated copy of previously exposed data. Not blind, not independent replication, not evidence about real aircraft. Observed results, statistical uncertainty, exploratory interpretation and limitations are kept in separate sections below.

## A. Execution record

| Gate | Status | UTC (gate record) | Wall s | CPU s (user+sys) | Peak RSS MB |
|---|---|---|---|---|---|
| G33-1 | PASS | 2026-10-13T16:24:05Z | not captured | not captured | not captured |
| G33-2 | PASS | 2026-10-13T16:25:02Z | not captured | not captured | not captured |
| G33-4a | PASS | 2026-10-13T16:34:09Z | 529.97 | 2027.63 | 3162.5 |
| G33-4b | PASS | 2026-10-13T20:01:16Z | 5105.7 | 19753.2 | 3490 |
| G33-5a | PASS | 2026-10-13T20:01:56Z | 25.767 | 71.9887 | 1130.2 |
| G33-5b | PASS | 2026-10-13T20:02:51Z | 43.108 | 114.442 | 1419.2 |
| G33-6 | PASS | 2026-10-13T20:13:16Z | 619.51 | 614.126 | 1183.6 |

G33-4b ran as two invocations of the same gate with identical code paths, parameters and seeds (ISSUES I-34): the first was stopped by the background-job time limit after the fits recorded as kept in `fit_progress.json`, the second (resumed) invocation hash-verified and kept them and fitted the rest. Fitted in the resumed invocation: 10; kept from the first invocation (besides the G33-4a fit): 14; failed fits: 0. Resource data for the interrupted first invocation were not captured (the job was killed).

### Fits (all 25 condition-by-seed pairs)

| Condition | Seed | Features | Validation-selected threshold | Validation F1 | Fit s | max_features | Model SHA-256 |
|---|---|---|---|---|---|---|---|
| C0 | 20260817 | 23 | 0.8609993568 | 0.83408593 | 519.03 | 4 | `25a442a761b74fa0…` |
| C1 | 20260817 | 21 | 0.8574409434 | 0.83088054 | 534.28 | 4 | `b3d3a71910b784e1…` |
| C2 | 20260817 | 20 | 0.8668248314 | 0.83600964 | 547.96 | 4 | `40be74659e307b03…` |
| C3 | 20260817 | 16 | 0.8581080345 | 0.82655076 | 527.43 | 4 | `c2bfbb7b3b705f44…` |
| X1 | 20260817 | 22 | 0.8612278062 | 0.82996558 | 513.35 | 4 | `69115255d4e751cc…` |
| C0 | 20261101 | 23 | 0.8610331602 | 0.83488561 | 505.94 | 4 | `3db7aa3ba1125af8…` |
| C1 | 20261101 | 21 | 0.7945971273 | 0.81901734 | 518.82 | 4 | `3084a9a125ccd037…` |
| C2 | 20261101 | 20 | 0.8649335665 | 0.83215166 | 531.99 | 4 | `c84c0752ec9dc340…` |
| C3 | 20261101 | 16 | 0.8612778589 | 0.83194588 | 530.29 | 4 | `a72661d51ac6264f…` |
| X1 | 20261101 | 22 | 0.8543847337 | 0.82865779 | 474.72 | 4 | `9978b524f2fc0493…` |
| C0 | 20261102 | 23 | 0.8570144471 | 0.83206342 | 458.57 | 4 | `d27c0a61996e0e7c…` |
| C1 | 20261102 | 21 | 0.819810746 | 0.81811196 | 460.94 | 4 | `ef72bc0cf422836f…` |
| C2 | 20261102 | 20 | 0.8608156222 | 0.82257645 | 485.37 | 4 | `df757987e4bfd698…` |
| C3 | 20261102 | 16 | 0.8596129982 | 0.82616279 | 476.31 | 4 | `342a4e6bd35b7f11…` |
| X1 | 20261102 | 22 | 0.8592210142 | 0.82876191 | 468.99 | 4 | `8342b5fe0b849229…` |
| C0 | 20261103 | 23 | 0.8644075427 | 0.83285081 | 503.82 | 4 | `62857ad2990a28d7…` |
| C1 | 20261103 | 21 | 0.858145908 | 0.82440248 | 525.04 | 4 | `e65ca10917577b89…` |
| C2 | 20261103 | 20 | 0.7923365127 | 0.82130699 | 535.13 | 4 | `c6434e8ca804d7e5…` |
| C3 | 20261103 | 16 | 0.8579207464 | 0.83121948 | 530.43 | 4 | `1d2700d436f8eda2…` |
| X1 | 20261103 | 22 | 0.8661348229 | 0.83382534 | 508.89 | 4 | `401f3cd716509127…` |
| C0 | 20261104 | 23 | 0.8690789216 | 0.83577681 | 483.59 | 4 | `65dbd3ff810c53ce…` |
| C1 | 20261104 | 21 | 0.8599065458 | 0.8293904 | 512.92 | 4 | `cf3614f5341623d1…` |
| C2 | 20261104 | 20 | 0.8589452157 | 0.82615547 | 505.75 | 4 | `6e89dd39368e30b0…` |
| C3 | 20261104 | 16 | 0.8619344519 | 0.83029107 | 495.14 | 4 | `f5838485261ca5b4…` |
| X1 | 20261104 | 22 | 0.8625308885 | 0.83424051 | 462.27 | 4 | `39f152b5526540e4…` |

(The full model hashes are in `audit.json`. Several fits selected a visibly lower threshold than their siblings - for example C1 at seed 20261101 and C2 at seed 20261103 - which affects threshold-dependent metrics but not PR-AUC.)

## B. Observed results (statistical uncertainty stated alongside)

### B1. Primary contrasts (retrained feature ablation; PR-AUC; seed-mean estimand)

- **D1 = PR-AUC(C0) - PR-AUC(C1)**: seed-mean 0.00019292, median -9.21098e-05; trajectory-bootstrap 95% interval [-0.00389957, 0.00355389] (B=1000, seed 20261013, undefined replicates 0); Bonferroni-adjusted (m=2) interval [-0.00455631, 0.00400295]. Seed variability (descriptive): per-seed deltas range -0.000726828 to 0.00100895, SD 0.000760502; same sign for every seed: False.
- **D2 = PR-AUC(C0) - PR-AUC(C2)**: seed-mean 0.000519249, median 0.000523785; trajectory-bootstrap 95% interval [-0.00360436, 0.00408731] (B=1000, seed 20261013, undefined replicates 0); Bonferroni-adjusted (m=2) interval [-0.00435214, 0.0045776]. Seed variability (descriptive): per-seed deltas range -0.000603481 to 0.00193642, SD 0.000927227; same sign for every seed: False.

Under the protocol's wording rules: for D1 and D2 **no difference was demonstrated** (both intervals include 0, and the per-seed deltas have mixed signs). The across-seed SD of the deltas is larger than the seed-mean delta in both cases, so at five seeds these differences are not separable from training noise. No meaningful-effect margin was specified, so this report does **not** declare the conditions equivalent or the effect negligible.

### B2. Secondary and exploratory contrasts

- C1 - C2 (secondary): seed-mean 0.000326329, interval [-0.000374327, 0.000972861], per-seed range -0.000431319 to 0.00134699.
- C0 - C3 (exploratory, unadjusted): seed-mean 0.00211605, interval [-0.00180349, 0.00572954]; all five per-seed deltas are positive (0.000849056 to 0.00421655); the interval for the seed mean includes 0. In the single-seed view, seed 20261101 has an unadjusted interval that excludes 0 ([0.000237758, 0.00801888]); with five seeds, two primary contrasts and several exploratory ones, that single interval is not evidence of an effect.
- C0 - X1 (exploratory, unadjusted): seed-mean 0.000102092, interval [-0.00100513, 0.00104762], per-seed range -0.000364838 to 0.000711862.

PR-AUC by condition across the five seeds (descriptive spread, not an interval): C0 mean 0.8909057 (min 0.8904915, max 0.8916254, SD 0.0004444); C1 mean 0.8907128 (min 0.8900629, max 0.8914402, SD 0.0004914); C2 mean 0.8903865 (min 0.889689, max 0.891095, SD 0.0005283); C3 mean 0.8887897 (min 0.8874089, max 0.8896425, SD 0.0008711); X1 mean 0.8908037 (min 0.8897797, max 0.8919903, SD 0.0008814).

### B3. Sensitivity analyses

- Regime-stratified resampling, D1: [-0.00399123, 0.00337306] versus the primary [-0.00389957, 0.00355389]; both include 0: True. Test strata (usable trajectories): gradual_approach_v3 346, normal 81, stall 29.
- Regime-stratified resampling, D2: [-0.00381647, 0.00375816] versus the primary [-0.00360436, 0.00408731]; both include 0: True. Test strata (usable trajectories): gradual_approach_v3 346, normal 81, stall 29.

### B4. Reproduction diagnostic (C0 at seed 20260817 versus the frozen model's stored scores)

Level **R1**: scores are not bit-identical (max absolute difference 0.0702948); PR-AUC(C0) - PR-AUC(frozen) = 0.000435902, interval [-0.000417944, 0.00158958] includes 0; the validation-selected threshold differs by 0.0024459. This is a reported discrepancy, not a failure: C0 is a retrained model (scikit-learn 1.9.0; the frozen model's fitting environment is unrecorded). The comparisons D1 and D2 are among retrained models and do not depend on it.

### B5. Descriptive threshold-dependent test metrics (each model at its own validation-selected threshold, and at the validation-matched operating point)

Differences here mix ranking quality with threshold position and carry no hypothesis test. Event metrics use the existing definitions (76 events in 57 trajectories; lead time capped at 5 s).

| Condition | Seed | Threshold | Precision | Recall | F1 | Events warned | Median lead s | | Matched threshold | Precision | Recall | F1 | Events warned |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C0 | 20260817 | 0.860999 | 0.9344 | 0.7336 | 0.8219 | 73/76 | 4.72 | | 0.860562 | 0.9343 | 0.7338 | 0.822 | 73/76 |
| C1 | 20260817 | 0.857441 | 0.9455 | 0.7309 | 0.8244 | 73/76 | 4.72 | | 0.853236 | 0.9307 | 0.7375 | 0.8229 | 73/76 |
| C2 | 20260817 | 0.866825 | 0.9459 | 0.7174 | 0.8159 | 73/76 | 4.68 | | 0.86029 | 0.9423 | 0.7295 | 0.8224 | 73/76 |
| C3 | 20260817 | 0.858108 | 0.9457 | 0.7268 | 0.8219 | 73/76 | 4.71 | | 0.85907 | 0.9458 | 0.7264 | 0.8217 | 73/76 |
| X1 | 20260817 | 0.861228 | 0.9565 | 0.7308 | 0.8286 | 73/76 | 4.68 | | 0.860553 | 0.9564 | 0.7311 | 0.8287 | 73/76 |
| C0 | 20261101 | 0.861033 | 0.9364 | 0.7338 | 0.8228 | 74/76 | 4.675 | | 0.861023 | 0.9364 | 0.7338 | 0.8228 | 74/76 |
| C1 | 20261101 | 0.794597 | 0.8645 | 0.7627 | 0.8104 | 76/76 | 4.775 | | 0.856927 | 0.9421 | 0.7282 | 0.8214 | 73/76 |
| C2 | 20261101 | 0.864934 | 0.9449 | 0.7241 | 0.8199 | 73/76 | 4.68 | | 0.859681 | 0.9446 | 0.7266 | 0.8214 | 73/76 |
| C3 | 20261101 | 0.861278 | 0.9567 | 0.7247 | 0.8247 | 75/76 | 4.67 | | 0.861277 | 0.9567 | 0.7247 | 0.8247 | 75/76 |
| X1 | 20261101 | 0.854385 | 0.9207 | 0.7351 | 0.8175 | 73/76 | 4.73 | | 0.862843 | 0.9423 | 0.7316 | 0.8237 | 73/76 |
| C0 | 20261102 | 0.857014 | 0.9354 | 0.7341 | 0.8226 | 73/76 | 4.73 | | 0.857014 | 0.9354 | 0.7341 | 0.8226 | 73/76 |
| C1 | 20261102 | 0.819811 | 0.8694 | 0.751 | 0.8059 | 75/76 | 4.77 | | 0.864059 | 0.9559 | 0.7262 | 0.8254 | 73/76 |
| C2 | 20261102 | 0.860816 | 0.9449 | 0.7293 | 0.8232 | 73/76 | 4.69 | | 0.863745 | 0.945 | 0.7275 | 0.8221 | 73/76 |
| C3 | 20261102 | 0.859613 | 0.9562 | 0.7265 | 0.8257 | 73/76 | 4.7 | | 0.861412 | 0.9565 | 0.7259 | 0.8254 | 73/76 |
| X1 | 20261102 | 0.859221 | 0.9343 | 0.7319 | 0.8208 | 73/76 | 4.68 | | 0.869097 | 0.9577 | 0.7276 | 0.827 | 73/76 |
| C0 | 20261103 | 0.864408 | 0.9573 | 0.7333 | 0.8305 | 73/76 | 4.68 | | 0.864403 | 0.9573 | 0.7333 | 0.8305 | 73/76 |
| C1 | 20261103 | 0.858146 | 0.9431 | 0.7304 | 0.8232 | 73/76 | 4.73 | | 0.860141 | 0.9517 | 0.7296 | 0.826 | 73/76 |
| C2 | 20261103 | 0.792337 | 0.865 | 0.7632 | 0.811 | 76/76 | 4.75 | | 0.863853 | 0.9559 | 0.7282 | 0.8266 | 73/76 |
| C3 | 20261103 | 0.857921 | 0.9564 | 0.7271 | 0.8261 | 74/76 | 4.73 | | 0.861157 | 0.9566 | 0.7259 | 0.8255 | 74/76 |
| X1 | 20261103 | 0.866135 | 0.9576 | 0.7277 | 0.827 | 73/76 | 4.69 | | 0.868146 | 0.9577 | 0.7271 | 0.8266 | 73/76 |
| C0 | 20261104 | 0.869079 | 0.9474 | 0.7288 | 0.8238 | 73/76 | 4.7 | | 0.868997 | 0.9474 | 0.7288 | 0.8238 | 73/76 |
| C1 | 20261104 | 0.859907 | 0.9432 | 0.7302 | 0.8231 | 74/76 | 4.695 | | 0.863604 | 0.9433 | 0.7283 | 0.822 | 73/76 |
| C2 | 20261104 | 0.858945 | 0.9423 | 0.7299 | 0.8226 | 73/76 | 4.71 | | 0.866929 | 0.9645 | 0.7266 | 0.8288 | 73/76 |
| C3 | 20261104 | 0.861934 | 0.9567 | 0.7252 | 0.8251 | 75/76 | 4.68 | | 0.864442 | 0.9571 | 0.7241 | 0.8245 | 75/76 |
| X1 | 20261104 | 0.862531 | 0.9463 | 0.7319 | 0.8254 | 73/76 | 4.68 | | 0.871237 | 0.9564 | 0.7285 | 0.827 | 73/76 |

Event-level trajectory-bootstrap intervals (seed 20260817 only): event recall C0 own 0.9605 [0.9091, 1]; C1 matched 0.9605 [0.9091, 1]; C1 own 0.9605 [0.9091, 1]; C2 matched 0.9605 [0.9091, 1]; C2 own 0.9605 [0.9091, 1]. With 76 events in 57 trajectories, and a recall near 96%, these intervals are very wide and degenerate near 100%.

### B6. Frozen-model input masking (separate analysis family: frozen_model_masking)

Unmasked comparator: the frozen model re-scored in this run, PR-AUC 0.890277477701 (identical to the stored original value and to the Phase 3 re-score). Changes in PR-AUC with 95% trajectory-bootstrap intervals (unadjusted; first permutation draw only for MS2/MS3; the other four draws are listed in REPORT.md):

| Variant | PR-AUC change | Interval | Precision at the frozen threshold | Recall at the frozen threshold |
|---|---|---|---|---|
| M-A-MS1 | -0.046427 | [-0.074632, -0.024053] | 0.9995 | 0.1351 |
| M-A-MS2-20261201 | -0.081286 | [-0.10821, -0.062443] | 0.9939 | 0.2345 |
| M-A-MS3-20261201 | -0.015869 | [-0.030509, -0.0029877] | 0.9469 | 0.5164 |
| M-B-MS1 | -0.01611 | [-0.026413, -0.0084708] | 0.9413 | 0.6063 |
| M-B-MS2-20261201 | -0.013555 | [-0.02113, -0.0077282] | 0.9562 | 0.6246 |
| M-B-MS3-20261201 | -0.010757 | [-0.017712, -0.0054223] | 0.9549 | 0.6324 |
| M-C-MS1 | -0.072258 | [-0.11079, -0.043159] | 0.9997 | 0.1332 |
| M-C-MS2-20261201 | -0.10396 | [-0.13615, -0.080912] | 0.995 | 0.2228 |
| M-C-MS3-20261201 | -0.026158 | [-0.043894, -0.010933] | 0.9509 | 0.4611 |

MS1 = training-median constant, MS2 = global permutation, MS3 = within-trajectory permutation; M-A = elevator and throttle, M-B = elevator_change_1s, M-C = all three. Derived columns were not recomputed after replacement.

## C. Exploratory interpretation (hypotheses; none was tested by this run)

1. **Retrained models do not lose measurable PR-AUC when controls are withheld.** In this simulator the remaining features include the angle of attack and its short-history statistics and derivatives, which describe the approach to the stall boundary directly. State variables integrate the scripted past controls, so control information can remain in the state features (the protocol's C3 removed only four named proxies, and C0 - C3 still shows no demonstrated difference). The data cannot distinguish 'controls carry no extra information' from 'the same information is available elsewhere'.
2. **The frozen model's reliance is large, the retrained models' need is not.** Masking the frozen model's control inputs lowers its PR-AUC substantially (largest for global permutation, smallest for within-trajectory permutation), while retrained models without those inputs perform about as well as with them. These are different quantities: masking measures sensitivity of one fitted function to out-of-distribution, physically inconsistent inputs (derived columns such as elevator_change_1s, dq_dt and dV_dt were not recomputed, so the masked rows contradict the equations of motion); retraining lets the forest rely on other features. The two results are not contradictory and are not combined.
3. **Throttle can identify trajectories in training.** 1840 of 2118 training trajectories (86.87%) hold throttle constant at a value no other trajectory shares (1840 distinct values), and 184 hold elevator constant. A forest could in principle exploit such a fingerprint during training; test trajectories carry unseen values, and removing throttle produced no detectable change in test PR-AUC. This run provides no evidence that a fingerprint helped on test; it does not rule out an effect on training fit.
4. **Open-loop, scripted controls.** Controls in the simulator are scripted time functions and do not respond to the aircraft's state; in the dominant regime the stall is produced by the scripted elevator pulse itself. Statements about 'dependence on controls' therefore concern predictive information in this generator, not how a pilot-in-the-loop system would behave.
5. **No causal reading.** Feature ablation shows how much predictive information a model family loses, not a causal effect of the controls, not causal independence, and not performance on real aircraft.

## D. Discrepancies, deviations and what could not be concluded

- Reproduction diagnostic level R1 (section B4).
- G33-4b was interrupted by the background-job time limit and resumed (section A; ISSUES I-34).
- The bootstrap metric computation was changed after the preservation commit from per-replicate scikit-learn calls to an equivalent pre-sorted weighted computation (ISSUES I-33). Equivalence checks: scikit-learn recomputation of all 50 point estimates agrees to 0; per-seed deltas, means and medians agree to 0; the first 40 bootstrap replicates of all 25 score vectors agree with scikit-learn to 3.33e-16 (in-run check: 2.22e-16 over 2 replicates).
- The locked protocol's register (SEC-3) asks for seed-averaged ROC-AUC contrasts for all seeds while its cost estimate counts ROC-AUC only for seed 20260817 (ISSUES I-27); the register was followed.
- The `synthetic_fit` test group was not run (it was excluded at G33-3 and not re-authorized).
- Not concluded: any equivalence or negligible effect (no margin was specified); any effect of controls beyond what five seeds and 456 test trajectories can resolve; generalisation to other regimes, designs, aircraft or real flights.
- Limitations: original v0.3 dataset absent and the regenerated copy not shown byte-identical; previously exposed test split; trajectories may share regime or generator dependencies the bootstrap does not model; one train/validation/test split; five seeds sample one source of randomness; hyperparameters were not retuned per condition; simulation only.

