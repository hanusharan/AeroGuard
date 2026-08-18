# AeroGuard — Final Temporal ML Experiment: v0.2 vs v0.3

**Run:** `scripts/run_temporal_experiment_v03.py`, seed `20260817`, wall-clock runtime
**1324.8s (~22.1 min)**, executed once, no reruns. Supplementary analysis:
`scripts/analyze_v03_physics_vs_ml.py`, `scripts/build_v03_final_comparison.py` (both
read-only against already-saved artifacts — no additional model fits). All new artifacts
live under `outputs/ml_v03/` and `data/ml_temporal_v03/` (both new, additive). Nothing
under `aeroguard/`, `aeroguard_dataset/`, `data/processed/`, `data/splits/`, `data/ml/`,
`data/ml_temporal/`, or `outputs/ml_temporal/` was read for anything other than reference,
and nothing there was modified (confirmed in the Final Validation section).

---

## 1. Research question

*"Does the physically credible multi-second precursor introduced in v0.3 produce genuinely
useful early-warning performance that was absent in v0.2?"*

## 2. v0.2 baseline (reference only, never rerun)

v0.2's own temporal experiment (`outputs/ml_temporal/temporal_experiment_report.md`)
established that its Stage-4 model was, at best, an **imminent-stall detector**: row-level
recall was 97–99% inside 0.5s of the actual crossing, then fell to 18–26% at 0.5–3s and to
0–2% at 3–5s. Median credited event-level lead time was 0.53s (mean 0.81s), and the physical
root cause (confirmed independently in `outputs/precursor_diagnosis/`) was that v0.2's
`near_boundary` regime produced crossings with a median 8°→16° alpha transition of only
0.37s — there was essentially no multi-second precursor for any model to learn from.

## 3. Why v0.3 was created

A multi-stage physics-calibration effort (`outputs/v03_calibration/`,
`outputs/dataset_audit_v3/`) diagnosed the short v0.2 precursor as a **control-profile
timing artifact**, not a physics limitation, and iteratively designed, calibrated, and
gated a new `gradual_approach_v3` regime (two-stage, same-sign, duration-capped elevator
pulses) that reliably produces smooth, monotonic, multi-second `SAFE → GRADUAL APPROACH →
NEAR STALL → CROSSING` trajectories using the *same* validated aircraft physics, pitch
model, and stall boundary as v0.1/v0.2 — only the control-input *timing* changed. The full
v0.3 dataset (3,150 trajectories: 500 `normal` + 250 `stall` + 2,400 `gradual_approach_v3`)
passed its generation gate (`outputs/dataset_audit_v3/v03_generation_report.md`): 317
`gradual_approach_v3` crossings, 194 with a usable dip-aware precursor estimate, median
4.38s, with 66.0% / 59.3% / 55.7% / 13.4% reaching ≥2s / ≥3s / ≥4s / ≥5s.

## 4. Experimental methodology (pre-registered, locked before results were seen)

Per Phase 1's explicit instruction, this experiment reuses v0.2's model family, feature
definitions, threshold-selection procedure, event/lead-time definitions, and lead-time
bucket edges **unchanged**, with only the deliberate, up-front efficiency reductions the
task instructions specified:

