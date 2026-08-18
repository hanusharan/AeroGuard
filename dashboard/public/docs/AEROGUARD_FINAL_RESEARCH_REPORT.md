# AeroGuard — Final Research Report

**Status: FROZEN.** This report synthesizes the complete AeroGuard research program,
v0.1 through the final cross-mechanism generalization experiment, using only
numbers already measured and reported in this repository's own experiment reports.
No new experiment, ablation, or model was run to produce this document — it is a
packaging/synthesis pass over `outputs/*/`. Every number below is cited to its
source report; see `PROVENANCE.md` for which code produced which artifact and
`REPRODUCIBILITY.md` for exact commands to regenerate any of it.

---

## 1. Abstract

AeroGuard is a self-contained research pipeline — a 2D longitudinal flight-dynamics
simulator, a versioned trajectory-dataset generator, and a machine-learning
early-warning system — built to ask one question: **can a physically credible,
multi-second precursor to an aerodynamic stall be reliably predicted by a machine
learning model before the stall occurs, and does that predictive skill transfer
beyond the exact scenario it was trained on?**

Three dataset generations (v0.1 → v0.2 → v0.3) and a parallel line of ML
experiments trace the answer. v0.1/v0.2 datasets, generated with fast-rising
elevator control profiles, produced stall crossings with a median alpha 8°→16°
transition of only 0.37–0.54 seconds — too short a physical precursor for any
model to learn a genuine multi-second warning from, and a Stage-4 temporal-ML
model confirmed this: reliable lead time under 0.5s, recall falling to 0–26%
beyond that. A multi-stage physics-calibration effort diagnosed this as a
**control-profile timing artifact, not a physics limitation**, and designed,
calibrated, and gated a new v0.3 dataset (3,150 trajectories, 5,340,865 rows)
built on the *same* validated aircraft dynamics and stall boundary, with only the
elevator-input *timing* changed. The result: a median physical precursor of 4.38s
(66% of crossings ≥2s, 59% ≥3s), and a temporal ML model achieving event recall
96.1% (73/76) with median credited lead time 4.72s — roughly 9x v0.2's lead time.

A regime-exclusion check showed this multi-second capability collapses 20–40x
when the model has zero training exposure to the slow-approach phenomenon,
raising the concern that the model had merely memorized one specific control-input
shape. A final, independently designed alternative-mechanism experiment
(a structurally distinct single-pulse precursor, "Candidate F") tested this
directly: the frozen v0.3 model retained 94% of its in-distribution PR-AUC and
100% event recall (46/46) on the novel mechanism, in both directions of transfer.
**The evidence supports multi-second stall early-warning and transfer across
structurally distinct control-input mechanisms producing the same underlying
physical phenomenon, but does NOT establish universal zero-shot stall prediction
across arbitrary unseen flight regimes.**

## 2. Research question

Can a physics-based flight simulator produce trajectories with a genuine,
multi-second (2–5s) precursor signal ahead of a stall event, and — if so — can a
machine-learning model learn to detect that precursor early enough to constitute
a *useful* early-warning system, rather than an imminent-event detector reacting
inside the final half-second before the event?

A secondary, later-arising question, made necessary by the first answer: is the
learned precursor-detection skill a transferable understanding of "rising alpha
with shrinking stall margin over several seconds," or is it a memorized fingerprint
of one specific control-input shape?

## 3. Hypothesis

That the short precursor window observed in early datasets was a byproduct of how
control inputs were generated (fast elevator pulses aimed at a far-past-boundary
equilibrium) rather than an inherent property of the underlying flight dynamics —
and that slowing and re-aiming the control-input timing, without touching the
validated physics, could produce trajectories with a real multi-second precursor
that a temporal ML model could then learn to detect.

## 4. AeroGuard architecture

