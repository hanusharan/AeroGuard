# Changelog

Notable changes to the AeroGuard repository, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

The first release is prepared as **v1.1.0** but has not been tagged or published:
no Git tag and no GitHub release exists (checked 2026-10-24). Earlier entries are grouped by commit
date taken from Git history; the version labels used for them are
the ones the repository itself uses ("v1.0" for the frozen research packaging,
and v0.1–v0.3 for the datasets). The v0.1–v0.3 research was done before the
first commit, so Git history does not record when it happened — see
[`experiments/EXPERIMENT_LOG.md`](experiments/EXPERIMENT_LOG.md) for the research chronology.

This file covers the repository as a whole. The research paper has its own
build notes in [`paper/CHANGELOG.md`](paper/CHANGELOG.md).

## [Unreleased]

## [1.1.0] — not yet released (prepared 2026-10-24)

Prepared as the first tagged release; the tag has not been created. It preserves the v1.0 research record (Zenodo DOI
10.5281/zenodo.22724022) and adds the integrity, reproduction and evaluation
work listed in the dated entries below. No v1.0 result was changed.

- **Paper:** event-metric scope wording applied (from
  `paper/PROPOSED_AMENDMENT_event_metrics_scope.md`; wording only, no number
  changed). The PDF was rebuilt and now shows the correct repository URL,
  `github.com/hanusharan/AeroGuard`.