| Dimension | v0.2 | v0.3 (this experiment) | Source of match/deviation |
|---|---|---|---|
| Model family | RandomForest (`n_estimators=200, max_depth=12, min_samples_leaf=5, class_weight=balanced_subsample`) | **identical**, reused unchanged, no re-tuning | `ml/temporal_config_v03.py:FROZEN_RF_PARAMS` = v0.2's own tuned result |
| Feature definitions | instantaneous state (8) / state+derivatives (13) / +windowed temporal stats (10/window) | **identical**, imported unchanged from `ml/temporal_config.py` | `ml/temporal_config_v03.py` re-exports, does not redefine |
| History windows | [0.5, 1, 2, 3]s | **[0.5, 1, 2]s** (3s dropped) | explicit instruction: v0.2 already showed 3s adds nothing |
| Model hierarchy | A / B / C / D | **A / B / D** (C dropped) | explicit instruction: v0.2 showed C never helps |
| Primary window | 1s | **1s** (unchanged) | explicit instruction |
| Threshold selection | TRAIN-then-VAL (top-k by TRAIN F1, best VAL F1) | **identical**, `ml/calibration.py` reused unchanged | — |
| Event/lead-time definition | episode-based, 5s-horizon-capped | **identical**, `ml/events.py` reused unchanged | — |
| Lead-time buckets | 0–0.5/0.5–1/1–2/2–3/3–4/4–5s | **identical**, `ml/temporal_experiment.py:LEAD_TIME_BINS_FINE` reused unchanged | — |
| Model A ("instantaneous baseline") | frozen pre-existing Stage-3 model, re-scored only | **freshly fit** on v0.3's own TRAIN split, same architecture/features/hyperparameters | no frozen v0.3 baseline exists (Stage 3 was never run on v0.3); freshly fitting is the correct like-for-like analogue, not a deviation — see `ml/temporal_experiment_v03.py` module docstring |
| Train/val/test methodology | trajectory-level, 700/150/150 | **identical procedure**, trajectory-level, 2205/472/473 | `data/splits/split_manifest_v3.csv`, generated at the dataset stage, unmodified here |

No methodology choice below this table was changed after seeing v0.3's results — this
report was written from the single run logged in `outputs/ml_v03/experiment_config.json`.

## 5. Leakage controls (verified before any model was trained)

`tests/test_temporal_v03_integrity.py` (11 tests, all passing, run both before and after
the temporal cache was built):

| Check | Result |
|---|---|
| Train/val/test trajectory-level split, zero overlap | ✅ verified directly on `split_manifest_v3.csv` and on the built cache |
| v0.3 trajectory-id namespace disjoint from v0.2's (`traj_00000...` vs `traj_0000...`) | ✅ — guards against ever silently joining v0.3 rows to v0.2 metadata |
| No label-derived / forbidden columns in any feature set | ✅ `get_xy`'s leakage guard (reused unchanged from `ml/temporal_experiment.py`) raises on `future_stall_5s`, `future_stall_5s_available`, `is_unsafe`, `time_to_stall`, `trajectory_id`, `time`, `split` |
| Temporal windows strictly causal, never cross a trajectory boundary | ✅ `build_temporal_panel` groups by `trajectory_id` before every rolling/shift op (unchanged from v0.2, re-verified against real v0.3 cache: `test_v03_real_data_trajectory_boundaries_never_crossed`) |
| `time_to_stall` never negative (no past-crossing-as-future leak) | ✅ |
| Test set untouched until final evaluation | ✅ thresholds selected TRAIN-then-VAL; TEST only appears inside `evaluate_on_test()` |
| Windows never span two trajectories | ✅ (same mechanism as v0.2, reused unmodified) |

## 6. Model configurations trained

Exactly 8 RandomForest fits, all `n_estimators=200, max_depth=12, min_samples_leaf=5,
class_weight=balanced_subsample` (no hyperparameter search — v0.2's frozen config reused):

1. **A** (v0.3-retrained instantaneous baseline, 8 features) — common-subset population
2. **B** (state + derivatives, 13 features) — common-subset population
3. **D_0.5s** (state + derivatives + 0.5s temporal stats, 23 features) — common-subset population
4. **D_1s** (23 features) — common-subset population
5. **D_2s** (23 features) — common-subset population
6. **D_1s primary** (23 features) — own realistic-scale population (this is the model saved to `outputs/ml_v03/models/primary_model_D_1s.joblib` and used for every downstream analysis: false-alarm, regime/airspeed breakdown, physics-vs-ML)
7. **D_1s generalization check** — TRAIN with all `gradual_approach_v3` trajectories excluded

That's 7 distinct fits; the primary model (#6) reuses feature set D_1s with a different
(larger, "own usable rows") row population than #4, so it is a separate fit — **7 total**,
against v0.2's 13 (hyperparameter tuning was skipped entirely; window/model hierarchy cut
from 4 windows × 2 models + B + A = 13 down to 3 windows × 1 model (D only) + B + A(retrain)
+ primary + generalization = 7).

