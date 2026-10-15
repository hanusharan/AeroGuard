# Items 37–39 report (run `run_20261015T143215846532Z`)

> Regenerated v0.3 copy; previously exposed test data; not blind or independent; rates are per simulated hour of eligible evaluation time, not operational rates; simulation only.

Protocol SHA-256 `07b170eda959870964fefeaedf73e1ed3ff8db1f696fe0fc4e8f408a12c09bfb` (committed before this run). Population: 538,034 usable test rows, 456 trajectories.

## Item 39 — trajectory and event counts

| Split | Trajectories (manifest / panel) | With usable rows | Excluded | Usable rows | Eligible time (span) |
|---|---|---|---|---|---|
| train | 2205 / 2205 | 2118 | 87 | 2,443,881 | 24417.63 s (6.783 h) |
| val | 472 / 472 | 459 | 13 | 491,322 | 4908.63 s (1.364 h) |
| test | 473 / 473 | 456 | 17 | 538,034 | 5375.78 s (1.493 h) |

Test events: 76 (57 first, 19 later) in 57 trajectories; 399 usable trajectories have no event. 10 further trajectories contain an unsafe run that lies outside the usable rows (excluded; reasons in `counts_item39.json`). Left-censored events (stall already under way at the first usable row): 0. Positive rows 46,169, negative rows 491,865. Split overlap {'train&val': 0, 'train&test': 0, 'val&test': 0}; duplicate keys [0, 0, 0]; duplicate initial conditions in the metadata: 0.

| Regime (test, usable) | Trajectories | Rows | Positive rows | Events | Event-bearing trajectories |
|---|---|---|---|---|---|
| gradual_approach_v3 | 346 | 396,207 | 30,001 | 54 | 40 |
| normal | 81 | 113,481 | 0 | 0 | 0 |
| stall | 29 | 28,346 | 16,168 | 22 | 17 |

Independent evidence: the frames are not independent. The 456 test trajectories are the resampling unit, and event-level results rest on the 57 event-bearing trajectories.

## Item 37 — false-warning episodes per simulated flight hour (primary: no merging, FALSE episodes only)

| Method | Threshold | Episodes | True | Ongoing | False | False / sim. hour [95% CI] | Existing definition (incl. ongoing) | Merge 1 s | Merge 2 s | Episode precision |
|---|---|---|---|---|---|---|---|---|---|---|
| aoa_signed | 0.217239 | 129 | 94 | 0 | 35 | 23.44 [14.87, 33.38] | 23.44 [14.87, 33.38] | 22.1 [13.69, 31.79] | 18.08 [10.93, 26.67] | 0.7287 |
| aoa_two_sided | 0.217239 | 129 | 94 | 0 | 35 | 23.44 [14.87, 33.38] | 23.44 [14.87, 33.38] | 22.1 [13.69, 31.79] | 18.08 [10.93, 26.67] | 0.7287 |
| instantaneous_model_a | 0.819487 | 139 | 95 | 0 | 44 | 29.47 [17.64, 43.78] | 29.47 [17.64, 43.78] | 21.43 [13.99, 30.01] | 20.76 [13.45, 28.92] | 0.6835 |
| frozen_temporal | 0.858553 | 121 | 93 | 0 | 28 | 18.75 [11.57, 26.84] | 18.75 [11.57, 26.84] | 14.73 [9.362, 20.95] | 14.73 [9.362, 20.95] | 0.7686 |

Retrained Item 33 models (own validation-selected thresholds), primary rate summarised across the five seeds (every seed and interval in `false_alarms_item37.json`):

| Condition | Median false / sim. hour | Min | Max | Median false episodes |
|---|---|---|---|---|
| C0 | 19.42 | 15.4 | 20.76 | 29 |
| C1 | 17.41 | 16.74 | 29.47 | 26 |
| C2 | 16.74 | 14.73 | 30.14 | 25 |
| C3 | 16.74 | 15.4 | 20.09 | 25 |
| X1 | 20.09 | 16.74 | 20.76 | 30 |

The denominator is 1.493 simulated hours, so each false episode adds about 0.67 per hour; intervals are wide.

## Item 38 — warning coverage at lead times (primary: existing lead-time definition, all events)

| Method | Events warned | Coverage at 2 s [95% CI] | Coverage at 4 s [95% CI] | Sustained warning, 2 s | Sustained warning, 4 s | Eligible events at 4 s |
|---|---|---|---|---|---|---|
| aoa_signed | 76/76 | 0.5135 [0.4246, 0.595] | 0.194 [0.1094, 0.2806] | 0.01351 [0, 0.04479] | 0 [0, 0] | 67 |
| aoa_two_sided | 76/76 | 0.5135 [0.4246, 0.595] | 0.194 [0.1094, 0.2806] | 0.01351 [0, 0.04479] | 0 [0, 0] | 67 |
| instantaneous_model_a | 75/76 | 0.6892 [0.5937, 0.7904] | 0.6269 [0.527, 0.7361] | 0.4595 [0.3332, 0.6056] | 0.4328 [0.3174, 0.5594] | 67 |
| frozen_temporal | 73/76 | 0.6622 [0.56, 0.7627] | 0.6269 [0.527, 0.7361] | 0.4865 [0.3582, 0.6282] | 0.4179 [0.3043, 0.5469] | 67 |

| Item 33 condition | Median coverage at 2 s (min–max over seeds) | Median coverage at 4 s (min–max) |
|---|---|---|
| C0 | 0.6622 (0.6622–0.6622) | 0.6269 (0.6269–0.6269) |
| C1 | 0.6622 (0.6622–0.7162) | 0.6269 (0.6269–0.6567) |
| C2 | 0.6622 (0.6486–0.7162) | 0.6269 (0.6119–0.6567) |
| C3 | 0.6622 (0.6622–0.6622) | 0.6269 (0.6269–0.6269) |
| X1 | 0.6622 (0.6622–0.6622) | 0.6269 (0.6269–0.6269) |

All lead times (0.5, 1, 2, 3, 4, 5 s), first-event-only coverage and per-seed intervals are in `coverage_item38.json`. The primary definition credits a warning that was active at some point in the 5 s before the crossing; the sustained definition requires the warning to stay on from t − L until the crossing.

## Checks and limitations

- Every input hash matched its audit record; all score vectors match the common population; the existing-definition false-alarm rates and warned-event counts reproduce the values stored by Phase 3 and Item 33 (`cross_checks.json`).
- Previously exposed test data on a regenerated copy; about 1.49 simulated hours and 76 events in 57 trajectories; trajectories may share regime dependencies that the trajectory bootstrap does not model; thresholds are each model's own validation-selected threshold, not a matched operating point.
- No acceptable false-alarm rate or required coverage is defined; nothing here is an operational rate or evidence about real aircraft.
