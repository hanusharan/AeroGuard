# AeroGuard Items 37, 38, 39 — False alarms, warning coverage, trajectory and event counts

| | |
|---|---|
| **Status** | Pre-specified before any Item 37–39 number was computed. Committed before the analysis runs. |
| **Scope** | Item 39 (trajectory and event counts), Item 37 (false alarms per simulated flight hour), Item 38 (warning coverage at lead times). Descriptive evaluation of **already stored** test scores. No model is trained or re-scored. |
| **Evidence** | E2 on previously exposed test data (regenerated v0.3 copy, Item 26). Not blind, not independent replication. Simulation only: nothing here describes real aircraft or an operational false-alarm rate. |

## 1. Inputs (all hash-checked against their own audit records before use)

- **Test panel** `ml_temporal_v03/temporal_test.parquet` (SHA-256 `c03634b4…41b8`), columns `trajectory_id, time, is_unsafe, future_stall_5s, future_stall_5s_available, time_to_stall` and the ten 1 s window columns; train/validation panels for the Item 39 counts only (keys and labels, no features).
- **Tracked metadata** `data/metadata/trajectory_metadata_v3.csv` and `data/splits/split_manifest_v3.csv` (Item 39 only).
- **Stored scores and thresholds** (strict `score > threshold`):
  - Phase 3 run `run_20261013T140820817642Z`: `aoa_signed`, `aoa_two_sided`, `instantaneous_model_a`, `frozen_temporal` (thresholds in its `metrics_primary.json`; score hashes in its `audit.json`).
  - Item 33 run `run_20261013T162344038252Z`: 25 retrained models C0, C1, C2, C3, X1 × seeds 20260817, 20261101–20261104 (thresholds in `threshold_<c>_<s>.json`; hashes in its `audit.json`).
- **Population:** the common 1 s usable test rows (538,034 rows, 456 trajectories; key hash `806ab81b786ec704…` recorded by Item 33). Every score vector must match this key set and length, or the run stops.

## 2. Item 39 — trajectory and event counts

For train, validation and test: trajectories in the split manifest and in the panel; trajectories with at least one usable row; trajectories excluded (no usable row) with the reason taken from the metadata (`n_steps`, `termination_reason`; a trajectory needs more than 600 steps for any row to have both a full 1 s history and a full 5 s label horizon); usable rows; eligible duration (sum over trajectories of last minus first usable time, and rows × 0.01 s). For the test split also: stall events in usable rows (maximal runs of `is_unsafe`, existing `ml/events.py` definition), first and later events, trajectories with and without events, trajectories with an unsafe run that lies entirely outside the usable rows (events excluded from evaluation, with the reason), regime (`generation_mode`) breakdown of trajectories, rows, events and positive rows, duplicate key check, trajectory overlap across splits, duplicate initial conditions in the metadata. Independent units are stated explicitly: frames are not independent; trajectories are the resampling unit; event-bearing trajectories are the effective unit for event metrics.

## 3. Item 37 — false-warning episodes per simulated flight hour

- **Warning episode:** a maximal run of consecutive usable rows of one trajectory with `score > threshold` (existing `group_boolean_into_episodes`).
- **Classification by the episode's first row:** TRUE if `future_stall_5s == 1`; ONGOING if `future_stall_5s == 0` and `is_unsafe` is true (a warning that starts at the end of a stall with no further crossing within 5 s); FALSE otherwise.
- **Primary rate:** FALSE episodes / eligible simulated hours, where eligible hours = Σ over trajectories (last usable time − first usable time) / 3600 (the existing denominator, 5,375.78 s ≈ 1.49 h).
- **Pre-specified sensitivities:** (a) the existing `ml/events.py` definition, which counts ONGOING episodes as false; (b) merging episodes separated by a gap of at most g seconds, g ∈ {1.0, 2.0} (gap = start of the next episode minus end of the previous minus 0.01 s); (c) the rows × 0.01 s denominator.
- **Also reported:** total episodes, TRUE episodes, episode-level precision (TRUE / (TRUE + FALSE)), false episodes per trajectory, number of trajectories with at least one false episode, and false episodes by regime.

## 4. Item 38 — warning coverage at lead times

- **Lead times:** L ∈ {0.5, 1, 2, 3, 4, 5} s; **2 s and 4 s are the headline values**. The sampling interval is 0.01 s, so every L is resolvable; the labelling horizon is 5 s, so no L above 5 s is defined.
- **Primary (existing definition):** an event's lead time is computed as in `ml/events.py` (earliest warning episode active in (t_c − 5 s, t_c) that starts before the crossing t_c; lead = t_c − max(episode start, t_c − 5 s)). Covered at L iff lead ≥ L.
- **Sensitivity (sustained warning):** covered at L iff every usable row in [t_c − L, t_c) is predicted positive (the warning is on at t_c − L and stays on until the crossing).
- **Eligibility at L:** an event counts in the denominator at L only if its trajectory has usable rows covering [t_c − L, t_c) (otherwise no warning L seconds ahead could have been observed). Excluded events are counted and reported per L.
- **Reported:** coverage for all events and for first events only; numerator and denominator per L.

## 5. Uncertainty

Trajectory bootstrap, B = 1000, seed 20261013, percentile 95% interval: whole test trajectories are resampled with replacement; rates and coverages are ratio estimators recomputed per replicate (Σ numerator / Σ denominator over drawn trajectories). Replicates with a zero denominator are counted as undefined, not dropped silently. Intervals are per method and descriptive; no method-versus-method test is made here (that is Items 40–41). With about 1.49 eligible hours and 76 events in 57 trajectories, intervals are expected to be wide.

## 6. Reporting rules

Rates are per **simulated** flight hour of eligible evaluation time, not operational rates. No acceptable false-alarm rate or required coverage is defined or invented. Phase 3 methods and Item 33 models are reported separately; Item 33 models are summarised per condition across seeds (median, min, max) with every seed in the machine-readable output. No result is called blind, independent, confirmatory, or evidence about real aircraft.
