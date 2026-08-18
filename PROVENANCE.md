# AeroGuard — Code & Artifact Provenance

This document exists because the repository's history includes real experimental
dead ends, two genuinely concurrent Claude Code sessions that produced conflicting
implementations of the same stage, and multiple versioned datasets that are all
still valid and referenced. Per the project's own reconciliation reports, **nothing
has been deleted** from this repository at any stage — every file below is either
part of the live pipeline or a documented, still-imported, still-tested part of the
decision trail that produced it. This file is the map.

No source file was moved or archived during the v1.0 packaging pass: every module
listed as "historical" or "superseded" below is still imported by another module,
exercised by a currently-passing test, or both — physically relocating it would
break `pytest` without improving clarity. Documentation, not relocation, is the
safe form of cleanup here.

## 1. The canonical v0.3 pipeline (what actually produced the final results)

| Stage | Canonical module(s) |
|---|---|
| Physics engine | `aeroguard/aerodynamics.py`, `dynamics.py`, `aircraft.py`, `integrator.py` — unmodified since Stage 1 |
| Shared generation primitives | `aeroguard_dataset/config.py`, `control_profiles.py`, `dataset_builder.py` (schema/utilities, reused by v3), `events.py`, `features.py`, `labeling.py`, `paths.py`, `splitting.py`, `trajectory_sim.py`, `audit.py`, `visualize.py` |
| v0.3 `gradual_approach_v3` regime | `aeroguard_dataset/control_profiles_candidate_d_v3.py` (the winning "Candidate D v3": two-pulse, same-sign, zero-gap, 7.0s duration-capped) |
| v0.3 dataset generation | `aeroguard_dataset/dataset_builder_v3.py`, `scripts/generate_dataset_v3.py` → `data/{raw,processed}/*_v3.parquet`, `data/metadata/*_v3.*`, `data/splits/split_manifest_v3.csv` |
| v0.3 dataset audit | `scripts/audit_v3_precursor.py` → `outputs/dataset_audit_v3/` |
| Baseline ML (feeds temporal stages) | `ml/train_baseline.py` + `ml/evaluate_baseline.py` (+ shared `ml/baselines.py`, `calibration.py`, `evaluation.py`, `metrics.py`, `models.py`, `plots.py`) → `outputs/ml_baseline/` |
| Temporal ML (v0.2, reference) | `ml/temporal_config.py`, `temporal_data.py`, `temporal_features.py`, `temporal_experiment.py`, `temporal_plots.py`, `scripts/run_temporal_experiment.py` → `outputs/ml_temporal/` |
| Temporal ML (v0.3, final) | `ml/temporal_config_v03.py`, `temporal_data_v03.py`, `temporal_experiment_v03.py` (+ reuses the v0.2 modules above unchanged) `scripts/run_temporal_experiment_v03.py` → `outputs/ml_v03/`, incl. `models/primary_model_D_1s.joblib` (the frozen final model) |
| Cross-mechanism generalization (final experiment) | `aeroguard_dataset/control_profiles_alt_single.py`, `scripts/calibrate_alt_single.py`, `generate_alt_single_dataset.py`, `run_alt_generalization_experiment.py` → `outputs/ml_v03_generalization/` |

## 2. Historical milestones — kept, not superseded, actively referenced

v0.1 and v0.2 are not "old versions to discard" — every v0.3 report compares
against them directly, and the temporal-ML final report's headline claim (v0.2:
0.53s median lead time → v0.3: 4.72s) requires the v0.2 artifacts to remain intact.

- `scripts/generate_dataset.py` (v0.1) → `data/{raw,processed}/*.parquet` (no suffix), `outputs/dataset_audit/`
- `scripts/generate_dataset_v2.py`, `calibrate_v2.py` (v0.2, incl. the ground-contact
  termination fix and the `boundary`→`near_boundary` regime rename) → `data/*_v2.*`,
  `outputs/dataset_audit_v2/`, `outputs/dataset_audit_v2_calibration/`
- `scripts/prepare_ml_dataset.py` → `data/ml/*_v2.parquet` (feature-enriched v0.2 data, input to `ml/train_baseline.py`)

## 3. The v0.3 control-profile decision trail (rejected candidates, kept as evidence)

This is the most tangled part of the history: **two concurrent Claude Code
sessions** worked the same calibration task at the same time and produced
conflicting verdicts, which a later reconciliation pass resolved. Full narrative:
`outputs/v03_calibration/reconciliation_report.md`.

