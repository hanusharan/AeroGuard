# AeroGuard v0.3 baseline

This directory records what the **v0.3 research baseline** is and lets anyone
check that its tracked files have not changed. It adds no new results and
changes none.

## What "v0.3" means here

v0.3 is the third **dataset and experiment version** of the research: the
`gradual_approach_v3` control-profile regime (Candidate D v3), a 3,150-trajectory
dataset (5,340,865 rows, seed 20260823, `dataset_version` `stage2-v0.3-full`), the
temporal RandomForest trained on it, and the reports built on them. It is not a
software release, not the paper's version, and not the dashboard's "Frozen
Research · v1.0" label. Those are separate things; see
[`CONTRIBUTING.md`](../CONTRIBUTING.md#versions-and-releases).

The frozen model is `outputs/ml_v03/models/primary_model_D_1s.joblib`. It was
added in the repository's first commit (`297f6ac`, 2026-08-18) and has not
changed in Git history since. It records scikit-learn 1.9.0.

| Identifier | Value |
|---|---|
| SHA-256 | `707d4c61a791af940549f81520a0c8429edaa8ef8d67eb0f02c3174c5fe603f3` |
| Git blob ID | `d3772258289cf3eebe6a22087d3bee659b3c7d52` |

## Verify

From the repository root:

```bash
sha256sum -c baselines/v0.3.sha256        # expect: every line "OK"
```

`v0.3.sha256` lists 79 tracked files, all unchanged since the initial snapshot
commit apart from the documents added or edited later (`PROVENANCE.md`, the
final report and status, the experiment log and the paper PDF):

- the frozen model;
- the v0.3 generation config, feature schema, trajectory metadata and split
  manifest, and the ML experiment config;
- the v0.3 reports and metrics, the dataset audit, the cross-mechanism
  generalization report and metrics, and the v0.3 calibration decision reports;
- the final research report, final status, `PROVENANCE.md` and
  `experiments/EXPERIMENT_LOG.md`;
- the research paper PDF (`paper/AeroGuard_Research_Paper.pdf`);
- every Python module under `aeroguard/`, `aeroguard_dataset/` and `ml/`, and
  the v0.3 scripts, i.e. the code that produced the results.

A failing line means that a baseline file differs from the recorded version. Do
not "repair" it by editing the manifest; find out why it changed first.

On macOS use `shasum -a 256 -c baselines/v0.3.sha256`.

## What is not covered

- **The datasets.** The v0.3 data tables (`data/raw/`, `data/processed/`, the
  feature caches) are gitignored. The original files are not in this repository
  and no hash of them was ever recorded, so they cannot be verified. Only their
  tracked metadata is covered. A regenerated v0.3 dataset has the same row and
  trajectory counts and an identical split manifest, config and schema, with
  float values that agree to about 1e-12; details are in
  [`REPRODUCIBILITY.md`](../REPRODUCIBILITY.md#reproduction-evidence-2026-10-12).
- **The original software environment.** Only scikit-learn 1.9.0 is recorded
  (inside the model). The Python, numpy, pandas and other versions used for the
  original runs are unknown.
- **The paper source files.** `paper/AeroGuard_Research_Paper.md` and `.html`
  are not hashed here because their repository link was corrected after the
  baseline was frozen; the PDF, which still carries the older link, is hashed. This
  manifest does not show that the PDF is byte-identical to the file deposited on
  Zenodo (not checked).
- **Tests and the dashboard.** They are not part of the scientific baseline.

## Rules for future baselines

1. Never edit or regenerate `v0.3.sha256`'s files or this manifest to match a
   changed file. A deliberate change gets a new, dated entry in
   [`RESEARCH_LOG.md`](../RESEARCH_LOG.md) and a **new** manifest.
2. To freeze a later baseline (for example a future v0.4), generate a new
   `baselines/vX.Y.sha256` with `sha256sum` over the new artifacts and add a short
   section to this file. Keep the old manifests.
3. Hash only tracked, final files. Do not copy large models or datasets into this
   directory.
4. Git tags are a convenient pointer to a commit but do not replace the
   manifest; no tag has been created for v0.3.
