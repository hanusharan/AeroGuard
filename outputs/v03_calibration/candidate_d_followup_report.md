# Candidate D Follow-up — Same-Sign / Zero-Gap Sequencing Fix

One narrowly-scoped calibration per the reconciliation report's CASE B recommendation. No
full v0.3 dataset generated, no ML training, v0.1/v0.2/`aeroguard/` physics untouched
(verified: `aeroguard/*.py` and `data/processed/processed_dataset_v2.parquet` /
`data/metadata/trajectory_metadata_v2.csv` MD5-unchanged from before this session).

## 1. Baseline Candidate D parameters (canonical, `aeroguard_dataset/config.py:GRADUAL_D_TWO_STAGE`)

```
elevator: magnitude 0.05-0.09 rad, rise 1.5-3.0s, hold 0.5-2.0s, fall 0.5-1.5s
n_pulses_choices=(2,), both_channels_prob=0.0, elevator_prob_if_single=1.0
throttle: inert (magnitude 0.0-0.0)
```
Reconciliation baseline (reproduced exactly, see `outputs/v03_calibration/candidate_d_metric_comparison.csv`):
crossed 22.9%, gamma-term 31.4%, completed 68.6%, corrected (dip-aware, direction-aligned) ≥3s
precursor = 33.3% (2/6 usable crossings, n=8 crossings total).

## 2. Exact modification

New file `aeroguard_dataset/control_profiles_candidate_d_v2.py`. `GRADUAL_D_TWO_STAGE`'s
elevator `ControlRangeSpec` (magnitude/rise/hold/fall ranges) is imported unchanged.
`aeroguard_dataset/config.py`, `control_profiles.py`, and `dataset_builder.py` are untouched.
Two changes to how the 2 pulses are sequenced/signed, both purely at generation time (no
runtime feedback, no physics change):

1. **One shared sign for both pulses** (drawn once, applied to both), replacing
   `sample_pulses()`'s independent per-pulse random sign. Directly rules out the observed
   sign-reversal dive/recovery mechanism (traj_0013: pulse 1 negative → −26° gamma dive;
   pulse 2 positive → +42° zoom recovery before crossing 8s later).
2. **Zero idle gap**: pulse 2 starts exactly when pulse 1's fall ends
   (`t_cursor = start + rise + hold + fall`), replacing the unconstrained
   `rng.uniform(0.3, 1.5)`s gap. Keeps pulse 2 picking up from wherever pulse 1's fall left
   alpha, rather than after alpha has relaxed back toward trim — the generation-time proxy for
   "pulse 2 activates only once alpha is already at/above the approach region," achieved
   without observing alpha at runtime.

## 3. Calibration configuration

n=175 (same as reconciliation baseline), seed=20260817 (same), dt=0.01, duration=20s, same
`GenerationConfig` V0/altitude ranges and 45° gamma envelope. All 175 trajectories use
Candidate D v2 (single-candidate run — no new candidate family). Script:
`scripts/calibrate_candidate_d_v2.py`.

## 4. Full metrics table

| Metric | Candidate D v1 (baseline) | Candidate D v2 (this run) |
|---|---|---|
| n trajectories | 35 | 175 |
| Crossing rate | 22.9% | **22.9%** (identical, n=40) |
| Gamma-termination rate (all trajectories) | 31.4% | **57.7%** (worse — see §8) |
| Ground-contact rate | 0% | 0% |
| Low-airspeed termination | 0% | 1.1% (new, small) |
| Completion rate | 68.6% | 41.1% (worse — see §8) |

## 5. Corrected precursor metrics (dip-aware, direction-aligned — the only primary metric used)

| Metric | v1 (n=6 usable / 8 crossings) | v2 (n=32 usable / 40 crossings) |
|---|---|---|
| Median onset→crossing | 2.23s | 2.30s |
| ≥2s | 66.7% | **56.2%** |
| ≥3s | 33.3% | **37.5%** |
| ≥4s | 33.3%* | **31.2%** |
| ≥5s | 33.3%* | **15.6%** |
| Median 8°→16° transition | n/a (v1 not computed this way) | 2.27s |
| Median 12°→16° transition | n/a | 0.87s |
| Small-margin crossing rate | 8.6% (v1, n=35) | 6.3% |

(*v1's ≥3/4/5s were identical at 33.3% because only 2/6 usable crossings ever exceeded 3s, and
none exceeded 5s further — small-n artifact, not a plateau.)

