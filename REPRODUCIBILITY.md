# Reproducibility

Exact commands to regenerate every stage of the AeroGuard research program.
The commands and seeds below are read directly from each script's source, and
the expected outputs are the files already committed under `outputs/` and
`data/` in this repository. The v1.0 packaging did not re-run them. A partial
re-run on 2026-10-12, in a scratch copy of the repository, is recorded under
[Reproduction evidence](#reproduction-evidence-2026-10-12); read that section
before relying on any statement here that a stage "reproduces". The consolidated
evidence on what has and has not been reproduced is in
[`REPRODUCIBILITY_REPORT.md`](REPRODUCIBILITY_REPORT.md).

## Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-pinned.txt   # tested set, needs Python >= 3.12
# or: pip install -r requirements.txt    # loose lower bounds, not re-tested
```

`requirements.txt` pins: `numpy`, `matplotlib`, `pytest` (Stage 1); `pandas`,
`pyarrow` (Stage 2, dataset tooling); `scikit-learn` (Stage 3+, ML — sklearn's
own `HistGradientBoosting` is used instead of an external boosting library, see
`requirements.txt` comments for why). No GPU, no external services, no network
access required for any stage.

### Pinned environment

`requirements-pinned.txt` is a full `pip freeze` of an environment that was
installed and tested on 2026-10-12 with CPython 3.12 on Linux x86_64. It is a
**newly tested** environment, not the original research environment. The only
version with evidence behind it is scikit-learn **1.9.0**, recorded inside
`outputs/ml_v03/models/primary_model_D_1s.joblib` and in
`outputs/ml/metrics/test_lock.json`; the versions of Python, numpy, pandas,
pyarrow, matplotlib and pytest used for the original runs are not recorded in
the repository. `requirements.txt` is unchanged.

### Test policy for CI (`.github/workflows/tests.yml`)

`data/processed/` and the cached ML parquet files are gitignored and are not
regenerated in CI. On a clean checkout the original 190 tests give 155 passed,
24 skipped, 2 failed, 9 errors. (The 36 audit tests added later bring the
collected total to 226 and the CI result to 191 passed, 24 skipped, 11
deselected; the 190 and 155 below refer to the original suite. After commit
`30e7732` rebuilt the paper PDF, the baseline-hash test failed (326 passed,
1 failed). With the test now checking the recovered historical PDF and the
current PDF's own manifest (see [`baselines/README.md`](baselines/README.md)),
the CI selection gives 327 passed, 24 skipped, 11 deselected (local run, 2026-10-24).) The 11 failures/errors all come from
`FileNotFoundError` on gitignored data files and have no skip guard: 10 need
`data/processed/processed_dataset_v2.parquet` (all nine in
`tests/test_ml_pipeline.py` plus `test_build_ml_table_is_deterministic`), and 1,
`tests/test_ml_dataset_prep.py::test_feature_schema_matches_actual_columns`,
needs `data/ml/ml_dataset_v2.parquet`. CI deselects exactly those 11 node IDs (listed in the workflow) and
leaves the tests unedited; the 24 guarded tests report as skipped. A green CI
run therefore means the remaining 155 tests pass, not that the historical 190
passed or that any result was reproduced.

### Test-suite scope and known gaps

A review of the suite (175 test functions in 15 files; all but two contain an
explicit assertion or expected-exception check, and those two verify that a
call does not raise) found strong coverage of the
leakage and integrity risks that matter most for this research: causal
rolling/derivative features (`test_temporal_features.py`, including a test that
perturbs a future sample and a deliberate naive-versus-grouped leakage check),
trajectory-level split separation and forbidden-feature rejection
(`test_ml_pipeline.py`, `test_temporal_v03_integrity.py`), and physics and
integrator checks against closed-form results (`test_aerodynamics.py`,
`test_dynamics.py`, `test_integrator.py`). Known gaps, documented rather than
fixed: no test references `ml/evaluation.py` (which computes the headline
classification metrics), `ml/training.py`, `ml/ablation.py` or
`aeroguard_dataset/features.py`; the real-data integrity checks skip when the
cached parquet files are absent, so they do not run in CI; nothing asserts that
the frozen metrics files match the headline numbers in the reports; and the
dashboard's TypeScript physics port is checked only by the separate
`dashboard/parity/check.mjs` harness (`node dashboard/parity/check.mjs`), which
CI does not run. A passing suite supports software correctness; it does not
validate the science.

### What a clean checkout contains

- **Tracked in Git:** all code and tests; the metadata, configuration and
  split manifests for v0.1–v0.3 (`data/metadata/`, `data/splits/`); and every
  report, metric, plot and trained model under `outputs/`, including the frozen
  v0.3 model.
- **Not tracked (gitignored, regenerable):** the trajectory and ML tables
  `data/raw/`, `data/processed/`, `data/ml/*.parquet`,
  `data/ml_temporal*/*.parquet`, and the calibration/generalization parquet dumps
  under `outputs/`. The original files (about 3.6 GB in total, per `.gitignore`)
  are **not** in the repository and no hash of them was recorded, so a
  regenerated copy cannot be byte-compared to the original.

### Reproduction levels

| Level | What you do | Needs data? | Outcome (see evidence below) |
|---|---|---|---|
| 0. Verify frozen files | `sha256sum -c baselines/v0.3.sha256` | no | Confirms the tracked v0.3 model, config, reports and code are unchanged. Expected result since `30e7732`: 78 OK, 1 FAILED (the paper PDF was rebuilt). Then run `sha256sum -c baselines/paper_pdf_v1.1.0.sha256`, which verifies the recovered historical PDF and the current PDF; see [`baselines/README.md`](baselines/README.md). |
| 1. Test a clean checkout | CI command in `.github/workflows/tests.yml` | no | 191 passed, 24 skipped, 11 deselected when the audit tests were added (226 collected; 155 passed of the original 190). Now (local run, 2026-10-24): 327 passed, 24 skipped, 11 deselected; see the test policy above. |
| 2. Regenerate datasets | `scripts/generate_dataset_v2.py`, `scripts/generate_dataset_v3.py` | no | Regenerates the data; split manifests identical, floats within about 1e-12. |
| 3. Rebuild ML inputs and run the full suite | `scripts/prepare_ml_dataset.py`, temporal cache builders, `pytest tests/` | after level 2 | 190 passed. |
| 4. Re-score the frozen model | Snippet below | after level 2 | Matches the published v0.3 TEST metrics to about 1e-10. |
| 5. Retrain / rerun experiments | Stage 3–5 commands below | after level 2 | **Not tested** in this verification. |

Levels 2–4 are checks of the same code by the same author on a different
machine. They show the pipeline regenerates consistently; they are not an
independent replication and not a validation of the science.

### Run reproduction in a scratch copy

Every script writes to `data/` and `outputs/` under the repository root, and
many of those paths are tracked, frozen files. Running a stage inside your normal
checkout can overwrite them. Do the work in a copy instead (all paths are
resolved relative to the copy):

```bash
mkdir ../aeroguard-scratch
tar --exclude=.git --exclude=dashboard/node_modules --exclude=dashboard/dist -cf - . \
  | tar -xf - -C ../aeroguard-scratch
cd ../aeroguard-scratch
```

### Re-scoring the frozen model on regenerated v0.3 data (level 4)

After `python scripts/generate_dataset_v3.py` (about 9 minutes), this reads the
regenerated data, builds the TEST feature panel (cached under
`data/ml_temporal_v03/`) and scores it with the frozen model at the frozen
threshold. Run it from the scratch copy's root:

```python
import json, os, joblib
from sklearn.metrics import average_precision_score
from ml import temporal_config_v03 as v3cfg
from ml.events import aggregate_event_results, compute_event_level_results
from ml.temporal_data_v03 import load_temporal_splits
from ml.temporal_experiment import get_xy
from ml.temporal_features import usable_mask_for_window

pub = json.load(open(os.path.join(v3cfg.METRICS_DIR, "primary_model_metrics.json")))
w = v3cfg.PRIMARY_WINDOW_S
test = load_temporal_splits(force=False, verbose=False)["test"]
X, y, sub = get_xy(test, v3cfg.model_d_features(w), usable_mask_for_window(test, w))
sub = sub.reset_index(drop=True)
model = joblib.load(os.path.join(v3cfg.MODELS_DIR, "primary_model_D_1s.joblib"))
p = model.predict_proba(X)[:, 1]
agg = aggregate_event_results(compute_event_level_results(
    sub, (p > float(pub["threshold"])).astype(int), v3cfg.LABELING_HORIZON_S))
print("PR-AUC", average_precision_score(y, p), "published", pub["test_metrics"]["pr_auc"])
print("event recall", agg["event_recall"], "events", agg["n_events"],
      "median lead", agg["median_lead_time_s"], "test rows", len(sub))
```

(Run with `PYTHONPATH=.` from the scratch copy's root.)

The snippet applies the threshold with a strict `>`, exactly as the primary
evaluation does (`evaluate_on_test`, `ml/temporal_experiment.py:109`). An earlier
draft of this guide showed `>=`, which was a documentation error. The two
operators differ only for a score exactly equal to the threshold, and the effect
of that on row-level counts has not been measured. The other places that apply
a threshold, and which operator each uses, are listed in `RESEARCH_LOG.md`
(RL-004).

### Reproduction evidence (2026-10-12)

One run on CPython 3.12.3, Linux x86_64, with the exact packages in
`requirements-pinned.txt`, in a scratch copy of the repository. The model was
not retrained and no tracked file in the real checkout was modified.

- **Level 2, v0.2** (`generate_dataset_v2.py`, 173 s): 1,000 trajectories,
  1,753,615 rows (matches the documented count). `split_manifest_v2.csv`,
  `generation_config_v2.json` and `feature_schema_v2.json` are byte-identical to
  the tracked files. `trajectory_metadata_v2.csv` and `audit_report_v2.json`
  differ in the last digits of eight floating-point columns (max relative
  difference 1.5e-13); trajectory IDs, regimes, stall outcomes and termination
  reasons are identical.
- **Level 2, v0.3** (`generate_dataset_v3.py`, 520 s): 3,150 trajectories,
  5,340,865 rows (matches the documented counts). The split manifest,
  generation config and feature schema are byte-identical; the metadata CSV and
  audit JSON differ only in float last digits (max relative difference 8.9e-13).
- **Level 3:** `prepare_ml_dataset.py` (8.6 s) plus the v0.2 and v0.3 temporal
  cache builders, then `pytest tests/`: **190 passed, 0 skipped, 0 failed**
  (62.6 s). This includes the 11 tests that CI deselects and the 24 data-guarded
  tests, which is why the historical "190 passing" figure is reproducible
  *when the data is regenerated*.
- **Level 4:** the frozen model on the regenerated v0.3 TEST panel gave
  event recall 0.9605263157894737 (73/76), median credited lead 4.72 s and
  538,034 test rows, all equal to the published values. That run applied the
  threshold with `>=`, not the primary evaluation's `>` (see above); row-level
  confusion counts were not compared, and PR-AUC does not depend on the
  threshold. PR-AUC was not stable
  in its last digits between repeated runs on the same data: across five runs it
  took two values, 0.8902774777010881 (equal to the published value) and
  0.8902774777849808 (difference 8e-11). The cause was not investigated; it is
  consistent with floating-point effects in the forest's probability averaging.
  Compare PR-AUC with a tolerance, not for exact equality.

Not tested: the calibration scripts, the v0.1 dataset, retraining the baseline
or temporal models (about 22 minutes for v0.3), and the cross-mechanism
generalization stage. A retrained model is not expected to be byte-identical to
the frozen one; compare its metrics, not its hash.

### Troubleshooting

These errors were observed on a clean checkout:

- `FileNotFoundError: .../data/processed/processed_dataset_v2.parquet`: the
  gitignored data is missing; run `scripts/generate_dataset_v2.py` (Stage 2).
- `FileNotFoundError: .../data/ml/ml_dataset_v2.parquet`: run
  `scripts/prepare_ml_dataset.py` (needs the v0.2 data first).
- Tests reported as skipped with "run ... first": build the temporal caches with
  `ml.temporal_data.load_temporal_splits()` (v0.2) and
  `ml.temporal_data_v03.load_temporal_splits()` (v0.3) after generating the data.
- `requirements-pinned.txt` does not install on Python 3.11 or older (numpy
  2.5.4 requires 3.12).
- Regenerated `trajectory_metadata_v*.csv` and `audit_report_v*.json` will not
  match the tracked files byte for byte (float last digits); compare values with
  a tolerance.

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

## Phase 4 — aircraft family and JSBSim (Items 43–53)

The commands are those in §13 of
[`outputs/phase4/run_20261015T152932Z/REPORT.md`](outputs/phase4/run_20261015T152932Z/REPORT.md)
(`scripts/phase4_generate.py`, `scripts/phase4_generate_jsbsim.py`,
`scripts/run_phase4.py` with stages `primary`, `jsbsim` and `robust`, then
`scripts/phase4_item50.py`). What is and is not known about reproducing them
(checked in the Phase A audit, [`reports/PHASE_A_FINAL_AUDIT.md`](reports/PHASE_A_FINAL_AUDIT.md)):

- **Not archived:** the generated datasets, per-trajectory metadata
  (`*_meta.csv`), `envelopes.json`, fitted models and score arrays (about 3 GB,
  written to a scratch `<data_dir>`). Only aggregate results are in the
  repository, so no Phase 4 metric can be recomputed from data without
  regenerating everything.
- **Extra dependency:** `jsbsim==1.3.2`, needed only for the JSBSim stages; it
  is not in `requirements-pinned.txt`.
- **Environment:** the report states CPython 3.13; the package versions used for
  the run, the bootstrap replicate count (`P4_SMOKE_B` can override the default
  1000) and dataset checksums were not recorded. The experiment code (`phase4/`,
  the Phase 4 scripts, and the `ml/`, `aeroguard/`, `aeroguard_dataset/` and
  Items 37–39 modules it imports) is unchanged since the results commit
  (`edf768c`).
- **Not verified:** that a regeneration reproduces the stored results, or that
  the JSBSim stage is deterministic. No Phase 4 result has been reproduced or
  independently replicated.

## Testing

```bash
pytest tests/ -v
```
Expected result depends on the data available:

- **Clean checkout (no regenerated data):** 190 collected; run unfiltered this
  gives 155 passed, 24 skipped, 2 failed, 9 errors. CI deselects the 11
  data-dependent tests and gives 155 passed, 24 skipped, 11 deselected; with
  the 36 audit tests added, 191 passed, 24 skipped, 11 deselected. With the
  tests added since: 327 passed, 24 skipped, 11 deselected (local run,
  2026-10-24; between `30e7732` and the PDF-manifest fix, 326 passed, 1 failed).
- **After regenerating the data and caches (levels 2–3):** 190 passed, as
  measured in the scratch copy above.

The "190/190 passing" recorded at v1.0 packaging was taken in a working copy that
held the generated data. Passing tests are software checks, not independent
validation of the scientific results.

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
| Final synthesis | v1.0 packaging (documentation only) | `outputs/final/` |

## Notes on re-running expensive stages

Full v0.3 dataset generation (3,150 trajectories) and the v0.3 temporal ML
experiment (~22 min) were **not** rerun when the v1.0 documentation was assembled — all
numbers in `outputs/final/AEROGUARD_FINAL_RESEARCH_REPORT.md` are read from the
existing, already-frozen output files. If you do rerun any generation or
training script, it will overwrite its own output directory in place; the
frozen v0.1/v0.2/v0.3 datasets and the frozen `primary_model_D_1s.joblib` should
not be regenerated casually, since every downstream report's numbers are tied
to those specific frozen artifacts.
