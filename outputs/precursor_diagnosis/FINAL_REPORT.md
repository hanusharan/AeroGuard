# AeroGuard — Precursor-Signal Diagnosis & v0.3 Calibration Report

**Research question:** Can AeroGuard learn to predict an approaching stall several seconds
BEFORE it happens from physically meaningful precursor signals? **Can the current simulator
even generate trajectories that contain such precursors?**

**Scope of this stage:** read-only diagnosis of v0.2 (Phases 1–2) + a small (150-trajectory)
calibration of 5 v0.3 candidate control profiles (Phases 3–4), per the task's explicit "STOP
after diagnostic + calibration" instruction. No full v0.3 dataset was generated, no deep
learning was run, v0.1/v0.2 and `aeroguard/` physics were not modified. New artifacts only,
under `outputs/precursor_diagnosis/` and `outputs/v03_calibration/`.

**Note on session state:** partway through this work, a concurrent process modified this
repository directly — it added `GRADUAL_APPROACH_CANDIDATES`/`make_v03_calibration_config` to
`aeroguard_dataset/config.py` and a new `scripts/calibrate_v3.py`, and overwrote this session's
`tests/test_v03_candidates.py` with tests for that other code. It did not touch the validated
v0.1/v0.2 regime configs or any file this session created. That other implementation was left
alone; this report and all findings below come from this session's own independent analysis and
calibration run (`aeroguard_dataset/control_profiles_v03_candidates.py`,
`scripts/calibrate_v03.py`, `scripts/precursor_diagnosis.py`), with the test file restored to
match. The two are not reconciled — that is a separate decision for you to make.

---

## 1. Root cause of the weak early-warning signal

Two distinct, compounding causes, both confirmed by tracing real v0.2 trajectories:

1. **The alpha ramp itself is fast in both regimes that ever cross the boundary.** In
   `near_boundary`, alpha/elevator/pitch_rate are essentially flat from 5s to ~1s before
   crossing, then rise sharply in the final <1s (median alpha 8°→16° transit = **0.54s**). In
   `stall`, the same pattern is worse (median transit = **0.33s**), and only 24.5% of stall
   crossings are even nose-up (39% are negative-alpha/nose-down departures — a second failure
   mode, not a slow approach at all). The pooled analysis in the existing
   `outputs/ml_temporal/metrics/physics_diagnosis.csv` (AUC 0.51–0.61 at all lead times) masked
   a real regime split: **`near_boundary` alone shows AUC 0.78–0.99** for elevator/alpha/stall_margin
   even at 5s out, while **`stall` alone never exceeds AUC 0.64** at any lead time 0.5–5s (see
   `outputs/precursor_diagnosis/separability_by_regime.csv`).
2. **That `near_boundary` separability is a *level* effect, not a *trend* effect — the exact
   confusion the task warned against.** Crossing trajectories in `near_boundary` already sit at a
   higher baseline alpha (~6.5–7°) even 5s before crossing, purely because they're generated with
   larger-magnitude pulses; the classifier signal is "this trajectory has an elevated operating
   point," not "alpha is rising toward the boundary right now." The direction-aligned exact-offset
   trace (`exact_offset_summary_by_regime.csv`) shows alpha_mean essentially flat 0.11–0.12 rad
   from 5s→1s before crossing in `near_boundary`, only accelerating in the final 1s — consistent
   with the 0.54s median transit above. This is also *why* the temporal-ML generalization check
   collapsed (stall-regime recall 67.4%→6.3% when stall trajectories were excluded from
   training): the model was partly learning "which regime/trajectory-shape is this," not a
   transferable real-time trend.

Physical mechanism (traced through real trajectories, `crossing_ramp_mechanism.csv`):
`STALL_CONTROL_CONFIG`'s large magnitude (0.19–0.32 rad) and long hold (2–5s) drive **3.51s
median** of near-peak elevator held *after* crossing, and separately, **56/250 (22.4%) of the
entire `stall` regime allocation hits the 45° gamma envelope without ever crossing alpha_stall at
all** — pure wasted generation budget, confirming the "trajectories terminate at gamma envelope
before reaching a useful precursor" hypothesis for a meaningful slice of that regime.