v2 gives 5x the crossing sample (40 vs 8) with comparable-or-better ≥3s coverage on a far more
reliable base rate, and meaningful (not negligible) ≥4s/≥5s coverage.

## 6. Physical trajectory classification (Phase 3C, all 40 crossings)

| Category | Count | % |
|---|---|---|
| Gradual/monotonic, low-gamma | **36** | **90.0%** |
| Dip-then-rise | 0 | 0% |
| Dive-then-zoom-climb (gamma sign-flip) | 0 | 0% |
| Runaway/extreme (max\|gamma\|≥40° without a sign-flip) | 4 | 10.0% |

Only categories counted as "clean gradual precursor": **36/40 (90%)**. Full per-trajectory
detail, including `gamma_at_cross`: `outputs/v03_calibration/candidate_d_v2_crossing_classification.csv`.
Representative traces: `outputs/v03_calibration/plots/04_candidate_d_v2_traces.png`.

## 7. Before vs. after — was the dive/zoom-climb mechanism reduced?

**Yes, essentially eliminated for actual crossings.** 0/40 v2 crossings show the gamma
sign-flip pattern (traversing both >15° and <−15° within the pre-crossing window) that defined
traj_0013 and similar v1 cases; v1's reproduction had 5/8 crossings (62.5%) showing metric
inflation from exactly this kind of non-monotonic approach. Among crossing trajectories
specifically, termination is now overwhelmingly clean: of the 40 crossings, 37 (92.5%)
`completed_normally`, only 2 hit the gamma envelope and 1 hit low-airspeed — **after** crossing,
not as a pre-crossing artifact.

**But a new, distinct cost appeared: non-crossing trajectories got worse.** Breaking down the
57.7% aggregate gamma-termination rate by outcome: of 135 non-crossing trajectories, **99
(73.3%)** hit the gamma envelope without ever reaching the boundary (`outputs/v03_calibration/candidate_d_v2_metadata.csv`).
Forcing both pulses to the same sign removes the "lucky cancellation" that, in v1, let
opposite-sign pulse pairs partially cancel and settle back to safety; now, when a same-sign
two-pulse push is large enough to matter but not quite large enough to cross, it more often
runs away into an unconstrained climb or dive that trips the 45° cap without ever producing a
stall example. This is a real, mechanistically-understood side effect of the fix, not noise —
it is the accurate cost side of an accurate benefit.

## 8. GO / CONDITIONAL GO / NO-GO

**CASE B — need one more specific fix**, not CASE A.

Per-crossing precursor quality and physical credibility clearly improved (90% clean/monotonic,
sign-flip dive mechanism eliminated, ≥3s coverage on a 5x larger, more reliable crossing
sample). But "gamma termination reasonably controlled" — an explicit CASE A requirement — is
not met: it nearly doubled in aggregate (31.4%→57.7%), driven entirely by non-crossing
trajectories now running away instead of cancelling out. This is one identifiable, specific
mechanism (not a diffuse or fundamental limitation), which is exactly the CASE B bar.

**One additional narrowly-scoped fix to consider (not started):** cap the *combined* two-pulse
magnitude/duration so a same-sign pair that would drive alpha well past the boundary is capped
before generation (e.g., bias pulse 2's magnitude range downward when pulse 1 already pushed
alpha close to the approach region), so same-sign trajectories that don't cross still decay
back toward trim instead of running away. This is scoped for a future decision, not executed
here.

## 9. Exact next action

Do **not** generate the full v0.3 dataset — gamma-termination among non-crossing trajectories
is not yet controlled. Do **not** auto-start the combined-magnitude-cap fix proposed in §8 — it
requires your approval as the next CASE-B iteration. No further action taken this session
beyond this report.

---

## Files produced this follow-up

```
aeroguard_dataset/control_profiles_candidate_d_v2.py
scripts/calibrate_candidate_d_v2.py
tests/test_candidate_d_v2_sequencing.py               (5 focused tests, passing)
outputs/v03_calibration/candidate_d_v2_raw.parquet
outputs/v03_calibration/candidate_d_v2_metadata.csv
outputs/v03_calibration/candidate_d_v2_crossing_classification.csv
outputs/v03_calibration/candidate_d_v2_summary.json
outputs/v03_calibration/plots/04_candidate_d_v2_traces.png
outputs/v03_calibration/candidate_d_followup_report.md   (this file)
```

Full test suite: **162/162 passing** (157 pre-existing + 5 new). No existing RUN A/RUN B file,
v0.1/v0.2 data, or `aeroguard/` physics modified.
