# AeroGuard — Final Project Status

**Research status: COMPLETE.** Per explicit instruction, the final scientific
experiment (cross-mechanism generalization) is complete and no further
experiments, ablations, hyperparameter tuning, new datasets, or new candidate
mechanisms were run or should be run automatically from this document. This
packaging pass added only documentation, a synthesis report, a figures
selection, and non-destructive repository hygiene (see §"Files changed this
pass" below) — no physics, dataset, or model file was modified.

## Dataset status

Three versioned, frozen, integrity-verified datasets:

| Version | Trajectories | Rows | Verified this pass |
|---|---|---|---|
| v0.1 | 1,000 | 1,565,280 | ✅ no NaN/Inf, 0 dup trajectory IDs, min altitude 51.06m |
| v0.2 | 1,000 | 1,753,615 | ✅ no NaN/Inf, 0 dup trajectory IDs, min altitude 0.135m |
| v0.3 | 3,150 | 5,340,865 | ✅ no NaN/Inf, 0 dup trajectory IDs, min altitude 0.0199m |

Zero train/val/test trajectory-ID overlap confirmed directly (not just cited)
for all three versions this pass. All three datasets' underlying files are
unmodified since before this packaging pass began (verified via mtime diff
against the pre-cleanup git snapshot).

## ML status

- Baseline (instantaneous) ML: canonical result `outputs/ml_baseline/`,
  RandomForest test PR-AUC 0.742 (v0.2 data). A parallel, unused-downstream
  duplicate implementation also exists (`outputs/ml/`) — both preserved,
  documented in `PROVENANCE.md` §4.
- Temporal (early-warning) ML: v0.2 baseline PR-AUC 0.813 / median lead 0.53s
  → v0.3 final PR-AUC 0.890 / median lead 4.72s / event recall 96.1% (73/76).
  Frozen model: `outputs/ml_v03/models/primary_model_D_1s.joblib`, confirmed
  unmodified this pass.

## Generalization status

Zero-exposure regime-exclusion: **collapses** (PR-AUC 0.890→0.552, median lead
4.72s→0.73s) — the model cannot invent multi-second precursor detection from
no training exposure to the phenomenon class. Cross-mechanism transfer (trained
on one slow-approach shape, tested on a structurally distinct one): **retains
the large majority of in-distribution performance** in both directions
(forward PR-AUC 0.835 / 100% event recall; reverse PR-AUC 0.708 / 87.0% event
recall) — CASE A, the final decision gate. See report §17–19 for full numbers.

## Test status

**190/190 tests passing**, re-run twice during this packaging pass (before and
after cleanup, identical result, 32–34s runtime each). Leakage/integrity-specific
suites (`test_temporal_v03_integrity.py`, `test_temporal_features.py`,
`test_dataset_generation.py`, `test_dataset_builder_v3.py` — 64 tests) verified
individually and pass explicitly.

## Reproducibility status

Every stage has a documented exact command, seed, and output location in
`REPRODUCIBILITY.md`. All seeds are fixed and were never varied to obtain a
better-looking result (no stage in this project's history was rerun after
seeing its own results, per every stage report's own "no reruns" statement).
Expensive stages (full v0.3 generation, the ~22-minute v0.3 temporal ML run)
were **not** rerun during this packaging pass, per instruction — all report
numbers are read from already-frozen output files, cross-checked against a
cheap smoke-test integrity pass on the actual dataset files (see Test status).

## Documentation status

- `README.md` — rewritten, ~5-minute technical overview, current through the
  final generalization result.
- `PROVENANCE.md` — new, full canonical/historical/candidate file classification.
- `REPRODUCIBILITY.md` — new, exact commands/seeds/outputs per stage.
- `outputs/final/AEROGUARD_FINAL_RESEARCH_REPORT.md` — new, full 24-section
  chronological synthesis, every number cited to its source report.
- `outputs/final/figures/` — new, 8 figures (7 reused unchanged + 1 new
  pipeline diagram), indexed in `outputs/final/figures/README.md`.
- No existing report anywhere in `outputs/` was edited or overwritten.

## Known limitations

Not a validated real-aircraft model (2D/longitudinal only, constant air
density, linear pitch-response surrogate). Demonstrated generalization is
family-level (transfer across control-input *shapes* within one broad
slow-approach phenomenon), not zero-shot across arbitrary unseen regimes. The
`stall` regime remains an imminent-only detector in both v0.2 and v0.3.
Per-event lead-time calibration is only moderately correlated with true
physical onset (r=0.337). Full list: final report §20–21.

## Exact final conclusion

**The evidence supports multi-second stall early-warning and transfer across
structurally distinct control-input mechanisms producing the same underlying
physical phenomenon, but does NOT establish universal zero-shot stall
prediction across arbitrary unseen flight regimes.**

## Exact list of remaining optional/nonessential work

None of the following is required — the research question this project set out
to answer (§2 of the final report) has a supported, precisely-scoped answer.
If pursued later, each would be a **new** research stage, not a continuation of
this one:

1. Testing transfer to a qualitatively different (non-elevator-timing-driven)
   stall-inducing mechanism.
2. Improving per-event lead-time calibration (currently only moderately
   correlated with true onset, r=0.337).
3. Extending the physics model beyond 2D/longitudinal dynamics or a
   constant-density atmosphere.
4. Investigating whether the `stall` regime's short (~0.3s) physical precursor
   can itself be extended via control-profile timing, analogous to what this
   project did for `near_boundary`/`gradual_approach_v3`.
5. Reconciling or merging the duplicate Stage-3 ML implementation
   (`outputs/ml/` vs. canonical `outputs/ml_baseline/`) into one — currently
   both are preserved and clearly documented, not blocking anything.
6. Stripping the inert dead code (`GRADUAL_APPROACH_CANDIDATES`,
   `make_v03_calibration_config`) left in `aeroguard_dataset/config.py` from
   the resolved concurrent-session collision — inert, not incorrect, and
   `config.py` is a shared/central module intentionally left unedited this pass.

---

## Files changed this packaging pass

**Added:** `PROVENANCE.md`, `REPRODUCIBILITY.md`,
`outputs/final/AEROGUARD_FINAL_RESEARCH_REPORT.md`, `outputs/final/FINAL_STATUS.md`,
`outputs/final/figures/` (8 PNGs + README.md), git repository itself
(`git init` + initial safety-net commit, at the user's request, since none
existed before this pass).

**Moved/archived:** none. Every file audited as "historical" or "rejected
candidate" is still imported by canonical code or covered by a currently-passing
test (see `PROVENANCE.md`) — relocating any of them would have broken
`pytest` without improving clarity, so they were documented in place instead,
per the packaging instructions' explicit "archive or clearly document"
alternative.

**Modified:** `README.md` (full rewrite), `.gitignore` (added `.DS_Store` and
large regenerable data/intermediate-parquet exclusions with inline rationale).

**Deleted:** OS/build cruft only — `.DS_Store` files (3) and `__pycache__`
directories (5) outside `.venv`, both regenerable and already covered by
`.gitignore`. No source file, report, dataset, or model was deleted.

**Intentionally left untouched:** `aeroguard/` (physics engine), all
`aeroguard_dataset/*.py`, all `ml/*.py`, all `scripts/*.py`, all of `data/`,
all of `outputs/` outside the new `outputs/final/` directory, `tests/`,
`requirements.txt` — confirmed via mtime diff against the pre-cleanup git
snapshot (§Test status / Reproducibility status above).
