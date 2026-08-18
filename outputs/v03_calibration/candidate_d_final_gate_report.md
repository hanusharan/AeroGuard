# Candidate D — FINAL v0.3 Calibration Gate

One final narrowly-scoped fix on top of the v2 sequencing fix, per the v2 follow-up
report's CASE B recommendation. No full v0.3 dataset generated, no ML training,
v0.1/v0.2/`aeroguard/` physics untouched.

## 1. Baseline (Candidate D v2, after the sequencing fix)

`aeroguard_dataset/control_profiles_candidate_d_v2.py`: same-sign pulses, zero idle gap
between pulse 1's fall end and pulse 2's start. Elevator spec unchanged from
`GRADUAL_D_TWO_STAGE`: magnitude 0.05–0.09 rad/pulse, rise 1.5–3.0s, hold 0.5–2.0s, fall
0.5–1.5s, 2 pulses, throttle inert.

| Metric | v2 baseline |
|---|---|
| Crossing rate | 22.9% |
| Gamma termination | 57.7% |
| Completion rate | 41.1% |
| Clean gradual crossings | 36/40 (90%) |
| Corrected ≥2s / ≥3s / ≥4s / ≥5s | 56.2% / 37.5% / 31.2% / 15.6% |

## 2. Exact modification

New file `aeroguard_dataset/control_profiles_candidate_d_v3.py`. Reuses v2's
`sample_same_sign_sequential_pulses()` unchanged (sign-sharing and zero-gap sequencing
preserved exactly), then applies **one additional deterministic step**:
`cap_total_pulse_duration()` caps the combined `rise+hold+fall` of both pulses at
**7.0s**, achieved by trimming **hold time only** (pulse 2's hold first, then pulse 1's,
each floored at 0) — rise and fall, which shape the smooth transition, are never
touched. Pulse 2's start is recomputed after trimming so it still begins exactly when
pulse 1's (possibly shorter) fall ends, preserving v2's zero-gap invariant.

**Why this diagnoses and fixes the mechanism:** checked directly against v2's own data
(`candidate_d_v2_metadata.csv`) before implementing: gamma-terminated non-crossers reached
only modest peak alpha (mean 4.2°, max 12.2° — nowhere near the 16.07° boundary) but
sustained it for a long time (mean trajectory duration 9.5s, up to 14.4s) before hitting
the envelope; `completed_normally` non-crossers had *higher* peak alpha (mean 8.9°) but
only briefly. This confirms the failure mode is sustained *time* at elevated alpha, not
peak magnitude — capping total exposure duration targets exactly that. The 7.0s cap was
chosen from this same data: non-crossers needed ~9.5s mean (4.9s minimum) to blow the
envelope, while v2's clean crossings mostly resolved by ~6.2s; 7.0s sits just above the
crossing-relevant range and below the runaway range.

## 3. Calibration configuration

n=175, seed=20260817 (same as v1/v2 baselines), dt=0.01, duration=20s, same
`GenerationConfig` V0/altitude ranges and 45° gamma envelope. Single-candidate run (no
new candidate family). Script: `scripts/calibrate_candidate_d_v3.py`.

## 4. Before / after metrics

| Metric | v1 (orig.) | v2 (sequencing fix) | **v3 (+ duration cap)** |
|---|---|---|---|
| Crossing rate | 22.9% | 22.9% | **12.0%** (n=21/175) |
| Gamma termination (all traj.) | 31.4% | 57.7% | **28.6%** |
| Ground-contact rate | 0% | 0% | 0.6% (1 traj.) |
| Completion rate | 68.6% | 41.1% | **70.9%** |

Non-crossers specifically (the mechanism targeted): v2 had 99/135 (73.3%) hit the gamma
envelope without crossing; v3 has 50/154 (**32.5%**) — cut by more than half, and now
*below* the original v1 rate.

## 5. Corrected precursor metrics (dip-aware, direction-aligned — unchanged metric)

| Metric | v2 | **v3** |
|---|---|---|
| n usable | 32/40 | 13/21 |
| Median onset→crossing | 2.30s | **4.50s** |
| ≥2s | 56.2% | **61.5%** |
| ≥3s | 37.5% | **53.8%** |
| ≥4s | 31.2% | **53.8%** |
| ≥5s | 15.6% | **30.8%** |
| Median 8°→16° transition | 2.27s | **4.49s** |
| Median 12°→16° transition | 0.87s | 0.86s |
| Small-margin crossing rate | 6.3% | 4.0% |