## 7. Overall results

**Common-subset ablation** (identical row population for A/B/D, `outputs/ml_v03/metrics/common_subset_ablation_summary.csv`):

| Model | Features | PR-AUC | Recall(1–2s) | Recall(2–3s) | Recall(3–4s) |
|---|---|---|---|---|---|
| A — v0.3-retrained instantaneous baseline | 8 | 0.9027 | 0.600 | 0.551 | 0.600 |
| B — state + 1-step derivatives | 13 | **0.9189** | 0.643 | 0.589 | 0.620 |
| D_0.5s | 23 | 0.9179 | 0.633 | 0.522 | 0.554 |
| **D_1s (primary window)** | 23 | 0.9177 | 0.630 | 0.496 | 0.542 |
| D_2s | 23 | 0.9163 | 0.589 | 0.459 | 0.535 |

An important, honest nuance the common-subset table surfaces: **B is marginally *better*
than every D_w variant here**, mirroring v0.2's own finding that windowed summary
statistics add little beyond the 1-step derivatives — the same qualitative pattern holds in
v0.3. What is categorically different from v0.2 is the *absolute* magnitude of every
model's 1–5s bucket recall: even the plain instantaneous baseline (A) now recovers 55–66%
of the 2–5s-bucket positive rows, because the underlying precursor itself is now
multi-second — alpha (and `stall_margin`, its exact algebraic transform) is elevated for
several seconds before crossing, not just in the final instant. This is discussed further
in §9 and §14.

**Primary model** (Model D, 1s window, own realistic-scale population — 538,034 test rows,
456/473 test trajectories, threshold 0.859, `outputs/ml_v03/metrics/primary_model_metrics.json`):

| Metric | v0.2 | v0.3 |
|---|---|---|
| PR-AUC | 0.813 | **0.890** |
| ROC-AUC | 0.963 | 0.978 |
| Precision | 0.900 | 0.935 |
| Recall | 0.701 | **0.736** |
| F1 | 0.788 | 0.824 |
| Confusion matrix | TN 165,477 · FP 665 · FN 2,546 · TP 5,974 | TN 489,495 · FP 2,370 · FN 12,184 · TP 33,985 |

Feature importance (top 5 of 23, `outputs/ml_v03/plots/05_feature_importance_primary_model.png`):
`stall_margin` (0.155), `alpha_max_1s` (0.143), `alpha` (0.110), `alpha_mean_1s` (0.105),
`elevator` (0.088) — the same alpha-family dominance as v0.2, consistent with the physics
being unchanged.

## 8. Lead-time results

Row-level recall by actual time-to-crossing bucket (primary model, own population):

| Bucket | v0.2 recall | v0.3 recall |
|---|---|---|
| 0–0.5s | 98.8% | 97.2% |
| 0.5–1s | 17.9% | **69.6%** |
| 1–2s | 17.7% | **61.8%** |
| 2–3s | 26.0% | **48.2%** |
| 3–4s | 2.3% | **46.9%** |
| 4–5s | 0.0% | **48.4%** |
| >5s | n/a (structurally empty — `future_stall_5s` requires a crossing within 5s by construction, in both v0.2 and v0.3; no row can have `time_to_stall` > 5s and `y=1`) | n/a (same structural reason) |

Event-level (`n_events` = distinct stall episodes in the primary model's own usable test
population — episodes, not trajectories; 19 v0.3 test trajectories re-enter `is_unsafe` a
second time, contributing 2 episodes each):