| File | Role | Verdict |
|---|---|---|
| `aeroguard_dataset/control_profiles_v03_candidates.py`, `scripts/calibrate_v03.py`, `scripts/precursor_diagnosis.py` | "RUN B" — 5 single-pulse candidates | **NO-GO** (`outputs/precursor_diagnosis/FINAL_REPORT.md`) |
| `aeroguard_dataset/config.py: GRADUAL_APPROACH_CANDIDATES` (dead code, left in place — see §5), `scripts/calibrate_v3.py`, `diagnose_precursor.py` | "RUN A" — 5 candidates incl. original two-stage "Candidate D v1" | Initial GO on D, later found metric-inflated (`decision_gate_report.md`, corrected by `reconciliation_report.md`) |
| `scripts/verify_candidate_d.py` | Independent reproduction of RUN A's D v1 numbers | Confirmed the raw numbers were real but the precursor *metric* over-counted (`reconciliation_report.md` §4-5) |
| `aeroguard_dataset/control_profiles_candidate_d_v2.py`, `scripts/calibrate_candidate_d_v2.py` | Same-sign / zero-gap sequencing fix | Fixed dive/zoom artifact, but gamma-termination among non-crossers regressed (`candidate_d_followup_report.md`) — CASE B, not final |
| `aeroguard_dataset/control_profiles_candidate_d_v3.py`, `scripts/calibrate_candidate_d_v3.py` | + 7.0s combined-duration cap | **CASE A — READY** (`candidate_d_final_gate_report.md`) — this is the version used for the full v0.3 dataset |

None of these files were deleted after being superseded — each is still imported
(directly, or via a shared constant like `CANDIDATE_D_V2_ELEVATOR_SPEC`) or still
covered by its own test (`test_v03_candidates.py`, `test_candidate_d_v2_sequencing.py`,
`test_candidate_d_v3_duration_cap.py`).

## 4. Duplicate Stage-3 ML implementation

`outputs/ml/` (report: `outputs/ml/reports/experiment_report.md`) and
`outputs/ml_baseline/` are two separate, complete runs of the same "Stage 3"
baseline ML experiment against v0.2 data, produced by `scripts/run_ml_experiment.py`
(+ `ml/data.py`, `features.py`, `ablation.py`, `training.py`) and
`ml/train_baseline.py` + `evaluate_baseline.py` respectively.

**Only `outputs/ml_baseline/` is wired into the rest of the pipeline** —
`ml/temporal_config.py:BASELINE_OUTPUTS_DIR` points at it, and the Stage-4/v0.2
temporal experiment explicitly re-scores its frozen `random_forest.joblib`.
`outputs/ml/` is not read by anything downstream. Both are kept: both are
complete, valid, currently-tested experiments (`tests/test_ml_baseline.py`,
`tests/test_ml_pipeline.py`, `tests/test_ml_dataset_prep.py`), and no report
instructs deleting either.

## 5. Known dead code left in place intentionally

`aeroguard_dataset/config.py` contains `GRADUAL_APPROACH_CANDIDATES` and
`make_v03_calibration_config()`, added by the concurrent "RUN A" session during
the v0.3 calibration collision (§3) and never removed. Nothing in the canonical
v0.3 pipeline imports them (the winning candidate lives in
`control_profiles_candidate_d_v3.py`, not in `config.py`). `config.py` is a
shared, heavily-imported module across `aeroguard_dataset/`, `ml/`, and most of
`scripts/`, so it was **not** edited during this packaging pass — trimming dead
code from a file this central is exactly the kind of change the packaging
instructions ask to avoid ("never modify... unless required for an obvious
correctness issue"; this is inert, not incorrect).

## 6. What's excluded from git, and why

See `.gitignore`. In short: `data/raw/`, `data/processed/`, and the large
`*.parquet` feature panels under `data/ml*/` (~3.6GB total) are regenerable from
the versioned scripts + documented seeds (`REPRODUCIBILITY.md`) and are excluded
so the repository stays a source-and-report artifact rather than a multi-GB data
dump. Small metadata (`data/metadata/`, `data/splits/`, all CSV/JSON) is tracked.
Bulky intermediate calibration parquet dumps under `outputs/v03_calibration/` and
`outputs/ml_v03_generalization/{data,calibration}/` are likewise excluded; the
reports, metrics (CSV/JSON/MD), plots (PNG), and trained models (`.joblib`) that
summarize them are all tracked.