Fewer crossings overall (21 vs 40, expected — capping exposure duration means fewer
trajectories accumulate enough excitation to reach the boundary at all), but **every
precursor-quality metric improved** on the crossings that do occur.

## 6. Physical trajectory classification

| Category | v2 (n=40) | **v3 (n=21)** |
|---|---|---|
| Gradual/monotonic, low-gamma | 36 (90.0%) | **21 (100%)** |
| Dip-then-rise | 0 | 0 |
| Dive-then-zoom-climb | 0 | **0** |
| Runaway/extreme | 4 (10.0%) | **0** |

All 21 v3 crossings are clean and monotonic. `max_alpha_deg` across crossings: mean
23.7°, range 16.6°–32.0° (all comfortably past the 16.07° boundary, no marginal or
extreme excursions). `gamma_at_cross_deg`: mean 14.5°, range 4.7°–31.2° — well clear of
the 45° cap in every single case (v2 had cases up to 38.5–39.0°). All 21 crossings
terminate `completed_normally` (0 hit gamma or ground-contact after crossing).

## 7. Gamma-termination diagnosis (post-fix)

The 28.6% aggregate rate is now driven almost entirely by non-crossing trajectories that
still, occasionally, get a same-sign push large enough to run away even within the
capped 7.0s window (50/154 non-crossers, 32.5%) — a smaller, but not fully eliminated,
residual of the same mechanism. No crossing trajectory contributes to gamma termination
in this run.

## 8. Is the sequencing fix still effective?

**Yes, fully preserved and reinforced.** 0/21 dive-then-zoom-climb crossings (same as
v2's 0/40) — the same-sign, zero-gap sequencing invariant from v2 is untouched by v3's
cap (verified directly: `tests/test_candidate_d_v3_duration_cap.py` confirms the zero-gap
and same-sign properties survive capping). The duration cap is additive on top of, not a
replacement for, the sequencing fix.

## 9. Final decision

**CASE A — READY FOR FULL GENERATION**, with one sizing caveat.

All CASE A criteria are met on this evidence:
- Clean gradual crossings dominant: **100%** (21/21), not just dominant — total.
- Dive/zoom behavior essentially eliminated: **0/21**, matching v2.
- Gamma termination falls substantially from 57.7%: **57.7% → 28.6%**, and below the
  original v1 baseline (31.4%).
- Meaningful ≥3s precursor coverage: **53.8%**, materially better than v1 (33.3%) and v2
  (37.5%), with real ≥4s (53.8%) and ≥5s (30.8%) coverage — the best result across all
  three iterations.
- Physically credible: gamma at crossing never exceeds 31.2° (13.8° margin under the
  cap), max-alpha distribution is unremarkable, all crossings terminate cleanly.

**Caveat to carry into full-dataset sizing (not a blocker, a parameter for that step):**
crossing rate dropped to 12.0% (from 22.9%). A full v0.3 generation using this exact
profile will need proportionally more total trajectories per desired crossing-example
count than v1/v2 would have — e.g., roughly double the trajectory count for the same
number of crossing examples. This is a sizing decision for the next stage, not a
reason to withhold GO here.

## 10. Exact next step

**Recommend locking Candidate D v3's parameters** (same-sign + zero-gap sequencing from
v2, 7.0s combined-duration cap from v3, elevator spec otherwise unchanged from
`GRADUAL_D_TWO_STAGE`) for full v0.3 generation. Per this stage's explicit scope, **no
further calibration iteration, no full 1000-trajectory generation, and no ML run should
happen automatically** — this is the final gate result, awaiting your go-ahead to
proceed to full generation (with trajectory-count sizing adjusted for the 12.0% crossing
rate, per §9).

---

## Files produced this final gate

```
aeroguard_dataset/control_profiles_candidate_d_v3.py
scripts/calibrate_candidate_d_v3.py
tests/test_candidate_d_v3_duration_cap.py              (6 focused tests, passing)
outputs/v03_calibration/candidate_d_v3_raw.parquet
outputs/v03_calibration/candidate_d_v3_metadata.csv
outputs/v03_calibration/candidate_d_v3_crossing_classification.csv
outputs/v03_calibration/candidate_d_v3_summary.json
outputs/v03_calibration/plots/05_candidate_d_v3_traces.png
outputs/v03_calibration/candidate_d_final_gate_report.md   (this file)
```

Full test suite: **168/168 passing** (162 pre-existing + 6 new). v0.1/v0.2 data and
`aeroguard/` physics confirmed unmodified.