| Metric | v0.2 | v0.3 |
|---|---|---|
| n events | 14 | **76** |
| Event recall | 100.0% (14/14) | 96.1% (73/76) |
| Median credited lead time | 0.53s | **4.72s** |
| Mean credited lead time | 0.81s | **3.42s** |
| Max credited lead time | — | 5.00s (horizon cap) |

Warning coverage — fraction of ALL events (warned or not) detected at least X seconds early
(`outputs/ml_v03/metrics/v02_vs_v03_warning_coverage.csv`, plotted in
`10_v02_vs_v03_warning_coverage.png`):

| Threshold | v0.2 | v0.3 |
|---|---|---|
| ≥0.5s | not computed for v0.2 | **92.1%** |
| ≥1s | 14.3% | **72.4%** |
| ≥2s | 14.3% | **64.5%** |
| ≥3s | 7.1% | **59.2%** |
| ≥4s | 0.0% | **55.3%** |
| ≥5s | 0.0% | **38.2%** |

**The key hypothesis — a substantial improvement specifically in the ≥2–5s warning
region — is confirmed, with a large margin, at the realistic test-set scale (76 events
vs v0.2's 14).**

## 9. v0.2 vs v0.3 comparison table (central result)

Full machine-readable version: `outputs/ml_v03/metrics/v02_vs_v03_comparison.csv`.

| Metric | v0.2 | v0.3 | Change |
|---|---|---|---|
| Crossing count (test split, from metadata) | 27 | 67 | +40 |
| Usable crossing count (primary model's own event population) | 14 | 76 | +62 |
| Median physical precursor duration (dip-aware) | 0.54s | 4.38s | +3.84s |
| ≥2s precursor coverage (physical) | ~4% | 66.0% | +62pp |
| ≥3s precursor coverage (physical) | ~0% | 59.3% | +59pp |
| ≥4s precursor coverage (physical) | ~0% | 55.7% | +56pp |
| ≥5s precursor coverage (physical) | ~0% | 13.4% | +13pp |
| Baseline PR-AUC (Model A, common-subset population) | 0.9329 | 0.9027 | −0.030 |
| Temporal PR-AUC (Model D, common-subset population) | 0.9338 | 0.9177 | −0.016 |
| Temporal improvement over baseline (common-subset, ΔPR-AUC) | +0.0010 | +0.0150 | +0.014 |
| Primary model PR-AUC (own realistic population) | 0.8133 | 0.8903 | +0.077 |
| Recall 0–0.5s | 98.8% | 97.2% | −1.7pp |
| Recall 0.5–1s | 17.9% | 69.6% | +51.7pp |
| Recall 1–2s | 17.7% | 61.8% | +44.1pp |
| Recall 2–3s | 26.0% | 48.2% | +22.2pp |
| Recall 3–4s | 2.3% | 46.9% | +44.6pp |
| Recall 4–5s | 0.0% | 48.4% | +48.4pp |
| Event-level recall | 100.0% | 96.1% | −3.9pp |
| Median lead time | 0.53s | 4.72s | +4.19s |
| Row-level false-positive rate | 0.400% | 0.482% | +0.08pp |
| Episode-level false-alarm precision | 67.6% | 76.9% | +9.2pp |

Note on the "baseline/temporal PR-AUC" rows: both are drawn from the **common-subset**
ablation (identical row population across A/B/D — the only apples-to-apples comparison
across the model hierarchy), which is why these two numbers are both *lower* in v0.3 than
in v0.2 even though the *primary/own-population* PR-AUC (a different, larger, harder
population — see §7) is substantially higher. Both are reported, clearly labeled, rather
than picking whichever looks better — the common-subset PR-AUC modestly dropping while
lead-time recall dramatically improves is itself an informative result (§14).

## 10. Regime analysis

Primary model, TEST, post-hoc only (regime is never a model input),
`outputs/ml_v03/metrics/regime_breakdown.csv` / `lead_time_by_regime.csv`:

| Regime | Rows | Positives | Recall | Precision | F1 |
|---|---|---|---|---|---|
| normal | 113,481 | 0 | n/a | — | — |
| **gradual_approach_v3** | 396,207 | 30,001 | **80.5%** | 93.4% | 86.5% |
| stall | 28,346 | 16,168 | 60.8% | 100.0% | 75.6% |

Lead-time recall by regime (`06_lead_time_by_regime.png`) shows the mechanism directly:
`gradual_approach_v3` sustains real recall across every bucket out to 4–5s (95.98% / 86.1%
/ 83.0% / 65.7% / 64.3% / 59.8%), while `stall` recall is 96–98.5% in 0–1s and **exactly
0%** beyond 1s — consistent with `stall`'s own median 0.29–0.38s physical precursor (§9):
there is no multi-second signal for the model to find there, in either dataset version.
`gradual_approach_v3` is precisely where the new physics lives, and precisely where
performance improved.

## 11. Generalization experiment (Phase 7 — the critical check)

Model D (1s) retrained with **all 1,691 `gradual_approach_v3` TRAIN trajectories excluded**
(556,080 rows remain), evaluated unchanged on the full TEST split (which still includes
`gradual_approach_v3`). `outputs/ml_v03/metrics/generalization_check.json`,
`12_generalization_comparison.png`:

| Metric | Full TRAIN | `gradual_approach_v3` excluded from TRAIN | Change |
|---|---|---|---|
| PR-AUC | 0.890 | 0.552 | −0.338 |
| `gradual_approach_v3` regime recall | 80.5% | 23.7% | −56.8pp |
| Event recall | 96.1% (73/76) | 64.5% (49/76) | −31.6pp |
| Median credited lead time | 4.72s | 0.73s | −3.99s |
| Recall 0–0.5s | 97.2% | 81.2% | −16.0pp |
| Recall 0.5–1s | 69.6% | 11.5% | −58.1pp |
| Recall 1–2s | 61.8% | 1.5% | −60.3pp |
| Recall 2–3s | 48.2% | 1.8% | −46.4pp |
| Recall 3–4s | 46.9% | 1.7% | −45.2pp |
| Recall 4–5s | 48.4% | 2.4% | −46.0pp |
| Warning coverage ≥4s | 55.3% | 11.8% | −43.5pp |
| Warning coverage ≥5s | 38.2% | 6.6% | −31.6pp |

**This is the single most important finding in the experiment.** The near-immediate
(0–0.5s) detection capability degrades only modestly (97.2%→81.2%) — that signal is
apparently close to regime-generic ("alpha is very near the boundary right now"). But the
entire **multi-second** early-warning capability — everything beyond ~0.5s — collapses by
roughly 20–40x, down to 1.5–2.4% row-level recall, when the model has never seen a
`gradual_approach_v3`-shaped trajectory during training. A small residual signal survives
(event recall doesn't go all the way to zero, and a few events still get ≥4–5s credit), so
this is not a *total* floor-zero collapse the way v0.2's stall-exclusion check was (which
went from 67.4%→6.3% regime recall). But it is unambiguously a **collapse, not
preservation**, of the multi-second capability specifically. **A meaningful share of the
model's apparent multi-second skill is regime-shape memorization, not a transferable
"rising alpha + shrinking margin over several seconds → stall is coming" physics
understanding.**

## 12. False-alarm analysis

`outputs/ml_v03/metrics/false_alarm_analysis.json`,
`false_positive_physics_characterization.csv`, `false_positive_regime_composition.csv`:

| Episode-level stat | v0.2 | v0.3 |
|---|---|---|
| Warning episodes | 34 | 121 |
| True warning episodes | 23 | 93 |
| False-alarm episodes | 11 | 28 |
| False warning rate | 32.4% | 23.1% |
| Episode-level precision | 67.6% | **76.9%** |
| Warnings/trajectory | 0.254 | 0.265 |
| False alarms/minute | 0.378 | 0.313 |

Row-level FPR is essentially unchanged (0.40%→0.48%, both tiny). Episode-level precision
and false-alarm rate both *improved* slightly in v0.3.

**Physics characterization of the 2,370 row-level false positives** (compared to the
33,985 true positives, same primary model): mean α 0.169 rad (9.7°) vs. 0.393 rad (22.5°)
for true positives; mean `stall_margin` +0.111 (still positive/healthy) vs. −0.113 for true
positives; 57.7% have rising α (dα/dt>0) vs. 72.4% of true positives; 66.4% are
decelerating (dV/dt<0) vs. 86.5% of true positives. Regime composition: 72.2%
`gradual_approach_v3`, 27.8% `normal`, 0.04% `stall`.

**This is a more nuanced picture than v0.2's.** In v0.2, 100% of false positives sat on
trajectories that *never* eventually stall — clean "boring, safe flight" noise. In v0.3,
**19 of 27 unique false-positive trajectories (70%) DO eventually cross the boundary
somewhere** in their recorded telemetry — these are largely early/ambiguous rows on
genuine `gradual_approach_v3`-shaped trajectories (moderate, rising α; shrinking but still
positive margin) that either haven't reached the boundary within the specific 5s window
being scored, or are on a trajectory that recovers before ever crossing. **Conclusion: the
false positives are not obviously-safe noise the way v0.2's were — they are physically
plausible near-approach states, consistent with the model correctly picking up on the
gradual-approach *shape* even when that specific instance doesn't culminate in a crossing
within the horizon.** This is a reasonable, expected cost of learning a genuine
multi-second precursor shape, not a red flag.

## 13. Physics-vs-ML consistency

`outputs/ml_v03/metrics/physics_vs_ml_lead_time.csv` / `physics_vs_ml_summary.json`,
`11_precursor_duration_vs_credited_lead_time.png` — per TEST-split crossing trajectory,
physical precursor duration (dataset-side, model-independent) vs. the primary model's
credited warning lead time:

| Regime | n test crossings | n usable for ML | Median physical precursor | Median ML credited lead (warned only) | Pearson r (paired, n) |
|---|---|---|---|---|---|
| `gradual_approach_v3` | 42 | 40 | 4.39s | 4.90s | 0.337 (n=22) |
| `stall` | 25 | 17 | 0.285s | 0.67s | 0.829 (n=16) |

**Does the ML warning horizon approximately track the physical precursor horizon?**
At the *aggregate/population* level, yes: median ML credited lead time (4.90s,
capped at the 5.0s labeling horizon) is close to the median physical precursor (4.39s) for
`gradual_approach_v3`, and the same holds for `stall`'s much shorter precursor (0.67s vs.
0.29s). But the *per-event* correlation for `gradual_approach_v3` is only moderate
(r=0.34) — the model does not finely calibrate its warning time to each individual
trajectory's specific onset; it behaves more like "this looks like the gradual-approach
shape, warn early" at a population level than "this specific trajectory's precursor started
exactly T seconds ago." (`stall`'s much higher r=0.83 is likely an artifact of that
regime's narrow dynamic range — precursors cluster tightly around 0.2–0.4s, so even a
coarse detector correlates well within a small window.)

