# Reproducibility

Exact commands to regenerate every stage of the AeroGuard research program.
None of these were rerun during the final packaging pass (per the explicit
"do not rerun expensive stages" instruction) — commands and seeds below are
read directly from each script's source, and expected outputs are the actual
files already committed under `outputs/`/`data/` in this repository.

## Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` pins: `numpy`, `matplotlib`, `pytest` (Stage 1); `pandas`,
`pyarrow` (Stage 2, dataset tooling); `scikit-learn` (Stage 3+, ML — sklearn's
own `HistGradientBoosting` is used instead of an external boosting library, see
`requirements.txt` comments for why). No GPU, no external services, no network
access required for any stage.

All commands below are run from the repository root, with `.venv` activated.

## Seeds

Every stage uses a fixed, documented seed — no stage was ever rerun to cherry-pick
a result. `20260817` is the base seed used throughout v0.1/v0.2 and most v0.3
calibration rounds; later stages that needed disjoint data derive new seeds from
it explicitly (documented per-stage below) rather than reusing it silently.

## Stage 1 — physics engine demo

```bash
python scripts/simulate.py
```
No seed (deterministic trim + fixed elevator step). Output: `outputs/trajectory.png`.
Runtime: seconds.

```bash
python scripts/validate_physics.py
```
Output: `outputs/validation/*.png` (9 sensitivity/validation plots).

## Stage 2 — dataset generation (v0.1 / v0.2 / v0.3)

```bash
python scripts/generate_dataset.py       # v0.1, seed baked into make_generation_config
python scripts/generate_dataset_v2.py    # v0.2, SEED = 20260817
python scripts/generate_dataset_v3.py    # v0.3, SEED = 20260823 (fresh, distinct from v0.1/v0.2 and all calibration seeds)
```

Outputs (per version, `_v2`/`_v3` suffix or none for v0.1):
`data/raw/raw_telemetry*.parquet`, `data/processed/processed_dataset*.parquet`,
`data/metadata/trajectory_metadata*.csv` + `generation_config*.json` +
`feature_schema*.json`, `data/splits/split_manifest*.csv`.

v0.3: 3,150 trajectories (500 normal + 250 stall + 2,400 gradual_approach_v3),
5,340,865 rows. Runtime: several minutes (not separately timed in the source
report; dominated by the 2,400-trajectory gradual_approach_v3 batch).

Dataset audits (`outputs/dataset_audit/`, `_v2/`, `_v3/`) run automatically as
the final step of each `generate_dataset*.py` script above (via
`aeroguard_dataset/audit.py`, a library module with no standalone CLI). One
additional v0.3-specific audit is a separate script:
```bash
python scripts/audit_v3_precursor.py   # v0.3-specific precursor/physical-quality audit
```

## Stage 2b — v0.3 control-profile calibration trail

Historical/decision-trail scripts (see `PROVENANCE.md` §3 for which candidate
won). Re-running these reproduces the calibration-scale (150–175 trajectory)
decision points, not the full dataset:

```bash
python scripts/calibrate_v2.py                # v0.2 near_boundary calibration
python scripts/calibrate_v3.py                # RUN A: 5-candidate sweep, seed 20260817
python scripts/calibrate_v03.py                # RUN B: 5-candidate sweep, seeds 20260818-20260822
python scripts/calibrate_candidate_d_v2.py     # sequencing fix, seed 20260817
python scripts/calibrate_candidate_d_v3.py     # FINAL: duration cap, seed 20260817 (the winning profile)
python scripts/verify_candidate_d.py           # independent reproduction check
python scripts/precursor_diagnosis.py          # RUN B diagnosis
python scripts/diagnose_precursor.py           # RUN A diagnosis
```

## Stage 3 — baseline ML (instantaneous)

