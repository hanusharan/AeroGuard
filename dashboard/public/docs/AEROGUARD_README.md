# AeroGuard

[![Live dashboard](https://img.shields.io/badge/live%20dashboard-open-2ea44f)](https://hanusharan.github.io/AeroGuard/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![License: MIT (code)](https://img.shields.io/badge/license-MIT%20(code)-blue.svg)](#license)
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
on it achieved **96.1% event recall** (73 of 76 evaluated events) **at a median
4.72s lead time among the warned events** (vs. v0.2's 100% recall at 0.53s; the
event population and these definitions are explained under
[Headline metrics](#headline-metrics)). A final experiment tested whether this skill transfers
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
tests/                   226 tests (the original 190 plus 36 research-audit
                         tests) covering physics, dataset generation, ML
                         pipelines, leakage/integrity guards and audit checks.
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
| Event recall (evaluated events) | 100.0% (14/14) | 96.1% (73/76) |
| Median credited lead time (warned events only) | 0.53s | **4.72s** |
| Warning coverage ≥2s | 14.3% | **64.5%** |
| Warning coverage ≥4s | 0.0% | **55.3%** |

### What the event metrics cover

The event metrics above describe the **evaluated test events**, not every stall
crossing in the test split (definitions in `ml/events.py`; counts from
`outputs/ml_v03/metrics/primary_model_metrics.json`,
`physics_vs_ml_summary.json` and `data/metadata/trajectory_metadata_v3.csv`).

- **Evaluated population.** Predictions are scored only on rows whose
  `future_stall_5s` label exists (the last 5 s of every trajectory has no
  complete future window) and that have a full 1 s feature window. 456 of the 473
  test trajectories have at least one such row. An "event" is a maximal run of
  unsafe samples, so the 76 events are 57 first crossings (one per trajectory)
  plus 19 second episodes in trajectories that re-enter the unsafe region.
- **Events outside the evaluated rows.** The frozen report lists 67 test
  crossings, of which 57 are in the evaluated rows. The other 10 are first
  crossings in 10 different test trajectories (8 `stall`, 2
  `gradual_approach_v3`) that occur in the last 5 s of the trajectory, so they
  fall outside the evaluated rows. They are counted neither as warned nor as
  missed. Later episodes in these trajectories also fall outside the evaluated
  rows, but the available metadata does not establish how many such episodes
  there are. The effect of these events on the reported recall has not been
  measured.
- **Recall.** 73 of the 76 evaluated events were warned and 3 were missed.
  The frozen per-regime summary counts 54 of the 57 first crossings as warned
  (37 of 40 in `gradual_approach_v3`, 17 of 17 in `stall`), so, by subtraction,
  all three misses are `gradual_approach_v3` first crossings and all 19 second
  episodes were warned. A warning that is still active when a trajectory re-enters the unsafe
  region can be credited to both events; the stored results do not show how often
  that happened.
- **Lead time.** The 4.72s median is taken over the 73 warned events only;
  missed events have no lead time and are not included (mean 3.42s, range
  0.14–5.0s, 29 of the 73 at the 5s cap). Lead time is capped at the 5s label
  horizon, and any warning that starts before the crossing and is active within
  the 5s window counts, with no minimum duration. Warning coverage ≥τ is measured
  over all 76 evaluated events.

## Generalization result

| Check | PR-AUC | Event recall | Median lead (warned events) |
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
calibration candidates preserved as part of the documented decision trail.
During v0.3 calibration, two independent investigations reached conflicting
results that were later reconciled; nothing was deleted, and the conflict and
its resolution are documented in `outputs/v03_calibration/reconciliation_report.md`
and `PROVENANCE.md` §3.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-pinned.txt   # exact, tested set (Python 3.12)
# or: pip install -r requirements.txt    # loose lower bounds
```

The pinned set needs Python 3.12 or newer (numpy 2.5.4 requires 3.12; the pinned
scikit-learn 1.9.0, the version recorded in the frozen v0.3 model, requires 3.11).
Python 3.11 with the loose `requirements.txt` has not been tested.
`requirements-pinned.txt` is a newly tested environment, not a reconstruction of
the original research environment — see
[`REPRODUCIBILITY.md`](REPRODUCIBILITY.md#pinned-environment).

## Reproduction commands

Full exact commands, seeds, and expected outputs for every stage are in
[`REPRODUCIBILITY.md`](REPRODUCIBILITY.md); what has and has not been reproduced is
summarized in [`REPRODUCIBILITY_REPORT.md`](REPRODUCIBILITY_REPORT.md). Quick start
(physics demo only, seconds to run):

```bash
python scripts/simulate.py          # one trajectory, saves outputs/trajectory.png
```

Regenerating any full dataset or ML experiment (minutes, `data/` is not
tracked in git) is documented per-stage in `REPRODUCIBILITY.md` — e.g. the
final v0.3 temporal experiment took ~22 minutes wall-clock on the original run.

## Testing

```bash
pip install -r requirements-pinned.txt
pytest tests/ -v
```

The test suite now collects 226 tests: the original 190-test suite plus 36
research-audit tests added after the v1.0 packaging
(`tests/test_audit_labels_features_splits.py` and
`tests/test_audit_event_metrics.py`). The "190/190" figure below refers only to
the original suite. The v1.0 status record
(`outputs/final/FINAL_STATUS.md`) reports "190/190 passing" in a working copy
that held the locally generated (gitignored) datasets; that is a historical claim and has not been independently
re-verified. On a clean checkout, 11 tests fail because gitignored data is
missing (10 need `data/processed/processed_dataset_v2.parquet`; 1,
`test_feature_schema_matches_actual_columns`, needs
`data/ml/ml_dataset_v2.parquet`), and 24 data-conditional tests skip. The [Tests workflow](.github/workflows/tests.yml) therefore runs the
suite with those 11 explicitly deselected (details in `REPRODUCIBILITY.md`); its
expected result is 191 passed, 24 skipped, 11 deselected (155 original tests plus
the 36 audit tests passing).
Passing tests do not by themselves reproduce any research result.

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

## Authorship and contributions

AeroGuard is an independent research project. The research idea is the
author's own: Bulusu Hanu Sharan conceived the project and is the sole listed
author of the [paper](https://doi.org/10.5281/zenodo.22724022) and the
repository owner. No institutional affiliation is claimed. The project was
built and implemented with the assistance of Claude Code (see
[AI assistance](#ai-assistance)).

The project's contributions, as stated in the paper (§1) and documented in the
[final report](outputs/final/AEROGUARD_FINAL_RESEARCH_REPORT.md) and
[experiment log](experiments/EXPERIMENT_LOG.md), are:

- a simulation and dataset pipeline that measures the physical precursor
  duration directly instead of assuming it;
- a diagnosis attributing the short precursor in the v0.2 dataset to
  control-profile timing rather than to the dynamics;
- a control-input intervention (v0.3) that changed only the elevator profile
  and left the physics engine untouched;
- a two-direction transfer test that separates family-level generalization from
  zero-shot prediction;
- the versioned datasets, tests, provenance and reproducibility records in
  this repository.

The underlying methods (RK4 integration, RandomForest and logistic-regression
classifiers, standard evaluation metrics) are standard techniques; the
contribution is their application and the experimental design above. The
repository record does not show which individual analyses, design decisions or
passages of text were produced by the author directly and which with Claude
Code's assistance.

## AI assistance

The research idea for AeroGuard is the author's. Claude Code, an AI coding
assistant from Anthropic, assisted with building and implementing the project.
Claude Code did not originate the research question, and its use is not
independent verification of any result. What the repository documents:

- The v0.3 control-profile calibration was investigated by two concurrent
  Claude Code sessions whose conflicting verdicts were reconciled (final report
  §11, §13, §21; `PROVENANCE.md` §3).
- Claude Code has assisted with repository engineering and documentation,
  including the licensing, citation, CI, dependency-pinning, dashboard-attribution
  and documentation changes made after the v1.0 research packaging.

The repository does not record, task by task, which experimental design
choices, analyses, model-selection decisions or manuscript passages were made
with Claude Code's assistance, so this document does not claim that any of them
were made without it. Every quantitative result traces to the frozen reports,
scripts and seeds cited above.

## License

The software in this repository is released under the [MIT License](LICENSE)
(Copyright (c) 2026 Bulusu Hanu Sharan). The license is intended to cover the
source code (`aeroguard/`, `aeroguard_dataset/`, `ml/`, `scripts/`, `tests/`,
`dashboard/` source). It does **not** grant rights to the research paper, report
text, figures, or other documents, and it makes no statement about the validity
of the research or the suitability of the software for any aviation use. Those
materials have no separate license yet; contact the author for reuse.
