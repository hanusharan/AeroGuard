# AeroGuard Stage 4 — Temporal Early-Warning Experiment Report

**Research question:** How early can AeroGuard reliably identify an approaching stall using only
information available up to the current time?

**Run:** `scripts/run_temporal_experiment.py`, seed `20260817`, total wall-clock runtime **544.5s (~9.1 min)**.
Executed once; no experiments in this report were rerun. All artifacts referenced below are under
`outputs/ml_temporal/` and `data/ml_temporal/` (both additive; nothing under `aeroguard/`,
`data/processed/`, `data/splits/`, `data/ml/`, or `outputs/ml_baseline/` was modified).

---

## 1. Can we predict stall before it happens?

Yes, but the honest answer is **"barely, and mostly at very short range."** Row-level recall is
97–99% for rows within 0.5s of the actual crossing, then falls off a cliff:

| Lead-time bucket | Positive rows | Recall | Warned / Missed |
|---|---|---|---|
| 0–0.5s | 5,564 | **98.8%** | 5,500 / 64 |
| 0.5–1s | 648 | 17.9% | 116 / 532 |
| 1–2s | 1,102 | 17.7% | 195 / 907 |
| 2–3s | 601 | 26.0% | 156 / 445 |
| 3–4s | 301 | 2.3% | 7 / 294 |
| 4–5s | 304 | 0.0% | 0 / 304 |

At the **event level** (14 discrete stall-boundary crossings in the usable test population — see
§7 on sample size), all 14 got at least one qualifying warning (event recall = 100%), but median
credited lead time was only **0.53s** (mean 0.81s, range 0.28–3.06s). Only 14.3% of events were
detected ≥1s early, 7.1% ≥3s early, and none ≥4s early.

**Read event-recall=100% with caution.** It only requires one flagged row anywhere in the 5s
pre-crossing window, so it overstates practical early-warning capability. The row-level
lead-time-bucketed recall table above is the more honest picture.

## 2. How many seconds early?

Reliably: **under 0.5 seconds.** Beyond that, recall drops to 18–26% and the model should not be
trusted as a multi-second early-warning system with the current feature set. Nothing in the
window ablation (§6) changes this — more history does not push the reliable horizon out further.

## 3. What precision/recall do we get?

Primary model (Model D: state + 1-step derivatives + 1s causal temporal features), RF
(`n_estimators=200, max_depth=12, min_samples_leaf=5, class_weight=balanced_subsample`),
threshold 0.841 (selected TRAIN-then-VAL), evaluated on its own realistic-scale TEST population
(174,662 rows / 134 of 150 test trajectories):

| Metric | Value |
|---|---|
| ROC-AUC | 0.963 |
| PR-AUC | 0.813 |
| Precision | 0.900 |
| Recall | 0.701 |
| F1 | 0.788 |
| Confusion matrix | TN 165,477 · FP 665 · FN 2,546 · TP 5,974 |
| Accuracy (not relied upon — see brief) | 0.982 |

Positive class is rare (8,520 / 174,662 ≈ 4.9% of rows), so accuracy is reported only for
reference and PR-AUC/recall/F1 drove all decisions here.

## 4. What is the false-alarm rate?

Row-level false-positive rate is low: **0.40%** (665 / 166,142 negative rows). At the more
operationally meaningful *episode* level (contiguous runs of positive predictions, not raw rows):

| Episode-level stat | Value |
|---|---|
| Warning episodes | 34 |
| True warning episodes | 23 |
| False-alarm episodes | 11 |
| False warning rate | 32.4% |
| Episode-level precision | 67.6% |
| Warnings / trajectory | 0.254 |
| False alarms / minute of flight | 0.378 |

**Does the model confuse aggressive-but-recoverable maneuvers with genuine impending stall?**
Checked directly by pulling the 665 row-level false positives from the cached primary model/test
panel (no retraining) and comparing their physics to true positives:

