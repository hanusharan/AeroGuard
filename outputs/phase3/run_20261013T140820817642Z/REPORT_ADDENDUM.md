# Addendum to REPORT.md (written after G8; REPORT.md is unchanged)

This file only adds statements that the generated REPORT.md does not contain and records two defects in it.
All numbers are in `metrics_primary.json`, `bootstrap.json`, `equivalence_check.json` and `population.json` of this run.

## Evidence status (PROTOCOL.md section 10)
- **Controlled re-evaluation of previously exposed data. This is NOT a blind or untouched test, and NOT independent replication.**
- The same test trajectories and labels were already used by: the original v0.3 frozen-model evaluation (E0), the v0.3 ablation, the
  `credibility-v1.1` AoA / margin-trend run (E1) and Item 26 (E1). The protocol author read those stored results before designing this study.
- All values in this run are **E2** (newly generated) and were computed on the **regenerated v0.3 copy from Item 26**, not on the original dataset.
- The frozen model's metrics and the AoA rule's metrics on this population equal the stored E0 / E1 values to full printed precision
  (frozen PR-AUC 0.8902774777010881, identical confusion matrix, 73/76 events, median lead 4.72 s; AoA PR-AUC 0.709466351978561, 76/76 events,
  23.4384591631354 false-alarm episodes per eligible hour). That agreement is consistent with the Item 26 reproduction; it is not independent verification.
- The instantaneous model's results are new. The earlier stored Model A (2 s common subset, retrained) is a different population and fit and is not comparable.

## Reading of the results (fixed rules, PROTOCOL.md sections 9.4 and 9.5)
- No practical-significance criterion exists (D10); none was invented. The report makes no claim of practical superiority.
- Primary contrast: PR-AUC(frozen temporal) - PR-AUC(instantaneous Model A) = +0.0148, paired trajectory-bootstrap 95% interval [0.0079, 0.0230] (B = 1000, seed 20261013).
  The interval excludes 0: statistical evidence of a difference under this resampling model. The size is small (about 1.5 PR-AUC points). Practical significance is not assessed.
- This does not show that temporal reasoning caused the difference: the models differ in inputs (23 vs 8), the frozen model was fitted once in the original environment with
  hyperparameters tuned on validation data using temporal features, and the instantaneous model was fitted once here (no seed sweep; the interval reflects test-sampling only).
- Threshold-dependent metrics are at each method's own validation-selected operating point and are NOT matched; they must not be ranked against each other.
- The two-sided AoA variant (run because Q3 = 461 > 0 at G4) has the same threshold and the same confusion matrix as the signed rule on the test population; it is a sensitivity analysis only.
- Event-level numbers rest on 76 events in 57 trajectories (16 of 19 later events share a warning episode with a first event); event-recall intervals near 100% are degenerate.

## Known defects and deviations
1. REPORT.md, section "Paired differences": the first column contains the text "<a> - <b> | <metric>", whose pipe character splits the Markdown table into extra columns
   (values shift one column to the right of their headers). The numbers are correct in `bootstrap.json`. REPORT.md was not edited (outputs are exclusive-create).
2. REPORT.md's Limitations section only refers to PROTOCOL.md for the prior-exposure disclosure; the explicit statement is made above.
3. No gate failed or was re-run. G7 ran once (`g7_started.lock`). No threshold or configuration was changed after any result was seen.
4. Item 30 decision counts: train 1 of 2,443,881 rows differs (exactly at the threshold, the row that defines it), validation 0 of 491,322, test 0 of 538,034.
   This is the expected operator difference (non-strict margin rule vs strict AoA rule), not an independent finding.