```
aeroguard/                  physics engine: 5-state RK4 integrator (V, gamma,
                             theta, h, q), nonlinear CL(alpha) with emergent
                             stall, linear pitch-response surrogate.
aeroguard_dataset/           control-profile generation, trajectory simulation
                             at scale, feature computation, future-stall
                             labeling, train/val/test splitting, auditing.
ml/                          baseline (instantaneous) and temporal (windowed
                             state+derivative) ML pipelines: RandomForest,
                             logistic regression, rule-based baselines.
scripts/                     one script per pipeline stage (generation,
                             calibration, ML experiment, audit).
data/, outputs/              versioned datasets and every experiment's reports,
                             metrics, plots, and models.
```

See `outputs/final/figures/01_aeroguard_pipeline.png` for the end-to-end flow
and `PROVENANCE.md` for the full canonical/historical file map.

## 5. Physics / simulation model

A 2D longitudinal-only point-mass model (`aeroguard/`): airspeed, flight-path
angle, pitch angle, altitude, and pitch rate, integrated with fixed-step RK4.
Lift is a smooth blend of a linear pre-stall curve and a flat-plate-like
post-stall curve, centered on a stall angle of attack of ~16.07° — stall is an
emergent property of this smooth `CL(alpha)` curve, not a discrete threshold
rule. Drag follows a standard polar (`CD = CD0 + k*CL^2`); thrust is linear in
throttle; pitch dynamics use a linear surrogate for the pitching-moment equation
(elevator deflection drives pitch-rate acceleration, damped by pitch rate,
weakly restored by angle of attack). Air density is constant (sea level); the
aircraft is a rigid body of constant mass. This is explicitly **not a validated
model of any real aircraft** — coefficients are plausible, order-of-magnitude
defaults for a small generic fixed-wing aircraft (`README.md`, `aeroguard/aircraft.py`).
The physics engine itself was never modified after Stage 1; every later stage
changed only how control inputs (elevator/throttle profiles) were generated.

## 6. Dataset generation

Each dataset version simulates trajectories under randomized initial conditions
and regime-specific control-input profiles, then computes per-timestep features
(state, causal 1-step derivatives, `stall_margin = alpha_at_cl_peak - alpha`)
and a `future_stall_5s` label (whether the trajectory crosses the stall boundary
within the next 5 seconds), with trajectory-level train/val/test splitting
(zero trajectory-ID overlap, verified programmatically at every stage). Full
integrity checks (no NaN/Inf, no duplicate trajectory IDs, monotonic timestamps,
no ground-contact/negative-altitude violations, causal-derivative re-derivation)
were run and passed at every dataset version — see §22 and `outputs/dataset_audit*/`.

## 7. v0.1 baseline

First dataset generation (`scripts/generate_dataset.py`), 1,000 trajectories:
500 `normal`, 250 `stall`, 250 `boundary` (later renamed `near_boundary` in v0.2).
1,565,280 total rows; 187/1,000 trajectories (18.7%) crossed the stall boundary;
`future_stall_5s` positive rate 8.98% of available rows. Physical ranges:
alpha −43.99° to 78.47°, altitude 51.06m–2,139.76m (never near ground level —
v0.1 had no explicit ground-contact termination check).
(`outputs/dataset_audit/audit_report.md`)

## 8. v0.2 improvements

v0.2 (`scripts/generate_dataset_v2.py`) regenerated the dataset with the
`boundary` regime renamed `near_boundary` and its control-profile calibration
adjusted (`outputs/dataset_audit_v2_calibration/`). 1,000 trajectories: 500
`normal`, 250 `stall`, 250 `near_boundary`; 1,753,615 rows; 192/1,000 (19.2%)
crossed the boundary; positive rate 6.95%. Physical ranges: alpha −41.57° to
73.93°, altitude **0.14m–2,125.66m** (`outputs/dataset_audit_v2/audit_report_v2.md`).

