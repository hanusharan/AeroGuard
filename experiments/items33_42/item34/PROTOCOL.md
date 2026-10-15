# AeroGuard Item 34 — Temporal control-input effects (pre-specified before any Item 34 number was computed)

**Question.** Does explicit control history at a second time scale add predictive information beyond the 23-feature model (Item 33 C0)?

- **Conditions.**
  - T0 = Item 33 C0: 23 features, 5 seeds. The stored test scores, thresholds and hashes are reused; nothing is refitted.
  - T1 = C0 + `elevator_change_0.5s`: 24 features, with the same 5 seeds (20260817, 20261101–20261104).
  - `elevator_change_2s` is not used: it is missing for the rows with less than 2 s of history (210,099 training rows), and the existing leakage guard refuses missing values. Throttle history is not added: throttle is constant within 1,840 of 2,118 training trajectories (Item 33).
- **Fitting.** Same as Item 33:
  - the frozen random-forest parameters;
  - the training and validation populations;
  - `ml.temporal_experiment.get_xy`;
  - `ml.calibration.select_threshold_train_then_val`;
  - strict `>`.

  The test data are scored once per fitted model.
- **Primary estimand.** D34 = PR-AUC(T1) − PR-AUC(T0), averaged over the 5 seeds and paired by seed. The population is the common test population (538,034 rows, key hash `806ab81b…`).
- **Uncertainty.**
  - Paired trajectory bootstrap: B = 1000, seed 20261013, 95% percentile interval. The same trajectory draws are used for every model.
  - Per-seed deltas and their spread are reported separately from the bootstrap interval.
- **Secondary (descriptive).** For each seed, at each model's own threshold:
  - ROC-AUC;
  - false-warning episodes per simulated hour;
  - coverage at 2 s and 4 s (the Items 37–39 definitions).
- **Reading rule.**
  - If the interval includes 0, the result is "no difference demonstrated". This is not evidence that there is no effect: no margin is defined, so no equivalence or negligible-effect claim is made.
  - If the interval excludes 0, it is reported as a difference in predictive information under this resampling model. That says nothing about causation or real aircraft.
- **Evidence.** E2 on previously exposed test data from a regenerated copy. It is not blind and not independent replication, and it is simulation only. The frozen model and all historical results are untouched.
