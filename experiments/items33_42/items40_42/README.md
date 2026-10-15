# AeroGuard Items 40–42 — fair comparison, comparison report, conclusion checks

- `PROTOCOL.md`: the rules, written before any number was computed (commit `6507d91`).
- `src/items40_42.py`: pure functions (fast false-episode count, the validation-only matched-threshold rule, paired ratio bootstrap, wording scan).
- `src/run_items40_42.py`: the runner. It scores the validation split with the frozen model and the Phase 3 instantaneous model (read-only, hash-checked), picks thresholds before reading the test split, and writes the Item 41 report and figures and the Item 42 checks.
- `tests/`: synthetic known-answer tests (no research data).
- Results: `outputs/items33_42/items40_42/run_20261015T144358282823Z/REPORT.md`, the combined comparison report. Item 42 results are in `item42_checks.json` and `C2_REVIEW.md`.

How to run (the panels and score arrays live in scratch storage, not in Git):

```
python -B experiments/items33_42/items40_42/src/run_items40_42.py <repo_root> <data_dir> <phase3_scratch_run_dir> <item33_scratch_run_dir> <items37_39_run_dir>
python -B -m pytest -p no:cacheprovider experiments/items33_42/items40_42/tests
```

## Reading notes (none of these changes a number)

- **Validation-matched rates do not carry over to test.** At R = 20 and R = 40, the two models' test false-episode rates are roughly half their validation rates. The AoA rule's test rates fall less, by about a quarter to a third. The coverage contrasts are therefore at matched *validation* rates, and the test rates are shown next to every contrast.
- **The contrasts are descriptive.** There are 18 of them and none is adjusted for multiplicity. Frozen − AoA coverage at 2 s and 4 s excludes 0 at every R. Frozen − instantaneous coverage excludes 0 at R = 10 (4 s) and R = 20 (2 s and 4 s), and not at R = 40.
- **Results of the checks.**
  - L1–L5 and M1–M5: all PASS.
  - Leakage screen (L3): the best single feature reaches PR-AUC 0.709 (`stall_margin`, the same as alpha), against 0.890 for the full model. No leakage pattern was found.
  - C1: PASS, 26 headline statements re-derived independently.
  - C2: 4 lines flagged; all were reviewed and found acceptable (see `C2_REVIEW.md`).