A Stage-3 baseline ML pass on this data (`ml/train_baseline.py` +
`evaluate_baseline.py` → `outputs/ml_baseline/`) established the canonical
instantaneous-state baseline: best model RandomForest, test PR-AUC **0.742**,
precision 0.814, recall 0.604, F1 0.693, ROC-AUC 0.947 (AoA-threshold rule:
PR-AUC 0.599 at a 14.45° threshold). This baseline is what the Stage-4 temporal
experiment (§10) compares against. *(A second, parallel Stage-3 implementation
also exists — `outputs/ml/` — complete and independently valid but not wired
into any downstream stage; see `PROVENANCE.md` §4.)*

## 9. Ground-contact correctness fix

v0.1's dataset showed no trajectories anywhere near ground level (min altitude
51.06m) and tracked no `ground_contact` termination reason at all. v0.2 added
explicit ground-contact detection to the trajectory simulator: min altitude
dropped to 0.1354m and 2/1,000 v0.2 trajectories terminated via
`ground_contact` — the simulator now correctly detects and terminates
trajectories that reach the ground, rather than allowing altitude to run
arbitrarily close to or past zero unflagged. This fix was carried forward
unchanged into v0.3 (min altitude 0.0199m, ground-contact rate 19/3,150 = 0.6%,
`outputs/dataset_audit_v3/v03_generation_report.md`).

## 10. Initial temporal ML result

The Stage-4 temporal experiment on v0.2 data (`scripts/run_temporal_experiment.py`
→ `outputs/ml_temporal/temporal_experiment_report.md`) is the first attempt to
measure early-warning lead time, not just point-in-time classification. Result:
row-level recall 97–99% within 0.5s of the actual crossing, falling to 17.9%
(0.5–1s), 17.7% (1–2s), 26.0% (2–3s), 2.3% (3–4s), 0.0% (4–5s). Event-level:
14 discrete stall crossings in the usable test population, 100% event recall,
but **median credited lead time only 0.53s** (mean 0.81s). Primary model
(RandomForest, state + 1-step derivatives + 1s windowed features, 23 features):
PR-AUC 0.813, precision 0.900, recall 0.701, F1 0.788. A regime-exclusion check
(training without any `stall`-regime trajectory) collapsed stall-regime recall
67.4%→6.3% and event recall 100%→28.6% — an early signal of the
regime-specificity theme that recurs throughout this project.

## 11. Physics precursor diagnosis

A dedicated diagnosis (`outputs/precursor_diagnosis/`) traced the root cause of
the sub-second lead time directly through real v0.2 trajectories. Direction-aligned
analysis showed alpha essentially flat from 5s to ~1s before crossing in both
regimes that ever cross the boundary, rising sharply only in the final <1s
(median alpha 8°→16° transition: 0.54s in `near_boundary`, 0.33s in `stall`).
Separability AUC for individual physical variables (alpha, elevator,
stall_margin) stayed at 0.51–0.65 (near chance) at every lead time beyond ~1s in
the `stall` regime, and even `near_boundary`'s higher separability (AUC
0.78–0.99) was diagnosed as a *level* effect (crossing trajectories start at a
higher baseline alpha) rather than a *trend* effect (alpha visibly rising toward
the boundary) — meaning even the seemingly-separable signal was not the kind of
early-rising trend a genuine early-warning system needs. Conclusion: v0.2's
STALL_CONTROL_CONFIG's large-magnitude, long-hold elevator pulses drove a fast
transit through the precursor region — a control-profile timing artifact, not
evidence that the underlying dynamics cannot support a slower approach.

Two concurrent Claude Code sessions independently investigated this in the same
window and reached different initial verdicts (one NO-GO on rise-time-only
fixes, one conditional GO on a two-stage pulse design); the conflict and its
resolution are documented in full in `outputs/v03_calibration/reconciliation_report.md`
and summarized in `PROVENANCE.md` §3.

## 12. v0.3 motivation

Given the diagnosis in §11, the explicit next step was to test whether
*re-timing* the control-input profile — without touching the validated
aircraft physics, pitch model, or stall boundary — could produce trajectories
with a genuine 2–5 second precursor. This required a new regime
(`gradual_approach_v3`) and a multi-round calibration process to find a control
profile that produced a slow, monotonic approach to the boundary without
pathological side effects (runaway flight-path-angle excursions, dive-then-zoom
maneuvers).

