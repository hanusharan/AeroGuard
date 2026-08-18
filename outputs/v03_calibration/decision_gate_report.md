# AeroGuard — Phase 5 Decision Gate: v0.3 Precursor Calibration

Research question: can the validated aircraft dynamics naturally produce a genuine
2–5s precursor to stall under a more appropriate control profile (not by manufacturing
a signal, but by removing a control-timing artifact)?

Inputs: `outputs/precursor_diagnosis/` (Phase 1–2, real v0.2 data) and
`outputs/v03_calibration/` (Phase 4, 175-trajectory calibration run, seed 20260817,
`scripts/calibrate_v3.py`). v0.2 (`data/*_v2.*`) was never modified or regenerated.

## Baseline (v0.2, real data)

- Median alpha 8°→16° transition: **0.37s** (IQR 0.30–0.57s)
- Median alpha 12°→crossing: **0.18s**
- Separability AUC vs safe background: flat ~0.59–0.61 across the entire 5s→1s
  lead-time range, only sharpening inside the last 0.5s.

## Calibration results (175 trajectories, 35/candidate)

| Candidate | Crossed | Gamma-term | Ground-contact | Full-duration | Median 8→16deg (s) | Median onset(8°)→crossing (s) | ≥2s precursor | ≥3s | ≥4s | ≥5s |
|---|---|---|---|---|---|---|---|---|---|---|
| A tight_margin | 14.3% | 62.9% | 0% | 37.1% | 4.51 | 4.53 | 100% | 80% | 60% | 40% |
| B moderate_margin | 11.4% | 88.6% | 0% | 11.4% | 4.80 | 4.82 | 75% | 50% | 50% | 50% |
| C high_margin | 14.3% | 91.4% | 0% | 8.6% | 1.37 | 1.39 | 40% | 40% | 40% | 40% |
| **D two_stage** | **22.9%** | **31.4%** | 0% | **68.6%** | **5.99** | **6.01** | **100%** | **87.5%** | **87.5%** | **87.5%** |
| E slow_rise_slow_recovery | 25.7% | 71.4% | 0% | 28.6% | 1.80 | 1.81 | 44.4% | 11.1% | 11.1% | 11.1% |

Full data: `v03_calibration_stats.csv` / `.json`. Sample size caveat: 4–9 crossing
events per candidate (calibration-scale, not final-dataset-scale) — directional, not
tightly estimated.

## Interpretation

1. **The mechanism works.** Every candidate beats v0.2's 0.37s/0.18s baseline by a
   wide margin, confirming Phase 2's root cause: the short precursor window was a
   control-profile timing artifact (fast-rise pulses aimed at a far-past-boundary
   equilibrium), not a physics limitation. Slowing the elevator rise to 2–5s and
   aiming closer to the boundary reliably produces smooth, monotonic, multi-second
   `SAFE → GRADUAL APPROACH → NEAR STALL → CROSSING` shapes (`02_alpha_traces_by_candidate.png`).
2. **Single-large-pulse candidates (A/B/C) trade crossing reliability for gamma-envelope
   blowouts.** Holding a large elevator deflection for the multi-second rise+hold
   needed for a slow approach keeps CL elevated long enough that gamma (flight-path
   angle) climbs into the 45° envelope cap on 63–91% of trajectories, usually *without
   ever reaching the alpha boundary* — a physically implausible sustained zoom-climb,
   not a controlled approach.
3. **Candidate D (two-stage, two smaller sequential pulses) resolves this.** Lower
   peak magnitude (0.05–0.09 rad vs 0.07–0.17 rad) and shorter per-pulse duration keep
   gamma in check (31.4% envelope-exceeded, vs 63–91% for the others; 68.6% reach full
   nominal duration) while still producing the **best** precursor statistics of any
   candidate: 100% of crossings have ≥2s precursor, 87.5% have ≥3/4/5s. Verified
   directly against gamma-at-crossing for all 8 crossing events in the calibration
   run — every one terminated `completed_normally`, with gamma at the crossing moment
   ranging from −1.4° to 24.9° (comfortably inside the 45° envelope), confirming the
   crossings themselves are clean, not envelope-boundary artifacts.
4. **E (slow rise, minimal hold) underperforms** — without a sustained hold near the
   boundary, alpha overshoots through the transition zone quickly once the ramp
   catches up, reproducing much of the old fast-crossing behavior (median 1.80s, only
   11% reach ≥3s).

## GO / NO-GO

**GO — recommend building v0.3**, using a regime modeled on **Candidate D
(two-stage)** as the "near_boundary"-equivalent slow-approach regime. This is not
manufacturing a signal: the same validated `aeroguard/` physics, the same pitch model,
the same stall boundary — only the *timing* of the existing calibrated control-profile
approach was changed (two smaller, longer-rise elevator pulses instead of one short
one), which Phase 2 predicted analytically before Phase 4 confirmed it empirically.

**Caveats to carry into v0.3 design** (not blocking, but should shape the next
iteration, not a full 1000-trajectory run yet):
- Candidate D's crossing rate (22.9%) and gamma-termination rate (31.4%) are still
  worse than v0.2 `near_boundary`'s calibrated 11–17%/2–7% — some further tuning
  (e.g. narrowing pulse-2's magnitude range, shortening hold further) is likely needed
  before treating it as final, not just adopting these exact numbers verbatim.
  Only 8 crossing events were observed at calibration scale — real proportions need
  confirmation at a larger (but still not-1000) trial size before locking parameters.
- Throttle is inert for alpha in this model (Phase 2 finding) — confirmed, no further
  throttle-based approach is worth exploring.
- NORMAL and STALL regimes are unchanged and should stay that way; only a
  near_boundary-equivalent regime needs replacing.

## Exact next step

Do **not** generate the full v0.3 dataset yet. Recommended next step: a second,
still-small calibration round (~150–200 trajectories) that fine-tunes Candidate D's
two-pulse magnitude/hold ranges specifically to push gamma-envelope termination down
toward v0.2 `near_boundary`'s 2–7% while preserving the ≥2–5s precursor fractions
achieved here — then, only after that converges, proceed to a full v0.3 dataset
generation (1000 trajectories) and re-run the temporal ML experiment to see whether
the now-genuinely-multi-second precursor moves PR-AUC/lead-time-recall beyond the
current ceiling.