**Distinguishing the three things Phase 9 asks to keep separate:**
- **Physical precursor availability**: real, large, verified independently of any model
  (§3, §9) — 66%/59%/56% of `gradual_approach_v3` crossings have a genuine ≥2/3/4s
  precursor.
- **Model detectability**: strong, when trained in-distribution (§7, §8, §10) — the model
  clearly exploits the available signal, well beyond v0.2's ceiling.
- **Model generalization**: weak (§11) — most of that detectability does not transfer to a
  regime the model has never trained on. Correlation ≠ causation is also worth stating
  plainly here: the moderate per-event r above shows association, not that the model has
  learned the underlying causal mechanism generating the precursor.

## 14. Limitations

- **The overall (common-subset) PR-AUC gain from temporal features over the instantaneous
  baseline is still small in v0.3** (+0.015, vs. v0.2's +0.001) — qualitatively the same
  modest pattern as v0.2. What changed dramatically is not "temporal ML got much better at
  finding a hidden multi-second signal"; it's that **v0.3's precursor is now so
  physically pronounced that even the instantaneous state (Model A) is informative several
  seconds out** (2–5s bucket recall 55–66% for A alone, common-subset population). Model B
  (derivatives) adds a real, if modest, further gain over A; the richer windowed statistics
  (Model D) do not clearly beat B, mirroring v0.2's own finding.
- **Generalization is the central limitation** (§11): the multi-second early-warning
  capability collapses by 20–40x when `gradual_approach_v3` is excluded from training. This
  system, as evaluated, should not be assumed to generalize to a genuinely novel
  slow-precursor shape it hasn't been trained on.
- **The false positives changed character** (§12): a majority now sit on trajectories that
  do eventually cross the boundary, just outside the specific 5s scoring window — a
  reasonable byproduct of learning the approach shape, but worth knowing before treating
  row-level FPR as the whole false-alarm story.
- **Per-event physics/ML lead-time correlation is only moderate** (r=0.34) for the regime
  that matters — aggregate/median tracking looks good, individual-trajectory tracking does
  not.
- **`stall` regime remains an imminent-only detector in both v0.2 and v0.3** (0% recall
  beyond 1s in both) — this experiment did not, and was not intended to, change that;
  `stall`'s own physical precursor is still ~0.3s in both dataset versions.
- **19 test trajectories have two separate stall episodes** (`is_unsafe` re-entered after a
  first crossing) — event counts in this report are per-episode, not per-trajectory;
  documented explicitly in §7/§13 rather than silently collapsed to one event.

## 15. Scientific interpretation

The physically credible multi-second precursor introduced in v0.3 **does** produce
substantially better early-warning performance than v0.2 when the model is trained on data
that includes the regime being evaluated: event recall 96% (vs. v0.2's small-sample 100%
on only 14 events), median credited lead time 4.72s (vs. 0.53s), and 55–59% of events
warned ≥3–4s early (vs. 0–7%). This is a real, large, statistically meaningful improvement
at a much more reliable sample size (76 events vs. 14) and represents the clearest evidence
in this project's history that multi-second ML stall early-warning is achievable *given the
right underlying flight-dynamics precursor to learn from*.

However, the generalization check is decisive evidence that this capability is
**substantially regime-specific rather than a generalized understanding of
approach-to-stall physics**. A meaningful residual signal survives regime exclusion (this
is not nothing), but the bulk of the multi-second recall — the very capability that defines
this experiment's headline result — requires having seen `gradual_approach_v3`-shaped
trajectories during training. The improvement is real and large for the deployed,
in-distribution case (which is also the realistic development scenario: a real system would
be trained on data resembling its deployment population), but the *mechanism* is better
described as "the model learned to recognize this specific gradual-approach trajectory
shape" than as "the model learned that a multi-second rise in α with shrinking margin
predicts stall, regardless of the specific control-input shape that produced it."

## 16. Final decision: CASE B

**CASE B — Some improvement, but limited or regime-specific.**

Justification, weighing both directions honestly:

- **For CASE A**: the in-distribution improvement is large, real, and answers the primary
  research question affirmatively at a much more reliable sample size than v0.2 ever had.
  Physical precursor availability, model detectability, false-alarm control, and
  aggregate physics-vs-ML lead-time tracking are all consistent with a genuinely useful
  early-warning capability.
- **Why not CASE A**: the explicit generalization criterion this experiment was
  pre-registered to apply — "if performance collapses [when the regime is excluded from
  training], state clearly that the model learned regime-specific patterns rather than
  transferable physics" — is met. Row-level 1–5s-bucket recall drops 20–40x under
  exclusion; this is a collapse of exactly the capability the whole experiment set out to
  demonstrate.