## 13. v0.3 control-profile development

Five single-pulse candidates with lengthened elevator rise times were tested
first (30/candidate, 150 total): every candidate roughly tripled median transit
time (0.54s → 0.90–1.76s) but gamma-envelope termination jumped from v0.2's
22.7% baseline to 57–80%, and **zero of five candidates ever produced a single
≥3s precursor event** (`outputs/precursor_diagnosis/FINAL_REPORT.md`). A
parallel line of investigation (the concurrent "RUN A" session) tested a
two-stage, two-pulse design ("Candidate D") that performed substantially
better (22.9% crossing rate, 31.4% gamma-termination, headline 87.5% ≥3s
precursor rate) but this headline number was later found inflated ~2.5x by a
non-direction-aligned precursor metric that credited dive/zoom-recovery time as
precursor time; the corrected figure was 33.3% (`reconciliation_report.md`).
Two further fix rounds resolved the remaining issues: **v2** (same-sign,
zero-gap pulse sequencing) eliminated dive/zoom-climb crossings (0/40) but
regressed non-crossing gamma-termination (31.4%→57.7%); **v3** (7.0s combined
pulse-duration cap, trimming hold time only) cut non-crossing gamma-termination
by more than half (73.3%→32.5%, below the original 31.4% baseline) while
improving every precursor-quality metric on the crossings that do occur
(`candidate_d_final_gate_report.md`).

## 14. v0.3 calibration