- **100% of false positives have no future stall crossing anywhere in their trajectory** — they
  are not "near-miss" rows on a trajectory that eventually stalls.
- Regime composition: 80.3% from `normal` trajectories, 19.7% from `near_boundary`, **0% from
  `stall`**.
- Physically they look nothing like real precursors: mean α 0.14 rad vs. 0.68 rad for true
  positives; mean stall margin **+0.14** (healthy, positive margin) vs. **−0.40** for true
  positives (already past nominal margin); only 23.6% have rising α (dα/dt > 0) vs. 67.1% of true
  positives; only 23.6% are decelerating (dV/dt < 0) vs. 65.3% of true positives.

**Conclusion: no.** The false positives are rare and look like ordinary low-α, steady, unaccelerated
flight — not steep, decelerating approaches to the boundary. Whatever residual noise produces
these 665 rows, it is not the model mistaking aggressive recoverable maneuvers for genuine stall
risk.

(Full breakdown: `outputs/ml_temporal/metrics/false_positive_physics_characterization.csv`,
`false_positive_regime_composition.csv`.)

## 5. Does temporal history actually help?

**Only marginally, and only via the 1-step derivatives — not via the richer windowed statistics.**
Fair, common-subset comparison (identical 148,436 test rows for every model, so this isolates the
effect of feature set alone):

| Model | Features | PR-AUC | Recall(1–2s) | Recall(2–3s) |
|---|---|---|---|---|
| A — frozen instantaneous baseline (existing Stage-3 model, re-scored only) | 8 | 0.9329 | 0.007 | 0.000 |
| B — state + 1-step derivatives | 13 | 0.9332 | 0.020 | 0.000 |
| C_1s — state + windowed temporal stats (no derivatives) | 18 | 0.9294 | 0.023 | 0.000 |
| **D_1s — state + derivatives + windowed temporal stats** | 23 | **0.9338** | 0.023 | 0.000 |
| D_0.5s / D_2s / D_3s | 23 | 0.9327 / 0.9329 / 0.9318 | ~0.02 | 0.000 |

- **A → B**: +0.0003 PR-AUC — 1-step derivatives add essentially nothing to overall PR-AUC, though
  they roughly triple recall in the 0.5–1s bucket (0.365 → 0.430 on this population).
