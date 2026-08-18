# AeroGuard

A self-contained research pipeline asking one question: **can a physically
credible, multi-second precursor to an aerodynamic stall be predicted by a
machine-learning model before the stall occurs — and does that skill transfer
beyond the exact scenario it was trained on?**

AeroGuard is a small 2D longitudinal flight-dynamics simulator, a versioned
trajectory-dataset generator, and a temporal ML early-warning system, built and
evaluated end to end in this repository. **This is a simplified, educational
physics model — it is NOT a validated model of any real aircraft**, and no
result here should be read as a claim about real-aircraft behavior or safety.

**Full synthesis:** [`outputs/final/AEROGUARD_FINAL_RESEARCH_REPORT.md`](outputs/final/AEROGUARD_FINAL_RESEARCH_REPORT.md)
**Project status:** [`outputs/final/FINAL_STATUS.md`](outputs/final/FINAL_STATUS.md)
**File provenance (canonical vs. historical vs. rejected-candidate):** [`PROVENANCE.md`](PROVENANCE.md)
**Exact reproduction commands:** [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md)

## Research question

Early datasets (v0.1/v0.2) produced stall crossings with a median 0.37–0.54s
transition from a warning-relevant angle of attack to the stall boundary — too
short for any model to learn a genuine multi-second early warning from. Was
that a fundamental limit of the simulated dynamics, or an artifact of *how*
control inputs were generated? And if a genuine multi-second precursor could be
engineered into the dataset, would an ML model's resulting early-warning skill
be a transferable understanding of the underlying approach-to-stall physics, or
a memorized fingerprint of one specific control-input shape?

## Key result

