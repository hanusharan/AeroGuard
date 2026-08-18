# AeroGuard v0.3 — Full Dataset Generation Report & Decision Gate

Full v0.3 dataset generated using the locked Candidate D v3 profile (CASE A / READY,
`outputs/v03_calibration/candidate_d_final_gate_report.md`). No parameters were tuned after
seeing results. v0.1/v0.2 data, `aeroguard/` physics, and all existing ML outputs confirmed
untouched (MD5-verified unchanged from pre-generation state).

## Locked Candidate D v3 parameters (used exactly as calibrated, unmodified)

From `aeroguard_dataset/control_profiles_candidate_d_v3.py` (imported, not redefined):
- Elevator: magnitude 0.05–0.09 rad/pulse, rise 1.5–3.0s, hold 0.5–2.0s, fall 0.5–1.5s
  (identical to `GRADUAL_D_TWO_STAGE`'s spec)
- Sequencing (v2 fix, reused unchanged): both pulses share one randomly-drawn sign; pulse 2
  starts exactly when pulse 1's fall ends (zero idle gap)
- Duration cap (v3 fix, reused unchanged): combined rise+hold+fall ≤ 7.0s, enforced by
  trimming hold time only (floor 0), never rise/fall
- 2 pulses, throttle inert

## Trajectory-count calculation (stated before generation)

Candidate D v3's calibration crossing rate: 21/175 = 12.0%. Wilson 95% CI: [8.0%, 17.6%].
Target: match or beat v0.2's total crossing count (192, from `trajectory_metadata_v2.csv`).
Used the **conservative CI lower bound** (8.0%, not the point estimate) so the target holds
even under the pessimistic end of calibration uncertainty:

```
N_gradual = ceil(192 / 0.080) = 2400
```

`normal` (500) and `stall` (250) kept at v0.2's own **absolute counts**, configs unchanged —
stall-regime crossings are known (reconciliation work) to have ~0.33s median precursor, so
padding the crossing target with more stall trajectories would not serve the actual research
goal; the 192-crossing target is sized against `gradual_approach_v3` alone.

```
N_total = 500 + 250 + 2400 = 3150
```

## Generation-time tracking (all regimes, actual results)

| Metric | normal | stall | gradual_approach_v3 | Total |
|---|---|---|---|---|
| Count | 500 | 250 | 2400 | 3150 |
| Completed normally | 500 | 80 | 1693 | 2273 |
| Gamma termination | 0 | 170 | 688 | 858 |
| Ground-contact | 0 | 0 | 19 | 19 |
| Low-speed termination | 0 | 0 | 0 | 0 |
| Numerical failures | 0 | 0 | 0 | 0 |
| Crossed boundary | 0 | 153 (61.2%) | 317 (13.2%) | 470 (14.9%) |

`future_stall_5s`: 310,404 positive / 3,467,445 negative / 1,563,016 unavailable (final 5s of
each trajectory, by design) — positive rate 8.2% of available rows (v0.2: 7.0%).

Max |gamma| observed: 45.45° (within the 45° envelope + one floating-point step, matches v0.2's
own pattern of recording the boundary-crossing sample). Min altitude: 0.020m (never ≤0 —
ground-contact fix preserved). Alpha range: −41.22° to 76.19°. Airspeed range: 13.72–132.47 m/s.

## Corrected precursor metrics (dip-aware, direction-aligned — unchanged metric), at full scale

| Metric | Calibration (n=21) | **Full v0.3 gradual_approach_v3 (n=317)** | stall (n=153, for contrast) |
|---|---|---|---|
| n usable for metric | 13 | 194 | 144 |
| Median onset→crossing | 4.50s | **4.38s** | 0.38s |
| ≥0.5s | — | 100.0% | 16.7% |
| ≥1s | — | 99.5% | 1.4% |
| ≥2s | 61.5% | **66.0%** | 0.0% |
| ≥3s | 53.8% | **59.3%** | 0.0% |
| ≥4s | 53.8% | **55.7%** | 0.0% |
| ≥5s | 30.8% | 13.4%* | 0.0% |
| Median 8°→16° transition | 4.49s | 4.36s | 0.36s |
| Median 12°→16° transition | 0.86s | 0.74s | 0.20s |
| Small-margin crossing rate | 4.0% | 4.5% | 3.6% |

(*≥5s dropped from the calibration's 30.8% — expected: that figure was based on only 13
usable crossings, high variance; 194 usable crossings at full scale gives a far more reliable
estimate. Every other threshold reproduced calibration numbers closely.)

## Physical trajectory classification, at full scale

| Category | Calibration (n=21) | **Full v0.3 (n=317)** |
|---|---|---|
| Gradual/monotonic, low-gamma | 21 (100%) | **314 (99.1%)** |
| Dip-then-rise | 0 | 0 |
| Dive-then-zoom-climb | 0 | **0** |
| Runaway/extreme | 0 | 3 (0.9%) |

The dive-then-zoom-climb mechanism (the original problem this whole effort targeted) remains
**fully eliminated at scale** (0/317). A small residual runaway fraction (3/317, 0.9%) appeared
that wasn't visible in the 21-trajectory calibration sample — expected at 15x the sample size,
and small enough not to be concerning (99.1% clean is a strong result, not a red flag).

## Integrity checks (all passed)

| Check | Result |
|---|---|
| No NaN/Inf in raw data | ✅ (0 missing, 0 infinite) |
| Processed NaN pattern | ✅ documented only (first-row derivatives, final-5s labels) |
| No duplicate rows (raw/processed) | ✅ 0 / 0 |
| No duplicate trajectory IDs | ✅ 0 in metadata, 0 in split manifest |
| Monotonic timestamps | ✅ 3150/3150 trajectories checked, 0 violations |
| No altitude ≤ 0 | ✅ min = 0.0199m |
| No invalid controls | ✅ 0 `invalid_control_values` terminations |
| No numerical failures | ✅ 0 `numerical_instability_nan_inf` terminations |
| Trajectory-level split integrity | ✅ 2205 train / 472 val / 473 test, 0 overlap, `verify_no_overlap` passed |
| Causal derivative re-derivation | ✅ 25 trajectories independently recomputed, 0 mismatches |
| Future-label re-derivation | ✅ 25 trajectories independently recomputed, 0 mismatches |
| Metadata/data row-count consistency | ✅ `sum(n_steps)` = 5,340,865 = raw row count |

Full audit: `outputs/dataset_audit_v3/audit_report_v3.md` / `.json` (reuses `aeroguard_dataset/audit.py`
unmodified). Plots: `outputs/dataset_audit_v3/plots/` (reuses `aeroguard_dataset/visualize.py`
unmodified).

## v3 vs v2 comparison

| Metric | v0.2 (near_boundary, n=250) | **v0.3 (gradual_approach_v3, n=2400)** |
|---|---|---|
| Crossing rate | 12.4% (31/250) | 13.2% (317/2400) |
| Gamma termination | 5.6% (14/250) | 27.2% (688/2400, non-crossers mostly) |
| Median precursor (dip-aware) | 0.54s | **4.38s** |
| ≥2s precursor coverage | ~4% | **66.0%** |
| ≥3s precursor coverage | ~0% | **59.3%** |
| Clean/monotonic crossing rate | not directly comparable (v2 had no such classification) | 99.1% |
| `future_stall_5s` positive rate | 7.0% | 8.2% |

Gamma termination is higher in v0.3's gradual regime than v0.2's near_boundary (27.2% vs 5.6%)
— this is the known, accepted, mechanistically-explained trade-off from the calibration stage
(capping combined pulse duration reduces but does not fully eliminate non-crossing runaway
trajectories; §7 of the final-gate report), not a new finding. It does not affect crossing
quality: every crossing-level metric improved dramatically over v0.2.

---

## Decision-gate questions

**A. Did the full dataset preserve the successful Candidate-D behavior?**
Yes. Crossing rate (13.2% vs. calibration's 12.0%), gamma termination (27.2% vs. 28.6%), median
precursor (4.38s vs. 4.50s), and clean-crossing rate (99.1% vs. 100%) all landed within normal
sampling variation of the calibration numbers. No parameter drifted or needed adjustment.

**B. Did the 1000+ trajectory run produce enough crossing examples?**
Yes, comfortably. Target was 192 (matching v0.2's total); `gradual_approach_v3` alone produced
317 crossings (165% of target), and the full dataset produced 470 total crossings (245% of
target, including stall-regime's 153).

**C. Are the multi-second precursors still present at scale?**
Yes, and the estimates are now far more reliable (194 usable crossings vs. calibration's 13).
66.0% of crossings have a genuine ≥2s precursor, 59.3% have ≥3s, 55.7% have ≥4s — all direction-
aligned, dip-aware, physically classified as gradual/monotonic in 99.1% of cases. This is the
first point in the whole precursor-diagnosis effort where multi-second precursor coverage is
both large in absolute count (194+ examples) and high in fraction (>50% at 3-4s).

**D. Did gamma/ground-contact failures remain controlled?**
Ground-contact: yes, negligible (19/3150, 0.6%, consistent with calibration). Gamma: at the
level already accepted at the decision gate (27.2% aggregate, driven by non-crossing
`gradual_approach_v3` trajectories, not crossings) — not newly controlled beyond what CASE A
already signed off on, but not worse either.

**E. Is there evidence of any new artifact or distribution problem?**
One minor, expected observation: 3/317 (0.9%) `gradual_approach_v3` crossings classify as
"runaway/extreme" — not seen in the 21-trajectory calibration sample, but statistically
unsurprising at 15x the sample size and small enough not to indicate a new failure mode. No
other artifact found: alpha/gamma/V ranges are physically unremarkable and consistent with
v0.1/v0.2's own ranges (e.g., v0.2 alpha range was −41.6° to 73.9°; v0.3 is −41.2° to 76.2° —
essentially the same). All integrity checks passed with no exceptions.

**F. Is v0.3 READY for the temporal ML experiment?**
**Yes.** The dataset delivers what the entire multi-stage diagnosis was aimed at: a large
(194+), reliable, physically-credible population of genuine multi-second stall precursors,
alongside unchanged `normal`/`stall` regimes for contrast, full trajectory-level train/val/test
splitting with zero overlap, and every integrity check passing. This report does not itself
run or recommend specific ML next steps beyond confirming readiness — per this stage's explicit
scope, no ML was run.

---

## Files produced this stage

```
data/raw/raw_telemetry_v3.parquet                    (5,340,865 rows)
data/processed/processed_dataset_v3.parquet           (5,340,865 rows)
data/metadata/trajectory_metadata_v3.csv               (3,150 rows)
data/metadata/generation_config_v3.json
data/metadata/feature_schema_v3.json
data/splits/split_manifest_v3.csv
outputs/dataset_audit_v3/audit_report_v3.md / .json
outputs/dataset_audit_v3/plots/                       (reused aeroguard_dataset/visualize.py)
outputs/dataset_audit_v3/v3_precursor_classification.csv
outputs/dataset_audit_v3/v03_generation_report.md      (this file)
aeroguard_dataset/dataset_builder_v3.py
scripts/generate_dataset_v3.py
scripts/audit_v3_precursor.py
tests/test_dataset_builder_v3.py                       (5 focused tests, passing)
```

Full test suite: **173/173 passing** (168 pre-existing + 5 new). v0.1/v0.2 data and `aeroguard/`
physics confirmed unmodified (MD5-verified). No ML training, no dashboards, no v3 parameter
tuning, no scaling beyond the justified 3,150-trajectory count.