- **Why not CASE C**: the physical precursor unambiguously *is* exploited by the model
  in-distribution — this is not "physics exists but ML cannot use it." Model detectability
  is strong when trained appropriately.
- **Why not CASE D**: no dataset or model problem was found. Every leakage/integrity check
  passed; the ablation, regime-breakdown, and physics-diagnosis results are internally
  consistent with each other and with the independently-computed physical precursor
  statistics; the generalization result, while sobering, is a coherent, mechanistically
  interpretable finding (regime-shape memorization), not an anomaly requiring
  investigation.

Not forcing a positive result: this experiment did **not** establish that AeroGuard has
learned generalizable stall-precursor physics. It established that, given training data
resembling the deployment population, the v0.3 precursor supports a substantially better
early-warning system than v0.2 ever could — and that this capability's robustness to novel
precursor shapes is the open problem for the next stage of work, not something this
experiment's own scope was designed to solve (Phase 7 explicitly asked for exactly one
targeted generalization experiment, run and reported here).

---

## Files produced this stage

```
ml/temporal_config_v03.py
ml/temporal_data_v03.py
ml/temporal_experiment_v03.py
scripts/run_temporal_experiment_v03.py
scripts/analyze_v03_physics_vs_ml.py
scripts/build_v03_final_comparison.py
tests/test_temporal_v03_integrity.py                        (11 tests, all passing)
data/ml_temporal_v03/temporal_{train,val,test}.parquet       (cached feature panels)
outputs/ml_v03/experiment_config.json
outputs/ml_v03/v03_temporal_ml_report.md                     (this report)
outputs/ml_v03/models/primary_model_D_1s.joblib
outputs/ml_v03/metrics/common_subset_ablation.json
outputs/ml_v03/metrics/common_subset_ablation_summary.csv
outputs/ml_v03/metrics/primary_model_metrics.json
outputs/ml_v03/metrics/primary_model_warning_coverage.json
outputs/ml_v03/metrics/primary_model_calibration.json
outputs/ml_v03/metrics/false_alarm_analysis.json
outputs/ml_v03/metrics/false_positive_physics_characterization.csv
outputs/ml_v03/metrics/false_positive_regime_composition.csv
outputs/ml_v03/metrics/regime_breakdown.csv
outputs/ml_v03/metrics/airspeed_breakdown.csv
outputs/ml_v03/metrics/lead_time_by_regime.csv
outputs/ml_v03/metrics/physics_diagnosis.csv
outputs/ml_v03/metrics/generalization_check.json
outputs/ml_v03/metrics/physics_vs_ml_lead_time.csv
outputs/ml_v03/metrics/physics_vs_ml_summary.json
outputs/ml_v03/metrics/v02_vs_v03_comparison.csv
outputs/ml_v03/metrics/v02_vs_v03_warning_coverage.csv
outputs/ml_v03/plots/01_pr_curve_instantaneous_vs_temporal.png
outputs/ml_v03/plots/02_lead_time_recall_comparison.png
outputs/ml_v03/plots/03_pr_auc_vs_history_window.png
outputs/ml_v03/plots/04_warning_time_distribution.png
outputs/ml_v03/plots/05_feature_importance_primary_model.png
outputs/ml_v03/plots/05b_confusion_matrix_primary_model.png
outputs/ml_v03/plots/06_lead_time_by_regime.png
outputs/ml_v03/plots/07_feature_distributions_near_vs_safe.png
outputs/ml_v03/plots/08_calibration_curve_primary_model.png
outputs/ml_v03/plots/09_v02_vs_v03_lead_time_comparison.png
outputs/ml_v03/plots/10_v02_vs_v03_warning_coverage.png
outputs/ml_v03/plots/11_precursor_duration_vs_credited_lead_time.png
outputs/ml_v03/plots/12_generalization_comparison.png
```

---

**STOP.** Per Phase 12's explicit instruction, this stage ends here after the report and
decision gate. No further experiments, ablations, or research should proceed
automatically from this report.