Slowing and re-timing the elevator control profile — without touching the
validated aircraft physics or stall boundary — produced a dataset (v0.3) with a
median 4.38s physical precursor (vs. v0.2's 0.54s). A temporal ML model trained
on it achieved **96.1% event recall at a median 4.72s lead time** (vs. v0.2's
100% recall at 0.53s). A final experiment tested whether this skill transfers
to a *structurally different* slow-approach control-input mechanism the model
never trained on: it retained **94% of its in-distribution PR-AUC and 100%
event recall** on the novel mechanism.

> **The evidence supports multi-second stall early-warning and transfer across
> structurally distinct control-input mechanisms producing the same underlying
> physical phenomenon, but does NOT establish universal zero-shot stall
> prediction across arbitrary unseen flight regimes.** A regime-exclusion check
> showed the multi-second skill collapses 20–40x when the model has *zero*
> training exposure to any slow-approach example — this is a family-level
> generalization, not a zero-shot one.

## Architecture

```
aeroguard/              physics engine: 5-state RK4 integrator, nonlinear
                         CL(alpha) with emergent stall, linear pitch-response
                         surrogate. Unmodified since Stage 1.
aeroguard_dataset/       control-profile generation, trajectory simulation at
                         scale, feature/label computation, splitting, auditing.
ml/                      baseline (instantaneous) + temporal (windowed
                         state+derivative) ML pipelines: RandomForest,
                         logistic regression, rule-based baselines.
scripts/                 one script per pipeline stage.
tests/                   190 tests covering physics, dataset generation, ML
                         pipelines, and leakage/integrity guards.
data/                    versioned trajectory datasets (v1/v2/v3) — large
                         binary files excluded from git, regenerable (see
                         REPRODUCIBILITY.md).
outputs/                 every experiment's reports, metrics, plots, models.
outputs/final/           this project's canonical synthesis (report, figures,
                         status).
```

See [`outputs/final/figures/01_aeroguard_pipeline.png`](outputs/final/figures/01_aeroguard_pipeline.png)
for the full data-flow diagram.

## Dataset versions

| Version | Trajectories | Rows | Regimes | Key change |
|---|---|---|---|---|
| v0.1 | 1,000 | 1,565,280 | normal / stall / boundary | first generation, no ground-contact check |
| v0.2 | 1,000 | 1,753,615 | normal / stall / near_boundary | ground-contact fix, regime rename/recalibration |
| v0.3 | 3,150 | 5,340,865 | normal / stall / gradual_approach_v3 | new slow-approach regime, engineered multi-second precursor |

## ML approach

RandomForest classifiers (`n_estimators=200, max_depth=12, min_samples_leaf=5,
class_weight=balanced_subsample`) predicting `future_stall_5s` (whether the
trajectory crosses the stall boundary within 5s), trained/thresholded on
TRAIN/VAL only and evaluated once on a held-out, trajectory-level TEST split
(zero trajectory overlap between splits, verified programmatically). Two model
families: an **instantaneous baseline** (8 state features) and a **temporal
model** (23 features: state + causal 1-step derivatives + 1s causal windowed
statistics). Event-level metrics use an episode-based, 5-second-horizon-capped
lead-time definition, unchanged across every dataset version for comparability.

## Headline metrics

| Metric | v0.2 (baseline) | v0.3 (final) |
|---|---|---|
| PR-AUC (primary model) | 0.813 | **0.890** |
| Event recall | 100.0% (14/14) | 96.1% (73/76) |
| Median credited lead time | 0.53s | **4.72s** |
| Warning coverage ≥2s | 14.3% | **64.5%** |
| Warning coverage ≥4s | 0.0% | **55.3%** |

## Generalization result

| Check | PR-AUC | Event recall | Median lead |
|---|---|---|---|
| v0.3 in-distribution | 0.890 | 96.1% | 4.72s |
| Zero-exposure exclusion (regime removed from TRAIN) | 0.552 | 64.5% | 0.73s |
| Forward: frozen model → novel control-input mechanism | 0.835 | **100.0%** | 2.96s |
| Reverse: mechanism-only-trained model → v0.3 gradual regime | 0.708 | 87.0% | 5.00s (cap) |

Cross-mechanism transfer (forward/reverse) retains the large majority of
in-distribution performance; zero-exposure exclusion collapses it. See
§17–19 of the final report for full interpretation.

## Repository structure

See the tree in [Architecture](#architecture) above and
[`PROVENANCE.md`](PROVENANCE.md) for exactly which files are canonical,
which are superseded-but-kept historical milestones, and which are rejected
calibration candidates preserved as part of the documented decision trail (a
significant part of this repository's history is two concurrent development
sessions producing genuinely conflicting v0.3 calibration results, later
reconciled — nothing was ever deleted, only reconciled and documented).

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Reproduction commands

Full exact commands, seeds, and expected outputs for every stage are in
[`REPRODUCIBILITY.md`](REPRODUCIBILITY.md). Quick start (physics demo only,
seconds to run):

```bash
python scripts/simulate.py          # one trajectory, saves outputs/trajectory.png
```

Regenerating any full dataset or ML experiment (minutes, `data/` is not
tracked in git) is documented per-stage in `REPRODUCIBILITY.md` — e.g. the
final v0.3 temporal experiment took ~22 minutes wall-clock on the original run.

## Testing

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Current state: **190/190 tests passing**, covering the physics engine, dataset
generation (all three versions, including leakage/integrity guards), the ML
pipelines, and the final generalization experiment's control-profile mechanism.

## Limitations

Not a validated real-aircraft model (2D/longitudinal only, constant air
density, linear pitch-response surrogate, plausible-not-measured coefficients).
The demonstrated generalization is family-level (transfer across
control-input *shapes* within the same broad slow-approach phenomenon), not a
zero-shot result across arbitrary unseen regimes. All results are
simulation-internal — no real flight or wind-tunnel data was used at any
stage. Full limitations and threats to validity: §20–21 of the final report.

## Research note / citation

This is an internal/independent research project, not peer-reviewed, not
flight-tested, and not a certified aviation safety tool. If referencing this
work, cite the repository and, for specific claims, the specific dated report
under `outputs/` that measured them — every number in the final report is
traceable to its source report and the exact script/seed that produced it.
