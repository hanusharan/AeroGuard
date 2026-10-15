# AeroGuard Items 37–39 — false alarms, warning coverage, counts

- `PROTOCOL.md`: definitions, fixed before any number was computed (commit `a1173e5`).
- `src/items37_39.py`: pure functions (episodes, false-alarm classes, event table, coverage, ratio bootstrap).
- `src/run_items37_39.py`: runner. Hash-checks every input against its audit record and stops if stored Phase 3 / Item 33 values are not reproduced.
- `tests/`: synthetic known-answer tests (no research data).
- Results: `outputs/items33_42/items37_39/run_20261015T143215846532Z/REPORT.md`.

Run (scores and panels live in scratch storage, not in Git):

```
python -B experiments/items33_42/items37_39/src/run_items37_39.py <repo_root> <data_dir> <phase3_scratch_run_dir> <item33_scratch_run_dir>
python -B -m pytest -p no:cacheprovider experiments/items33_42/items37_39/tests
```

## Note added after the run (does not change any number)

In the usable test rows, `is_unsafe` rows almost always have `future_stall_5s == 1` (16,769 of 16,818; 49 exceptions). So the ONGOING class is almost never reachable and was 0 for every method, which is why the primary and existing-definition false-alarm rates are identical. A warning episode that *starts* during a stall is classified TRUE by the label, as in the existing definition, even though it gives no advance notice; episode precision should be read with that in mind. Lead-time coverage (Item 38) is not affected, because it only credits warnings that start before the crossing.