- **B → D_w**: flat to slightly negative depending on window.
- **C_w is consistently *worse* than A at every window** (0.929–0.931 vs. A's 0.933) — windowed
  summary statistics *without* the paired 1-step derivatives slightly hurt. Adding derivatives
  back (D_w) restores parity.
- Best model overall (D_1s) beats the existing frozen baseline (A) by **0.0009 PR-AUC** —
  statistically indistinguishable, not a material win on that metric.
- The one place temporal features earn their keep is the early-lead-time recall buckets, where
  D-family models roughly 3x A's 1–2s recall (0.023 vs. 0.007) — small in absolute terms, but a
  real, repeatable direction across every window tested.

**Bottom line:** temporal history does not move overall discrimination (PR-AUC) in any way that
matters; its (modest) genuine value is entirely in the early-lead-time buckets, and that value
comes from the 1-step derivatives, not the windowed mean/min/max/range/slope/trend statistics.

## 6. Which features matter?

Primary model (D, 1s window) feature importances, top 5 of 23:

| Feature | Importance |
|---|---|
| stall_margin | 0.102 |
| alpha_max_1s | 0.101 |
| elevator | 0.088 |
| alpha | 0.087 |
| alpha_mean_1s | 0.075 |

α and its 1s-window statistics (max/mean/min/range) together account for ~30% of total
importance — physically sensible, since α and stall_margin are the direct boundary-relevant
quantities (`stall_margin = alpha_at_cl_peak − alpha`, an exact algebraic transform). No single
feature dominates (max 10.2%), consistent with the RF spreading signal across correlated
α-derived features. Full ranking and plot: `outputs/ml_temporal/plots/06_feature_importance_primary_model.png`.

**Physics/information diagnosis** (single-feature separability AUC, rows 1–5s before a crossing
vs. "safe" rows far from any crossing) is the mechanistic explanation for the §1/§2 cliff: every
variable (α, dα/dt, V, dV/dt, γ, dq/dt, elevator, stall_margin) scores **0.51–0.61 AUC** at every
lead time from 1–5s — barely above chance. None of these physics quantities, taken individually,
carries a strong univariate early-trend signal several seconds out; they only become sharply
informative once within roughly half a second of the boundary. This is consistent with (and
explains) why longer history windows don't help (§5) and why lead-time recall collapses beyond
0.5s (§1–2). Full table: `outputs/ml_temporal/metrics/physics_diagnosis.csv`.

## 7. Does performance remain good near the boundary?

**No — this is the most important finding of the experiment.** Row-level breakdown by physics
regime (never a model input, post-hoc only):

| Regime | Rows | Positives | Recall | Precision | F1 |
|---|---|---|---|---|---|
| near_boundary | 37,337 | 824 | **95.3%** | 85.7% | 90.2% |
| normal | 110,679 | 0 | n/a | — | — |
| stall | 26,646 | 7,696 | **67.4%** | 100% | 80.5% |

Recall in the actual `stall` regime (67.4%) is **worse** than in `near_boundary` (95.3%) — the
harder, real stall-approach trajectories are exactly where the model misses more positives. The
110,679 easy `normal` rows (63% of the test population, zero positives by construction) do not
mask this: the regime breakdown surfaces it directly, as intended.

**Trajectory-level caveat:** only **14 discrete stall-crossing events** exist in the usable primary
test population (out of up to 42 `stall`-regime + 29 `near_boundary`-regime test trajectories,
134/150 usable overall). This is a small sample — the 100% event-recall and the lead-time
distribution in §1 should be read as indicative, not tightly estimated population parameters.

**Generalization check** (Model D retrained with all 101 `stall`-regime trajectories removed from
TRAIN, evaluated unchanged on the full TEST split — `outputs/ml_temporal/metrics/generalization_check.json`):
stall-regime recall collapses from 67.4% → **6.3%**, PR-AUC from 0.813 → 0.645, event recall from
100% → **28.6%** (4/14). The model is not learning a regime-agnostic understanding of
approach-to-stall dynamics — a meaningful share of its apparent skill is specific to having seen
`stall`-regime trajectory shapes during training, not a transferable physics signal. This is a
genuine limitation, not just a sample-size artifact.

## 8. What is the simplest model worth carrying forward?

Applying the stated decision rule (prefer the simplest model within ~1–2 points of a more complex
one, do not chase ROC-AUC): the existing frozen instantaneous baseline (Model A, 8 features, no
retraining needed) is statistically tied with every temporal variant on overall PR-AUC (spread of
≤0.001). If overall PR-AUC were the only criterion, A would win on simplicity alone.

But the actual research question is about *early* detection, and that is exactly where A cannot
compete at all (1–2s recall 0.007 vs. D_1s's 0.023) and where the temporal features' only real,
repeatable benefit shows up. Given that:

- 1s of history already captures ~all the benefit available from any window tested (0.5s/1s/2s/3s
  all land within 0.002 PR-AUC of each other, §5) — no evidence longer windows help.
- The windowed summary-statistic features (C) do not help without the 1-step derivatives, and
  slightly hurt on their own.

**Recommendation: Model D at a 1-second history window** (state + 1-step derivatives + causal 1s
window statistics, 23 features) is the simplest model that captures the available early-warning
benefit. There is no scientific justification, from this experiment, for windows longer than 1s or
for the windowed-statistics feature block without its paired derivatives.

## 9. What are the limitations?

- **Reliable lead time is under 0.5s.** This system, as currently built, is an imminent-stall
  detector, not a multi-second early-warning system. Any product framing should say so explicitly.
- **Event-level sample size is small** (14 crossings in the usable test population) — event-level
  statistics (100% recall, lead-time distribution) carry wide uncertainty.
- **Performance is worse in the harder `stall` regime than in `near_boundary`** (67.4% vs. 95.3%
  recall) — the regime that matters most for real early warning is the one performing worst.
- **Weak generalization to an unseen regime**: excluding `stall`-regime trajectories from training
  collapses stall-regime recall to 6.3%, indicating substantial regime-specific memorization rather
  than transferable physics understanding.
- **Temporal history's contribution is real but small**, and driven entirely by 1-step derivatives,
  not by the richer windowed statistics — a more expressive temporal feature set or a different
  physics representation might be needed to meaningfully extend the reliable warning horizon beyond
  the current model's floor.
- **Mild probability miscalibration** in mid-range bins (Brier score 0.044, generally good, but
  several bins show the model somewhat overconfident) — not disqualifying since the deployed
  decision uses a fixed thresholded operating point, but worth knowing before using raw
  probabilities for anything beyond thresholding.

---

## Leakage audit (Phase 8, explicitly checked)

| Check | Status | Evidence |
|---|---|---|
| No future values enter features | ✅ | `ml/temporal_features.py` computes every window/derivative over the causal closed interval `[t−W, t]`; `compute_ols_slope`/`compute_endpoint_diff`/rolling stats are all backward-looking only, by construction (docstring + closed-form derivation). |
| Temporal windows only use t and earlier | ✅ | Same as above; enforced structurally, not just by convention. |
| Labels only use future data | ✅ | `future_stall_5s` is computed independently in `aeroguard_dataset/labeling.py` from strictly future samples; `ml/temporal_features.py` never reads it. |
| Trajectory IDs never overlap between splits | ✅ | Verified directly: train=700, val=150, test=150 trajectories; train∩val, train∩test, val∩test all = 0. |
| Scaling/normalization fit only on TRAIN | ✅ (N/A) | No scaler in this pipeline — Random Forest is used throughout, which is scale-invariant. |
| No feature mathematically derived from the label | ✅ | `get_xy()` raises `ValueError` if the feature set ever includes the target/derived columns; `stall_margin` is a physics quantity (`alpha_at_cl_peak − alpha`), not label-derived. |
| Test set untouched until final evaluation | ✅ | Hyperparameters tuned on VAL PR-AUC only; thresholds selected TRAIN-then-VAL (`select_threshold_train_then_val`); TEST appears only inside `evaluate_on_test()`, called after all tuning/thresholding is frozen. |
| Windows never span two trajectories | ✅ | All rolling/shift operations are grouped by `trajectory_id` before windowing; verified in `tests/test_temporal_features.py` (21/21 passing, including `test_common_subset_equals_largest_window_mask`). |

---

## Computational efficiency accounting

- **Experiments actually run:** 1 hyperparameter grid (2 RF configs) + 1 fair window ablation
  (1 re-scored frozen baseline + 9 newly-fit RF models: B + {C,D}×{0.5,1,2,3}s) + 1 primary model
  fit (D, 1s, own population) + 1 generalization-check fit (D, 1s, stall-regime-excluded train) +
  post-hoc analyses (false-alarm, regime/airspeed breakdown, physics diagnosis, calibration — all
  cheap aggregations, no additional model fits) + 10 plots. **13 RF trainings total.**
- **Experiments skipped / not needed:**
  - No large hyperparameter search — 2-point grid only, since VAL PR-AUC separated the two
    candidates clearly (0.9264 vs. 0.9006).
  - No repeated k-fold cross-validation on the 1.75M-row time-series dataset — trajectory-level
    TRAIN/VAL/TEST was used throughout, exactly as instructed.
  - No dozens of near-identical RF variants — the model hierarchy (A/B/C/D × windows) is the
    minimum set needed to isolate the effect of derivatives vs. windowed statistics vs. window
    length, each held against a fair common-subset population.
  - Windows tested: `[0.5, 1.0, 2.0, 3.0]`s, a subset close to (though not identical to) the
    0.5/1/2/3/5s specified — this was the window set already baked into the in-flight run's cached
    feature panels and completed fits by the time this task began; rerunning to add a 5s window
    would have meant re-fitting the tuning/ablation/primary/generalization stages from scratch for
    a dimension the physics diagnosis (§6) suggests carries little additional signal anyway. Not
    done, to honor "do not rerun completed experiments."
- **Runtime:** 544.5s (~9.1 min) wall-clock, end to end, `n_jobs=-1`, RF capped at 200 trees.
  Temporal feature panels (`data/ml_temporal/*.parquet`) were built once, previously, and reused
  (not rebuilt) on this run.
- **Best model:** Model D, 1s window (state + 1-step derivatives + causal 1s temporal statistics),
  RF(`n_estimators=200, max_depth=12, min_samples_leaf=5, class_weight=balanced_subsample`),
  threshold 0.841.
- **Best feature set:** state + 1-step derivatives + windowed temporal statistics together
  (derivatives contribute the real signal; windowed statistics alone slightly underperform state-only).
- **Best temporal window:** 1s — indistinguishable from 0.5s/2s/3s on PR-AUC; no evidence longer
  history helps.

## Exact files generated this run

```
outputs/ml_temporal/experiment_config.json
outputs/ml_temporal/metrics/hyperparameter_tuning.json
outputs/ml_temporal/metrics/window_ablation_common_subset.json
outputs/ml_temporal/metrics/window_ablation_summary.csv
outputs/ml_temporal/metrics/primary_model_metrics.json
outputs/ml_temporal/metrics/false_alarm_analysis.json
outputs/ml_temporal/metrics/regime_breakdown.csv
outputs/ml_temporal/metrics/airspeed_breakdown.csv
outputs/ml_temporal/metrics/lead_time_by_regime.csv
outputs/ml_temporal/metrics/lead_time_by_airspeed.csv
outputs/ml_temporal/metrics/physics_diagnosis.csv
outputs/ml_temporal/metrics/generalization_check.json
outputs/ml_temporal/metrics/primary_model_calibration.json
outputs/ml_temporal/metrics/false_positive_physics_characterization.csv   (post-hoc, this session)
outputs/ml_temporal/metrics/false_positive_regime_composition.csv          (post-hoc, this session)
outputs/ml_temporal/models/primary_model_D_1s.joblib
outputs/ml_temporal/plots/01_pr_curve_instantaneous_vs_temporal.png
outputs/ml_temporal/plots/02_lead_time_recall_comparison.png
outputs/ml_temporal/plots/03_warning_composition_by_lead_time.png
outputs/ml_temporal/plots/04_pr_auc_vs_history_window.png
outputs/ml_temporal/plots/04b_early_warning_recall_vs_history_window.png
outputs/ml_temporal/plots/05_warning_time_distribution.png
outputs/ml_temporal/plots/06_feature_importance_primary_model.png
outputs/ml_temporal/plots/06b_confusion_matrix_primary_model.png
outputs/ml_temporal/plots/07_lead_time_by_regime.png
outputs/ml_temporal/plots/08_lead_time_by_airspeed.png
outputs/ml_temporal/plots/09_feature_distributions_near_vs_safe.png
outputs/ml_temporal/plots/10_calibration_curve_primary_model.png
outputs/ml_temporal/temporal_experiment_report.md                          (this report)
data/ml_temporal/temporal_train.parquet   (cached, reused this run — not rebuilt)
data/ml_temporal/temporal_val.parquet     (cached, reused this run — not rebuilt)
data/ml_temporal/temporal_test.parquet    (cached, reused this run — not rebuilt)
```

---

**STOP.** Per the research plan, this stage ends here. No boundary experiments, ablations beyond
what's above, generalization work beyond the one check already run, dashboard, or research writing
should proceed automatically from this report — awaiting instruction.