Final Candidate D v3 calibration (n=175, seed 20260817,
`scripts/calibrate_candidate_d_v3.py`): crossing rate 12.0% (21/175),
gamma-termination 28.6% (down from v2's 57.7%, below v1's 31.4%), completion
rate 70.9%, ground-contact 0.6% (1 trajectory). Corrected (dip-aware,
direction-aligned) precursor metrics on the 13 usable crossings: median
onset→crossing 4.50s, ≥2s 61.5%, ≥3s 53.8%, ≥4s 53.8%, ≥5s 30.8%. Physical
classification: 100% (21/21) of crossings were clean gradual/monotonic
low-gamma approaches — zero dive-then-zoom-climb, zero runaway. **Decision:
CASE A — READY FOR FULL GENERATION**, with the caveat that the reduced 12.0%
crossing rate (vs. v1/v2's 22.9%) would require proportionally more total
trajectories to hit a target crossing count (`candidate_d_final_gate_report.md`).

## 15. v0.3 full dataset

Full generation (`scripts/generate_dataset_v3.py`, locked Candidate D v3
parameters, unmodified from calibration): **3,150 trajectories** (500 `normal` +
250 `stall` + 2,400 `gradual_approach_v3`, the 2,400 sized from the Wilson 95%
CI lower bound on crossing rate to guarantee at least v0.2's 192 total
crossings), **5,340,865 total rows**. Actual results: 317 `gradual_approach_v3`
crossings (13.2%), 153 `stall` crossings (61.2%), 470 total. `future_stall_5s`
positive rate 8.2%. At full scale: 194 usable crossings for the precursor
metric, median onset→crossing **4.38s**, ≥2s **66.0%**, ≥3s **59.3%**, ≥4s
**55.7%**, ≥5s 13.4% (dropped from calibration's 30.8% — expected, a small-n
artifact resolving at scale). Physical classification: 99.1% (314/317) clean
gradual/monotonic low-gamma crossings, 0.9% (3/317) runaway, 0% dive-then-zoom.
All integrity checks passed (§22). **Decision: READY for the temporal ML
experiment** (`outputs/dataset_audit_v3/v03_generation_report.md`).

## 16. v0.3 temporal ML results

`scripts/run_temporal_experiment_v03.py` (seed 20260817, reusing v0.2's frozen
model family/features/thresholding/event-definition procedure unchanged) →
`outputs/ml_v03/v03_temporal_ml_report.md`. Primary model (RandomForest, state +
derivatives + 1s window, 23 features, threshold 0.859, evaluated on 538,034 test
rows / 456 of 473 test trajectories):

| Metric | v0.2 | v0.3 |
|---|---|---|
| PR-AUC | 0.813 | **0.890** |
| Precision / Recall / F1 | 0.900 / 0.701 / 0.788 | 0.935 / 0.736 / 0.824 |
| Event recall | 100.0% (14/14) | **96.1% (73/76)** |
| Median credited lead time | 0.53s | **4.72s** |
| Warning coverage ≥2s | 14.3% | **64.5%** |
| Warning coverage ≥4s | 0.0% | **55.3%** |
| Row-level recall, 2–3s bucket | 26.0% | 48.2% |
| Row-level recall, 4–5s bucket | 0.0% | 48.4% |
| Episode-level false-alarm precision | 67.6% | 76.9% |

The false-positive character also changed: in v0.2, 100% of false positives sat
on trajectories that never stall (unambiguous noise); in v0.3, 70% of unique
false-positive trajectories *do* eventually cross the boundary elsewhere in
their telemetry — early/ambiguous rows on genuine gradual-approach shapes, a
reasonable cost of learning a real multi-second precursor rather than a red
flag. Physics-vs-ML consistency: median ML credited lead time (4.90s) tracks
median physical precursor (4.39s) closely at the population level for
`gradual_approach_v3`, though per-event correlation is only moderate (Pearson
r = 0.337, n=22) — the model behaves more like "this looks like the
gradual-approach shape, warn early" than a per-trajectory-calibrated timer.

## 17. Initial generalization failure

The same experiment's regime-exclusion check — Model D retrained with **all**
1,691 `gradual_approach_v3` TRAIN trajectories excluded, evaluated unchanged on
the full TEST split — is "the single most important finding" of that report:

| Metric | Full TRAIN | `gradual_approach_v3` excluded | Change |
|---|---|---|---|
| PR-AUC | 0.890 | 0.552 | −0.338 |
| Event recall | 96.1% (73/76) | 64.5% (49/76) | −31.6pp |
| Median credited lead time | 4.72s | 0.73s | −3.99s |
| Recall, 2–3s bucket | 48.2% | 1.8% | −46.4pp |
| Recall, 4–5s bucket | 48.4% | 2.4% | −46.0pp |
| Warning coverage ≥4s | 55.3% | 11.8% | −43.5pp |

Near-immediate (0–0.5s) detection degraded only modestly (97.2%→81.2%), but
every bucket beyond ~0.5s collapsed 20–40x. **Verdict: CASE B — the
in-distribution multi-second early-warning capability is real and large, but a
meaningful share of it is regime-shape memorization, not demonstrated to be a
transferable "rising alpha + shrinking margin" understanding** — this is the
open question the final experiment (§18) was designed to resolve.
(`outputs/ml_v03/v03_temporal_ml_report.md` §11)

## 18. Alternative-mechanism experiment

The regime-exclusion check answers "can the model learn a multi-second
precursor from *zero* exposure to any slow-approach example?" (no) — it cannot
distinguish memorizing Candidate D's exact two-pulse shape from learning a
transferable pattern. The final experiment (`outputs/ml_v03_generalization/`)
tests the sharper question directly: given exposure to *one* slow-approach
shape (Candidate D), does that skill transfer to a **structurally distinct**
slow-approach mechanism ("Candidate F": a single, duration-capped elevator
pulse producing one smooth monotonic alpha rise, vs. Candidate D's two-stage
"staircase")? `aeroguard_dataset/control_profiles_alt_single.py` reuses an
already-calibrated elevator spec, independently re-applies the same
duration-cap fix concept, and does not touch the physics engine, `config.py`,
or either Candidate D module. A 150-trajectory calibration passed its own
decision gate cleanly (0% dive-then-zoom/runaway, 100% clean crossings, 100%
≥2s / 62.5% ≥3s precursor coverage).

**Forward check** (frozen v0.3 model, never refit, evaluated on 293 held-out
alt-mechanism trajectories / 46 events, none seen in any form during training):
PR-AUC **0.835**, event recall **46/46 = 100.0%**, median credited lead time
**2.96s**, warning coverage ≥2s **89.1%**, ≥4s 37.0%.

**Reverse check** (one fresh RF trained only on alt-mechanism trajectories,
never seeing a single `gradual_approach_v3` example, evaluated on the frozen
v0.3 TEST split's held-out `gradual_approach_v3` rows): PR-AUC **0.708**, event
recall **87.0% (47/54)**, median credited lead time **5.00s (horizon cap)**,
warning coverage ≥2s 72.2%, ≥4s 46.3%.

## 19. Final CASE A result

| Experiment | PR-AUC | Event recall | Median lead (s) | Cov. ≥2s | Cov. ≥4s |
|---|---|---|---|---|---|
| v0.3 in-distribution | 0.890 | 96.1% | 4.72 | 64.5% | 55.3% |
| Regime-exclusion (zero exposure) | 0.552 | 64.5% | 0.73 | 22.4% | 11.8% |
| Forward: frozen model → novel mechanism | 0.835 | 100.0% | 2.96 | 89.1% | 37.0% |
| Reverse: alt-trained model → v0.3 gradual | 0.708 | 87.0% | 5.00 | 72.2% | 46.3% |

**Decision: CASE A — the model retains substantial multi-second warning
performance on the structurally novel mechanism**, in both directions, and does
not collapse the way the zero-exposure regime-exclusion check did. Forward PR-AUC
retains 94% of its in-distribution value; event recall is 100% in the forward
direction; median lead time remains solidly multi-second in both directions;
≥2s coverage in the forward direction (89.1%) exceeds the in-distribution figure
itself. The corrected interpretation of §17's finding: the model has learned a
signal that generalizes across different *timing/shape* realizations of a
slow alpha-rise-toward-boundary approach, but which still requires having seen
*some* member of that broader phenomenon class during training — a
**family-level generalization, not a zero-shot one**.
(`outputs/ml_v03_generalization/generalization_experiment_report.md`)

## 20. Limitations

- **Not a validated real-aircraft model.** All physics coefficients are
  plausible defaults for a small generic fixed-wing aircraft, not measured or
  fitted data for any real airframe; the model is 2D/longitudinal only (no
  roll, yaw, sideslip), uses constant air density, a linear pitch-response
  surrogate, and a linear throttle-to-thrust map.
- **Family-level, not zero-shot, generalization.** §19's transfer result
  required prior training exposure to *some* slow-approach mechanism; the
  regime-exclusion check (§17) shows the capability does not emerge from zero
  exposure to the phenomenon class.
- **`stall` regime remains an imminent-only detector** in both v0.2 and v0.3
  (0% recall beyond ~1s in both) — its own physical precursor is ~0.3s in both
  dataset versions; nothing in this project extended warning time for that
  regime specifically.
- **Per-event lead-time calibration is only moderate** (Pearson r=0.337,
  gradual_approach_v3, n=22) — the model tracks the *population* median
  precursor well but does not finely calibrate its warning time to each
  individual trajectory's actual onset.
- **False-positive character shifted in v0.3**: 70% of unique false-positive
  trajectories eventually cross the boundary elsewhere in their own telemetry,
  a reasonable byproduct of learning the approach shape but worth knowing
  before treating row-level FPR as the complete false-alarm picture.
- **Small absolute event counts persist even at v0.3 scale** relative to
  typical ML benchmarks (76 events in the v0.3 primary test population, 46/54
  in the two generalization directions) — percentages at this scale carry real
  but not enormous sampling uncertainty.

## 21. Threats to validity

- **Two concurrent development sessions produced conflicting v0.3 calibration
  results** partway through this project (§11, §13; full account in
  `reconciliation_report.md`). The conflict was independently reconciled with a
  corrected, direction-aligned precursor metric and full-window (not
  crossing-instant-only) gamma checks, and the resolution is traceable and
  documented — but it is a real threat to the independence of any single
  report's headline number, which is why this final report cites the
  reconciled/corrected figures throughout, not the original inflated ones.
- **A duplicate Stage-3 ML implementation exists** (`outputs/ml/` vs. the
  canonical `outputs/ml_baseline/`, §8, `PROVENANCE.md` §4) — both are
  complete and internally consistent, but only one was actually used downstream;
  citing the wrong one would misstate the v0.2 baseline.
- **The alternative mechanism (§18), while structurally distinct from
  Candidate D, was still designed by reusing an already-calibrated elevator
  spec and the same duration-cap fix concept** — it tests transfer across
  control-input *shape* within the same broad "slow elevator-driven approach"
  family, not transfer to a qualitatively different stall-inducing mechanism
  (e.g., turbulence-induced, asymmetric/lateral, or non-elevator-driven
  approaches, none of which this simulator models).
- **All results are simulation-internal.** No real flight data, wind-tunnel
  data, or independent aircraft model was used at any stage; every claim in
  this report is a claim about this specific simplified simulator, not about
  real aircraft.

## 22. Reproducibility

Every dataset version, calibration round, and ML experiment in this report ran
from a fixed seed (`20260817`, with disjoint seeds for the final experiment's
new calibration/holdout/train_val batches, documented in
`outputs/ml_v03_generalization/generalization_experiment_report.md` §3–4) and
is independently re-runnable from the versioned scripts. Integrity checks
passed at every dataset version: no NaN/Inf, no duplicate rows or trajectory
IDs, monotonic timestamps, zero train/val/test trajectory-ID overlap, causal
(non-leaking) derivative and label re-derivation spot-checks, no negative or
sub-zero altitude records. Full exact commands, seeds, and expected outputs are
in `REPRODUCIBILITY.md`. Current verified state: **190/190 tests passing**,
frozen physics/datasets/models confirmed unmodified (§Phase 7 integrity summary,
`outputs/final/FINAL_STATUS.md`).

## 23. Final conclusion

**The evidence supports multi-second stall early-warning and transfer across
structurally distinct control-input mechanisms producing the same underlying
physical phenomenon, but does NOT establish universal zero-shot stall
prediction across arbitrary unseen flight regimes.**

Concretely: (1) a physically credible multi-second stall precursor is
achievable in this simulator through control-input timing alone, without any
physics change; (2) a standard temporal ML model (RandomForest on state +
derivatives + short windowed history) learns to exploit that precursor
effectively when trained on data resembling its deployment population (event
recall 96.1%, median lead 4.72s); (3) that learned skill substantially
transfers — in both directions — to a structurally distinct control-input
mechanism producing the same physical stall approach (forward PR-AUC retains
94% of in-distribution value, 100% event recall); but (4) the skill does not
emerge from zero training exposure to the slow-approach phenomenon class at
all (PR-AUC collapses to 0.552, median lead time to 0.73s under exclusion).
This is a family-level physics generalization, not a universal one.

## 24. Future work

No further experiments are proposed or should be run automatically from this
report — this is a packaging/synthesis pass, not a research continuation. If
the project resumes, the natural next questions raised (but explicitly not
pursued) by the reports above are: (a) testing transfer to a qualitatively
different stall-inducing mechanism (not elevator-timing-driven at all); (b)
improving per-event lead-time calibration (currently only moderately
correlated with the true physical onset, r=0.337); (c) extending the physics
model beyond 2D/longitudinal dynamics or a constant-density atmosphere before
any real-aircraft-relevant claim could be considered; (d) investigating
whether the `stall` regime's inherently short (~0.3s) physical precursor can be
extended through its own control-profile timing analysis, analogous to what
this project did for `near_boundary`/`gradual_approach_v3`.

---

*Report assembled from, and citing, existing frozen experiment outputs only.
No numbers in this report were computed, adjusted, or estimated beyond what is
already recorded in the cited source files.*