```bash
python scripts/prepare_ml_dataset.py    # builds data/ml/ml_{train,val,test}_v2.parquet from processed_dataset_v2
python -m ml.train_baseline             # ML_SEED = 20260817 (from ml/config.py), ~132s runtime
python -m ml.evaluate_baseline
```
Output: `outputs/ml_baseline/` (canonical — this is what Stage 4 reads).
Runtime: 132.5s (`outputs/ml_baseline/experiment_config.json`).

A separate, parallel Stage-3 implementation also exists and is **not** required
for any later stage (`PROVENANCE.md` §4):
```bash
python scripts/run_ml_experiment.py     # seed 20260817, output: outputs/ml/
```

## Stage 4 — temporal ML (early-warning, v0.2 and v0.3)

```bash
python scripts/run_temporal_experiment.py       # v0.2, seed 20260817, ~544.5s runtime
python scripts/run_temporal_experiment_v03.py   # v0.3 FINAL, seed 20260817, ~1324.8s (~22.1 min) runtime
```
Outputs: `outputs/ml_temporal/` (v0.2), `outputs/ml_v03/` (v0.3, incl. the
frozen `models/primary_model_D_1s.joblib`). Cached feature panels:
`data/ml_temporal/*.parquet`, `data/ml_temporal_v03/*.parquet` (reused, not
rebuilt, on subsequent runs unless deleted).

Supplementary (read-only, no new model fits, feeds `v03_temporal_ml_report.md`):
```bash
python scripts/analyze_v03_physics_vs_ml.py
python scripts/build_v03_final_comparison.py
```

## Stage 5 — cross-mechanism generalization (final experiment)

```bash
python scripts/calibrate_alt_single.py             # calibration, n=150, seed 20260817
python scripts/generate_alt_single_dataset.py       # holdout seed 20261817 (n=300), train_val seed 20262817 (n=350)
python scripts/run_alt_generalization_experiment.py # forward + reverse checks, reuses frozen primary_model_D_1s.joblib
```
Output: `outputs/ml_v03_generalization/`. This stage never refits or modifies
`outputs/ml_v03/models/primary_model_D_1s.joblib` — the forward check evaluates
it exactly as-is.

## Testing

```bash
pytest tests/ -v
```
Expected: **190/190 passing** (verified during final packaging, 32.4s runtime).

## Output locations reference

| Stage | Script(s) | Output dir |
|---|---|---|
| Physics demo | `simulate.py` | `outputs/trajectory.png` |
| Physics validation | `validate_physics.py` | `outputs/validation/` |
| v0.1 dataset | `generate_dataset.py` | `data/{raw,processed}/*.parquet` (no suffix), `outputs/dataset_audit/` |
| v0.2 dataset | `generate_dataset_v2.py` | `data/*_v2.*`, `outputs/dataset_audit_v2/` |
| v0.3 dataset | `generate_dataset_v3.py` | `data/*_v3.*`, `outputs/dataset_audit_v3/` |
| v0.3 calibration trail | `calibrate_*.py` | `outputs/v03_calibration/`, `outputs/precursor_diagnosis/` |
| Baseline ML | `ml.train_baseline`/`evaluate_baseline` | `outputs/ml_baseline/` |
| Temporal ML v0.2 | `run_temporal_experiment.py` | `outputs/ml_temporal/` |
| Temporal ML v0.3 | `run_temporal_experiment_v03.py` | `outputs/ml_v03/` |
| Generalization | `run_alt_generalization_experiment.py` | `outputs/ml_v03_generalization/` |
| Final synthesis | (this packaging pass) | `outputs/final/` |

## Notes on re-running expensive stages

Full v0.3 dataset generation (3,150 trajectories) and the v0.3 temporal ML
experiment (~22 min) were **not** rerun during the final packaging pass — all
numbers in `outputs/final/AEROGUARD_FINAL_RESEARCH_REPORT.md` are read from the
existing, already-frozen output files. If you do rerun any generation or
training script, it will overwrite its own output directory in place; the
frozen v0.1/v0.2/v0.3 datasets and the frozen `primary_model_D_1s.joblib` should
not be regenerated casually, since every downstream report's numbers are tied
to those specific frozen artifacts.