## 2. Quantitative precursor analysis at 5/4/3/2/1/0.5s

Full tables: `outputs/precursor_diagnosis/exact_offset_summary_by_regime.csv` (direction-aligned
means/medians per regime) and `separability_by_regime.csv` (AUC + Cohen's d per variable).

Direction-aligned alpha (rad), evolution toward whichever boundary was actually crossed:

| Offset before crossing | near_boundary alpha (n) | stall alpha (n) |
|---|---|---|
| 5.0s | 0.125 (12) | 0.026 (62) |
| 4.0s | 0.111 (18) | 0.018 (85) |
| 3.0s | 0.111 (26) | 0.023 (110) |
| 2.0s | 0.114 (28) | 0.020 (147) |
| 1.0s | 0.119 (31) | 0.027 (161) |
| 0.5s | 0.160 (31) | 0.107 (161) |
| 0.0s (crossing) | 0.282 (31) | 0.282 (161) |

Both regimes: **flat for 4.5 of the 5 seconds, then a sharp rise only in the final 0.5–1s.**
`stall` starts much closer to zero (near-trim) and is *entirely* flat until 1s out — there is no
usable multi-second ramp in that regime at all. `elevator` and `pitch_rate` show the identical
shape (flat, then a sharp final-second jump) — see the same CSV.

Separability (AUC, near-crossing vs. matched-safe rows, `n_near_crossing`/`n_safe` per cell in
the CSV): `near_boundary` alpha/elevator/stall_margin are 0.78–0.99 at every lead time 0.5–5s
(a level effect, per §1); `stall` never exceeds 0.64 for any variable at any lead time — direct
confirmation that **stall-regime rows carry almost no univariate information about an approaching
crossing until under ~1s out**, and that whatever separability exists in the pooled dataset comes
almost entirely from `near_boundary`, which is only 31/1000 trajectories.

## 3. Which physical variables actually contain useful information

`elevator`, `alpha`, and `stall_margin` (algebraically tied to alpha) are the only variables with
real separability, and only in `near_boundary` (AUC up to 0.99 at 0.5s, 0.82–0.89 further out).
`V`, `gamma`, and all the rate variables (`dV_dt`, `dalpha_dt`, `dgamma_dt`, `dq_dt`) stay near
chance (AUC 0.50–0.65) at every lead time in both regimes — consistent with the existing temporal
ML report's finding that 1-step derivatives added only marginal value. `V` in `near_boundary`
alone reaches AUC ~0.76–0.78 (crossing trajectories tend to be somewhat slower), a secondary,
weaker signal.

## 4. Which regimes contain the signal

**`near_boundary` only**, and even there it is dominated by a between-trajectory level effect
rather than a within-trajectory rising trend (§1). `stall` contains effectively no multi-second
precursor signal in the existing v0.2 data — it is a departure regime, not an approach regime, and
worse, 39% of its crossings are negative-alpha (nose-down) events, a different failure mode
entirely. `normal` never crosses (0/500), so it cannot be assessed and was excluded from the AUC
table by construction.

## 5. Can the simulator plausibly generate 2–5s precursor events?

**Only marginally, and with a real physical cost.** The Phase 4 calibration (below) shows that
deliberately slowing the elevator rise time roughly triples the median 8°→16° transit time
(0.54s → 0.90–1.76s across 5 candidates) and, in the best candidate, gets 20% of crossings to a
≥2s window — genuine, non-trivial movement. But **0 of 5 candidates ever produced a single ≥3s
precursor event**, and the mechanism that produces the improvement (sustained elevated alpha over
several seconds) also **necessarily accumulates flight-path angle**, since gamma responds to
sustained excess lift/alpha with no altitude-based restoring force in this simplified dynamics
model. The result: gamma-envelope termination jumped from 22.7% (v0.2 `near_boundary` baseline)
to **57–80%** across all 5 candidates, and 43–77% of *all* generated trajectories are "wasted" —
they hit the 45° gamma cap in an unconstrained climb or dive *without ever crossing alpha_stall*
(traced directly: `traj_0000` under candidate A dives from level flight to −45° gamma in 2.7s
while alpha only reaches −9.8°, well short of the −16° boundary; see
`outputs/v03_calibration/calibration_raw_trajectories.parquet`). One trajectory (`traj_0001`,
candidate A) does show the target pattern cleanly — alpha climbing 3.6°→15.3° smoothly over
t=4→7s while gamma also climbs from ~0°→30° — but it is the exception, not the rule, and even it
terminates via gamma shortly after crossing.

## 6. Candidate v0.3 control-profile designs

Five candidates (`aeroguard_dataset/control_profiles_v03_candidates.py`), all elevator-only
variants of `NEAR_BOUNDARY_CONTROL_CONFIG` with substantially lengthened rise time (the
diagnosed bottleneck from §1), holding pulse count/channel-selection identical to the validated
near_boundary regime:

| Candidate | Magnitude (rad) | Rise (s) | Hold (s) | Fall (s) |
|---|---|---|---|---|
| v03_a gentle_long_rise | 0.14–0.20 | 3.0–5.0 | 1.0–3.0 | 1.0–2.0 |
| v03_b gentle_longer_rise_lower_mag | 0.12–0.17 | 4.0–6.0 | 1.0–2.5 | 1.0–2.0 |
| v03_c moderate_rise_higher_mag | 0.16–0.24 | 2.0–3.5 | 1.0–2.5 | 1.0–2.0 |
| v03_d very_gentle_rise | 0.15–0.22 | 5.0–7.0 | 0.5–2.0 | 1.5–2.5 |
| v03_e gentle_rise_short_hold | 0.16–0.23 | 3.0–5.0 | 0.0–0.5 | 1.0–2.0 |

(v0.2 `near_boundary` baseline for comparison: magnitude 0.12–0.20, rise 0.4–1.0, hold 0.0–0.4,
fall 0.6–1.6.)

## 7. Calibration results

30 trajectories/candidate, 150 total, seed base 20260818 (`outputs/v03_calibration/`):

| Candidate | Crossed % | Gamma-term % | Median α8→cross (s) | ≥1s precursor | ≥2s precursor | ≥3s precursor |
|---|---|---|---|---|---|---|
| v03_a | 43.3% | 66.7% | 1.48 | 100% | 9.1% | 0% |
| v03_b | 6.7% | 80.0% | 1.69 | 100% | 0% | 0% |
| v03_c | 23.3% | 66.7% | 0.90 | 14.3% | 0% | 0% |
| v03_d | 16.7% | 76.7% | 1.76 | 100% | **20.0%** | 0% |
| v03_e | 46.7% | 56.7% | 1.32 | 100% | 0% | 0% |
| **v0.2 baseline** | 20.0%* | 22.7%* | 0.54 | 4.2% | 0% | 0% |

(*v0.2 baseline figures are whole-`near_boundary`-regime, n=250, from
`outputs/dataset_audit_v2_calibration/`, for reference scale — not a rerun.)

Every candidate improved median transit time (~2–3x) over baseline, and v03_d reached a
meaningful ≥2s precursor rate. But every candidate also made gamma-envelope termination
*dramatically* worse (57–80% vs. 22.7%), and none ever reached a ≥3s event. Ground-contact rate
stayed 0% throughout (not a factor here). Full per-candidate stats, including
`frac_spent_meaningful_time_8_16deg_pct` and `future_stall_5s` label composition:
`outputs/v03_calibration/candidate_calibration_summary.csv`.

## 8. GO / NO-GO decision for v0.3

**NO-GO** on generating a full v0.3 dataset from any of the 5 tested candidates.

None satisfies the Case A bar ("substantially more genuine 2–5s precursor events *without*
pathological gamma/post-stall behavior") — the gamma-termination rate got 2.5–3.5x worse for a
gain that tops out at a 20% ≥2s rate and 0% ≥3s across all candidates. This is not read as "the
simulator has zero exploitable precursor signal" (Case B) either — the ~3x median-transit
improvement and the one clean `traj_0001` example show a real, physically-generated capability
exists, just well short of the 2–5s target and currently bought at an unacceptable cost in
physically-degenerate trajectories.

This lands as **Case C: minor/mixed improvement.** One more narrowly-targeted calibration round
is scientifically justified before concluding negatively (see §9) — but it should not be another
blind magnitude/rise sweep; it should test a specific, mechanistically-motivated design.

## 9. Exact next step

**Do not scale any of the 5 tested candidates to a full dataset.** If the precursor-signal
question is still worth pursuing, the next and *last* recommended calibration round (not run in
this stage, per the task's stop instruction) should test a **two-stage elevator profile**: a
small, slow initial pulse that brings alpha to ~8–10° over 2–3s while gamma stays small (low
excess-lift, low accumulated climb), followed by a second, faster pulse that completes the
approach through 10°→16°. This is motivated directly by the one clean `traj_0001` trace in §5 and
is achievable within the existing `Pulse`/multi-pulse framework (`n_pulses_choices=(2,)`) without
touching `aeroguard/` physics — i.e., still "control-profile parameters only." If a two-stage
profile still cannot decouple the alpha ramp from gamma accumulation without pathological
termination rates, that would be much stronger evidence for Case B (the dynamics genuinely don't
support a multi-second precursor) than this round's simple rise-time sweep was, and the research
should proceed to the negative conclusion: **this simulator, as currently specified, cannot
reliably produce the 2–5s stall precursors needed for a genuine multi-second early-warning
system**, and the ML bottleneck documented in the Stage-4 temporal experiment report is a data
limitation, not a model-complexity one — confirming that report's own conclusion, now traced to a
specific, physically-explained cause rather than inferred from ML metrics alone.

Either way, this decision belongs to you, not to further autonomous escalation — per the task's
explicit stop instruction, no v0.3 full dataset, no two-stage calibration round, and no further ML
experiment should be run without your go-ahead.

---

## Files produced this session

```
outputs/precursor_diagnosis/
  exact_offset_raw.csv                    (per-trajectory, per-offset raw samples, direction-aligned)
  exact_offset_summary_by_regime.csv      (Q1-Q4 answer: mean/median/std by regime x offset)
  separability_by_regime.csv              (Q5 answer: AUC + Cohen's d by regime x variable x lead time)
  crossing_ramp_mechanism.csv             (Phase 2: alpha8->cross, alpha12->cross, elevator-hold timing)
  run_manifest.json
  plots/01_variable_evolution_before_crossing.png
  plots/02_separability_auc_heatmap.png
  FINAL_REPORT.md                         (this file)

outputs/v03_calibration/
  candidate_calibration_summary.csv / .json
  calibration_raw_trajectories.parquet    (150 trajectories, full telemetry)
  calibration_metadata.csv

aeroguard_dataset/control_profiles_v03_candidates.py   (5 candidate RegimeControlConfigs)
scripts/precursor_diagnosis.py                          (Phase 1-2 analysis script)
scripts/calibrate_v03.py                                (Phase 4 calibration script)
tests/test_v03_candidates.py                            (4 focused tests, passing)
```

Full test suite: 157/157 passing (153 pre-existing + 4 new). No existing file under `aeroguard/`,
`aeroguard_dataset/config.py`, `data/`, or `outputs/ml_temporal|ml_baseline|dataset_audit*` was
modified.
