# AeroGuard — Code & Artifact Provenance

This document maps the canonical pipeline, historical milestones, and retained experimental candidates that produced the current results.

## 1. The canonical v0.3 pipeline (what actually produced the final results)

| Stage | Canonical module(s) |
|---|---|
| Physics engine | `aeroguard/aerodynamics.py`, `dynamics.py`, `aircraft.py`, `integrator.py` — unmodified since Stage 1 |
| Shared generation primitives | `aeroguard_dataset/config.py`, `control_profiles.py`, `dataset_builder.py`, `events.py`, `features.py`, `labeling.py`, `paths.py`, `splitting.py`, `trajectory_sim.py`, `audit.py`, `visualize.py` |
| v0.3 `gradual_approach_v3` regime | `aeroguard_dataset/control_profiles_candidate_d_v3.py` — winning Candidate D v3 |
| v0.3 dataset generation | `aeroguard_dataset/dataset_builder_v3.py`, `scripts/generate_dataset_v3.py` |
| v0.3 dataset audit | `scripts/audit_v3_precursor.py` |
| Baseline ML | `ml/train_baseline.py` + `ml/evaluate_baseline.py` |
| Temporal ML | `ml/temporal_config*.py`, `temporal_data*.py`, `temporal_features.py`, `temporal_experiment*.py`, `scripts/run_temporal_experiment*.py` |
| Cross-mechanism generalization | `aeroguard_dataset/control_profiles_alt_single.py`, `scripts/calibrate_alt_single.py`, `generate_alt_single_dataset.py`, `run_alt_generalization_experiment.py` |

## 2. Historical milestones — retained because later analyses compare against them

v0.1 and v0.2 remain in the repository because the final analysis compares their datasets and metrics directly against v0.3.

## 3. v0.3 control-profile decision trail

The repository retains the competing calibration candidates and their validation reports so the final choice is auditable rather than reconstructed after the fact.

| File | Role | Verdict |
|---|---|---|
| `aeroguard_dataset/control_profiles_v03_candidates.py`, `scripts/calibrate_v03.py`, `scripts/precursor_diagnosis.py` | Five single-pulse candidates | **NO-GO** |
| `scripts/calibrate_v3.py`, `diagnose_precursor.py` | Initial candidate sweep | Initial GO later shown to have an inflated precursor metric |
| `scripts/verify_candidate_d.py` | Independent reproduction check | Confirmed raw numbers; corrected metric interpretation |
| `aeroguard_dataset/control_profiles_candidate_d_v2.py`, `scripts/calibrate_candidate_d_v2.py` | Sequencing fix | CASE B |
| `aeroguard_dataset/control_profiles_candidate_d_v3.py`, `scripts/calibrate_candidate_d_v3.py` | Final duration-capped profile | **CASE A — READY** |

## 4. Duplicate Stage-3 ML implementation

`outputs/ml/` and `outputs/ml_baseline/` contain separate Stage-3 baseline implementations. Only `outputs/ml_baseline/` is wired into later stages; both remain documented because they are valid historical experiments.

## 5. Known dead code

`aeroguard_dataset/config.py` contains an inert calibration constant and helper retained for historical compatibility. It is not part of the canonical v0.3 path.

## 6. What's excluded from git, and why

Large regenerable trajectory and feature parquet files are excluded so the repository stays a source-and-report artifact rather than a multi-gigabyte data dump. Seeds, scripts, metadata, reports, metrics, figures, and final models needed for reproduction remain tracked.
