# AeroGuard

[![Live dashboard](https://img.shields.io/badge/live%20dashboard-open-2ea44f)](https://hanusharan.github.io/AeroGuard/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Tests](https://github.com/hanusharan/AeroGuard/actions/workflows/tests.yml/badge.svg)](https://github.com/hanusharan/AeroGuard/actions/workflows/tests.yml)
[![Stage: simulation research](https://img.shields.io/badge/stage-simulation%20research-orange)](#limitations)

**Physics-informed machine learning for early aircraft stall warning.**

A self-contained research pipeline asking one question: **can a physically
credible, multi-second precursor to an aerodynamic stall be predicted by a
machine-learning model before the stall occurs — and does that skill transfer
beyond the exact scenario it was trained on?**

AeroGuard is a small 2D longitudinal flight-dynamics simulator, a versioned
trajectory-dataset generator, and a temporal ML early-warning system, built and
evaluated end to end in this repository. **This is a simplified, educational
physics model — it is NOT a validated model of any real aircraft**, and no
result here should be read as a claim about real-aircraft behavior or safety.

[![Research DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22724022.svg)](https://doi.org/10.5281/zenodo.22724022)

**Research paper / DOI:** https://doi.org/10.5281/zenodo.22724022
**Experiment log:** [`experiments/EXPERIMENT_LOG.md`](experiments/EXPERIMENT_LOG.md)
**Live dashboard:** [hanusharan.github.io/AeroGuard](https://hanusharan.github.io/AeroGuard/) — interactive walkthrough of the datasets, models, and results.
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

## v1.1 check: reproduction, rule baselines and confidence intervals

Added after v1.0, without retraining or changing the frozen model
(`scripts/analysis_v11_baselines_and_ci.py`, outputs in `outputs/analysis_v11/`).

**Reproduction.** Regenerating the v0.3 dataset from code and scoring it with the
frozen model reproduces the published TEST results exactly: PR-AUC 0.8903,
73/76 events warned, median lead 4.72 s, 538,034 test rows.

**Baselines and 95% confidence intervals** (bootstrap over the 456 TEST
trajectories, 1,000 resamples; all three evaluated on the same TEST rows; rule
thresholds chosen on TRAIN/VAL only):

| Model | PR-AUC [95% CI] | Event recall [95% CI] | Median lead [95% CI] | False alarms per simulated flight hour |
|---|---|---|---|---|
| Temporal RandomForest (frozen v1.0) | 0.890 [0.852, 0.920] | 73/76, 96.1% [91.2%, 100%] | 4.72 s [3.35, 4.98] | 18.8 |
| Angle-of-attack threshold rule | 0.709 [0.668, 0.746] | 76/76, 100% | 2.08 s [0.91, 3.37] | 23.4 |
| Stall-margin + alpha-rate trend rule | 0.688 [0.650, 0.721] | 76/76, 100% | 3.91 s [3.22, 4.05] | 54.9 |

The model's PR-AUC advantage over the rules is clear (+0.18 [0.15, 0.22] over the
angle-of-attack rule; +0.20 [0.17, 0.23] over the trend rule). At their chosen
operating points the rules warn on every event, but later (angle-of-attack rule)
or with about three times as many false alarms (trend rule). Caveats: the
operating points differ, so a comparison at matched false-alarm rates is still
to do; the lead-time interval is capped by the 5 s labeling horizon; and the
false-alarm rate is measured on simulated test flights, many of which approach
a stall, so it is not a real-flight rate. 18.8 false alarms per hour would be
too many for a cockpit system.

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

The test suite runs automatically on every push via GitHub Actions (see the
Tests badge above). At v1.0 packaging, **190/190 tests passed** locally, covering the physics engine, dataset
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

## How this was built

> **Draft — Hanusharan to complete in his own words before publishing.**

- **Origin:** the idea came from conversations with my uncle, an aeronautical
  engineer (IIT Kharagpur), about why aircraft stall. [one or two sentences]
- **What I designed and decided myself:** [e.g. the research question, the
  decision to treat the short v0.2 precursor as a control-profile artifact,
  the cross-mechanism transfer test, the evaluation metrics]
- **Tools used, including AI assistants:** [name each tool and what it was
  used for, e.g. "AI coding assistants helped write and refactor parts of the
  pipeline and documentation; I reviewed, ran and checked every result"]
- **What I verified myself:** [e.g. re-ran tests, checked metrics against
  output files, inspected trajectories and plots]
- **Version history:** this repository was put under version control when the
  v1.0 work was packaged (September 2026), so earlier development is not in the
  git history. All work after v1.0 is committed incrementally.

## Research note / citation

This is an internal/independent research project, not peer-reviewed, not
flight-tested, and not a certified aviation safety tool. If referencing this
work, use the "Cite this repository" button (generated from `CITATION.cff`) and, for specific claims, cite the specific dated report
under `outputs/` that measured them — every number in the final report is
traceable to its source report and the exact script/seed that produced it.