- **Evaluation after v1.0:** Phase 3 baselines, Items 33–42 and the Phase 4
  generalisation study (Items 43–53, merged from PR #4) are summarised in the
  README section "Evaluation after v1.0".
- **Dashboard:** launch-readiness and accessibility fixes (PR #3); a Phase 4
  "Generalisation Study" section (values exported by
  `dashboard/data_export/export_phase4.py` and checked by
  `parity/check_metrics.mjs`, 176/176); the stale "Next Research Stage" section
  replaced by "Open Questions"; sections renumbered (two were numbered 10);
  timeline extended to ten stages; a "simulator comparisons are not
  validation" limitation; the causal-claim sentence qualified to the
  simulator; desktop navigation moved to 1280 px and wider, because between
  1024 and about 1074 px it clipped the "Key Result" button.
- **CITATION.cff:** version 1.1.0 and release date were added in `30e7732`, then
  removed again in the Phase A audit because no release exists yet; they are to be
  added when the tag is created.
- **Excluded from this release (author decision):** the Item 50 final report,
  which is not in the repository, and the author's contribution statement:
  `AUTHOR_STATEMENT.md` remains an unfinished template, not linked from the README.
- **Phase A audit of Phase 4 (documentation only):**
  - Added `reports/PHASE_A_FINAL_AUDIT.md` and `reports/PHASE_A_STATUS.md`.
  - Qualified the Phase 4 wording in `README.md`, `dashboard/public/docs/AEROGUARD_README.md` and the website section `Phase4.tsx`: a second simulator model rather than an independent simulator; 20 model fits over 6 partition × data combinations; intervals describe flights within the tested configurations; lead time compared at unmatched false-warning rates (1.7–4.2×); scope of row PR-AUC and of the event population.
  - Added a Phase 4 section to `REPRODUCIBILITY.md`.
  - Documented in `baselines/README.md` and `REPRODUCIBILITY.md` (level 0) that the baseline check fails on the paper PDF since `30e7732`, giving the manifest hash and the current hash. The frozen manifest is unchanged.
  - Corrected the v1.1.0 wording: it is prepared, not yet tagged or released. Removed `version` and `date-released` from `CITATION.cff` until the tag exists, as `CONTRIBUTING.md` requires.
  - Corrected the CI expected-result statements in `README.md`, its public copy and `REPRODUCIBILITY.md`: since `30e7732`, CI gives 326 passed, 1 failed (`test_all_79_baseline_hashes_pass`, because of the rebuilt PDF), 24 skipped, 11 deselected.
  - Resolved the CI failure from the rebuilt PDF without touching `baselines/v0.3.sha256`. The baseline PDF bytes were recovered from Git into `paper/archive/AeroGuard_Research_Paper_baseline_v0.3.pdf`. New `baselines/paper_pdf_v1.1.0.sha256` records both PDFs. `test_all_79_baseline_hashes_pass` now pins the frozen manifest's own hash and verifies all 79 historical digests (the PDF via the recovered copy) plus the current PDF. CI selection: 327 passed, 24 skipped, 11 deselected (local run).
  - No number, result file, frozen artifact, protocol or model code was changed. Reasoning in `RESEARCH_LOG.md` RL-009.

### Changes included in 1.1.0 (previously unreleased)

### Added — Phase 4 (Items 43–53), 2026-10-15

- **Protocol and deviations:** `experiments/phase4/PROTOCOL.md` (committed before any data), `DEVIATIONS.md` (P4-D1 to P4-D5, written before the affected data were scored), `PARAMETER_RANGES.md`, `SIMULATOR_ASSUMPTIONS.md`, `published_reference.json`.
- **Code:** `phase4/` package (configuration design, density-aware simulation tested bit-identical to the original at sea-level density, models, metrics with trajectory bootstrap, abstention and conformal tools, JSBSim harness); `scripts/phase4_generate.py`, `scripts/phase4_generate_jsbsim.py`, `scripts/run_phase4.py`, `scripts/phase4_item50.py`; `tests/test_phase4_core.py` (20 synthetic tests). No frozen module, dataset, model or stored result was changed.
- **Dependency:** `jsbsim` 1.3.2 is needed only for the JSBSim stage; it is not added to `requirements.txt`.
- **Results:** `outputs/phase4/run_20261015T152932Z/` (report and machine-readable results; datasets, fitted models and score arrays are not committed). Interpretation in `RESEARCH_LOG.md` RL-008.

Local, **uncommitted** working-tree changes. Nothing here has been committed,
pushed, deployed, merged or published. These are documentation and engineering
safeguards only: no scientific method, dataset, experimental result or trained
model was changed, and no experiment, training run or dataset generation was
re-run in the repository (reproduction checks were run in scratch copies outside
it; see RL-001 and RL-006 in `RESEARCH_LOG.md`).

### Added

- **Software license:** [`LICENSE`](LICENSE) (MIT, copyright Bulusu Hanu
  Sharan). The README states it is intended to cover the source code only, not
  the paper, report text or figures.
- **Citation metadata:** [`CITATION.cff`](CITATION.cff) (CFF 1.2.0) naming the
  author, repository and the paper's DOI (10.5281/zenodo.22724022) as the
  preferred citation. It passed `cffconvert --validate` in a temporary
  environment; whether that DOI is a version or concept DOI is unconfirmed.
- **Pinned environment:** [`requirements-pinned.txt`](requirements-pinned.txt),
  a full `pip freeze` tested with CPython 3.12.3 on Linux x86_64. Only
  scikit-learn 1.9.0 is backed by repository evidence (it is recorded in the
  frozen v0.3 model and in `outputs/ml/metrics/test_lock.json`); every other
  version is newly selected. It is not a reconstruction of the original
  research environment. `requirements.txt` is unchanged.
- **Test workflow:** [`.github/workflows/tests.yml`](.github/workflows/tests.yml)
  runs the pytest suite on pull requests, pushes to `main` and manual dispatch,
  with read-only permissions. **It has not yet run on GitHub.** Locally, with
  the same command, 190 tests were collected and the result was 155 passed, 24
  skipped, 11 deselected, 0 failed (191 passed once the audit tests below were
  added). The 11 deselected tests need gitignored
  dataset files (ten need `data/processed/processed_dataset_v2.parquet`, one
  needs `data/ml/ml_dataset_v2.parquet`) and were not run against real data.
  Actions are pinned to major-version tags, not commit SHAs.
- **README test badge:** the live GitHub Actions status for `tests.yml`
  replaces the hardcoded "190/190 passing" badge. It reflects the workflow's real
  status once a run exists.
- **Dashboard safeguards:** a simulation-only notice under the hero buttons, and
  a footer stating the research-only status, the author, that no institutional
  affiliation or endorsement is claimed, and the AI-assistance link.
- **Authorship and AI disclosure:** README sections "Authorship and
  contributions" and "AI assistance". They state that the research idea is the
  author's and that Claude Code assisted with building and implementing the
  project, and they keep the documented Claude Code involvement in the v0.3
  calibration investigation. The extent of AI assistance in individual research
  decisions and manuscript passages is stated as unrecorded.
- **Reproduction guide:** [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) now explains
  what a clean checkout contains, defines six reproduction levels, says to run
  stages in a scratch copy (scripts overwrite tracked outputs otherwise), and adds
  troubleshooting. It records a reproduction run on 2026-10-12 in a scratch
  copy (CPython 3.12.3): regenerated v0.2 and v0.3 datasets have the documented
  row counts and identical split manifests (float values agree to about 1e-12);
  `pytest tests/` gave 190 passed with the regenerated data; and the frozen
  model re-scored on the regenerated v0.3 TEST data matched the published event
  metrics, with PR-AUC equal to about ten significant digits. This is the same
  code and author on another machine, not an independent replication. The model
  was not retrained and the generalization stage was not rerun.
- **v0.3 baseline manifest:** [`baselines/v0.3.sha256`](baselines/v0.3.sha256)
  (79 SHA-256 hashes, checked with `sha256sum -c`) and
  [`baselines/README.md`](baselines/README.md) define the v0.3 baseline and what
  it does not cover (the gitignored data and the original environment). No
  frozen file was modified and no Git tag was created.
- **Contributor guide:** [`CONTRIBUTING.md`](CONTRIBUTING.md) with a commit
  convention and a "Versions and releases" section that separates the research
  baseline, the "v1.0" label, the paper, software releases and dashboard
  labels, and lists the steps before a release. No release exists or has been
  prepared for publication.
- **Research log:** [`RESEARCH_LOG.md`](RESEARCH_LOG.md) with rules, a template and
  a retrospective index of the v0.1–v0.3 research (entry RL-001 records the
  reproduction run above; RL-002 to RL-007 record the later audits, the
  threshold-selection audit, the Item 26 reproduction check on regenerated data
  and the reproducibility report).
- **Reproducibility report:** [`REPRODUCIBILITY_REPORT.md`](REPRODUCIBILITY_REPORT.md)
  consolidates the v0.3 evidence: the stored results, the Item 26 check in which
  the frozen model was re-scored on regenerated data (all preregistered gates
  passed; confusion matrix and ROC-AUC exact, PR-AUC within 8.39e-11), the event
  population and shared-warning limits, the five-row bucket finding, and what
  cannot be established (original score arrays, the threshold-selection record,
  historical chronology, independent replication). It adds no new result and
  changes no stored metric, model or definition.
- **Audit tests:** [`tests/test_audit_labels_features_splits.py`](tests/test_audit_labels_features_splits.py)
  and [`tests/test_audit_event_metrics.py`](tests/test_audit_event_metrics.py) add 36 small tests with no
  dataset dependency: label window boundaries, whole-pipeline future-sample
  perturbation of the 23 model inputs, the frozen model's input list, tracked split
  manifests (including exact regeneration from IDs and seed), and event, lead-time
  and false-alarm accounting on hand-calculated cases. The local CI selection is now
  191 passed, 24 skipped, 11 deselected. They pin down current behavior, such as
  events removed by evaluation masks and the absence of a persistence requirement;
  they do not change any definition. No scientific code was modified.
- **Test-quality notes:** [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) now documents
  the CI test policy and known test gaps: no tests reference `ml/evaluation.py`,
  `ml/training.py`, `ml/ablation.py` or `aeroguard_dataset/features.py`, the
  real-data integrity checks skip on a clean checkout, nothing checks the
  frozen metrics files against the reported headline numbers, and the dashboard
  physics parity harness is not run in CI. That harness
  (`node dashboard/parity/check.mjs`) passed 420/420 checks locally.

### Changed

- README: the Python badge is now 3.12+ (the pinned numpy 2.5.4 requires it;
  it previously said 3.9+); installation points to
  `requirements-pinned.txt`; the "190/190 tests passing" statement is
  reframed as an unverified historical claim, with the clean-checkout result.
- README and `REPRODUCIBILITY.md`: removed instruction-style wording left over
  from the original packaging ("per the explicit … instruction", "packaging
  pass") and replaced an opaque aside about "concurrent sessions" with a pointer
  to the reconciliation records. Frozen reports, `PROVENANCE.md` and
  `FINAL_STATUS.md` were not edited.
- `dashboard/public/docs/AEROGUARD_README.md` (public copy of the README): the
  "190/190 passing" line now carries the same unverified-historical caveat.
- Dashboard footer: the paper title now matches the paper's actual title.

- README: the event metrics now state their evaluation scope. The headline recall
  (73 of 76 evaluated events) and median lead time (over the 73 warned events only)
  are explained under "What the event metrics cover", including the ten test
  crossings that fall in the last 5 s of their trajectories and so are outside the
  evaluated rows. All figures come from existing frozen metrics and tracked
  metadata; no result or definition changed. The dashboard's Key Results,
  Intervention, Problem, Flight Replay and Generalization text and its public
  README copy carry the same labels (recall over evaluated events, median lead
  time over warned events), with a short "Reading the event metrics" panel. A draft wording change for the paper
  is in [`paper/PROPOSED_AMENDMENT_event_metrics_scope.md`](paper/PROPOSED_AMENDMENT_event_metrics_scope.md)
  (proposal only; the paper and PDFs are unchanged).

### Fixed

- The paper's repository URL (`github.com/BulusuHanuSharan/AeroGuard`) was
  wrong in the source and its HTML renderings; it is now
  `github.com/hanusharan/AeroGuard` in `paper/AeroGuard_Research_Paper.md`,
  `paper/AeroGuard_Research_Paper.html` and
  `dashboard/public/paper/AeroGuard_Research_Paper.html`.

### Outstanding (not done)

- The published PDF (`paper/` and `dashboard/public/paper/`) and the Zenodo
  record still show the old repository URL. They need a rebuilt PDF and a new
  Zenodo version, which are external steps.
- The GitHub Actions workflow has not been run, so no remote test result exists.
- The historical "190/190 passing" result was reproduced only in a scratch copy
  with regenerated data, by the same author's code; it has not been repeated
  independently or in GitHub Actions, and passing tests do not reproduce any
  research result.
- An unmerged remote branch, `credibility-v1.1`, contains overlapping changes
  (`LICENSE`, `CITATION.cff`, a test workflow, the paper link, the hero text, a
  README section) and new analyses. It must be reconciled with this work before
  anything is merged or released.
- No software release, tag or version number exists or has been chosen.

## 2026-09-12

- Added a chronological research record,
  [`experiments/EXPERIMENT_LOG.md`](experiments/EXPERIMENT_LOG.md), summarizing
  the documented v0.1 → v0.3 experiments with no new measurements.
- README and dashboard: added links to the DOI, the experiment log and the GitHub
  repository, and a "Research record" card.
- Dashboard: added a "Next Research Stage" section describing a **proposed**
  v0.4 experiment (transfer across simulated aircraft parameters). It is future
  work only; no v0.4 results exist.

## 2026-09-05

- README: added a header block and a link to the live dashboard
  (commit `52a27fa`).

## 2026-08-31

- Consolidated project state (commit `47bc562`): added the research paper
  (Markdown source, HTML, PDF, figures and build scripts), the interactive
  stall simulator on the dashboard, and a dashboard physics-parity harness that
  compares the dashboard's TypeScript physics against the Python engine. The
  deploy workflow gained a check that the published paper files are present.

## 2026-08-18

- Initial commit: a pre-cleanup snapshot of the research repository holding the
  v0.1, v0.2 and v0.3 work (commit `297f6ac`). The message records "190/190
  tests passing" at that time; that claim has not been independently
  re-verified (see Unreleased).
- Packaged the "v1.0" frozen research record (commit `d636a8c`): final research
  report, final status, provenance and reproducibility documents, figures and a
  rewritten README. This is a label used in the commit message and the
  dashboard, not a tagged release. The v0.3 headline results it reports (event
  recall 96.1% at a 4.72s median credited lead time, PR-AUC 0.890, from the
  frozen model `outputs/ml_v03/models/primary_model_D_1s.joblib`) come from the
  existing frozen outputs; the packaging did not re-run experiments.
- Added the public research dashboard and its GitHub Pages deployment workflow,
  followed by build and base-path fixes.
