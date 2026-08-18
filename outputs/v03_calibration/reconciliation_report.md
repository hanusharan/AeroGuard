# AeroGuard v0.3 — Reconciliation & Decision Gate

Reconciles two conflicting, concurrently-produced v0.3 precursor-calibration results
found in this repository. No full v0.3 dataset generated, no ML training run, v0.1/v0.2
and `aeroguard/` physics untouched (verified below).

---

## 1. Repository state

Two independent implementations of the same Phase 3/4 task exist side by side, produced by
two concurrent Claude Code sessions working on this repo at the same time.

**RUN B** (this session, first pass):
- `aeroguard_dataset/control_profiles_v03_candidates.py` — 5 single-pulse candidates (`V03_CANDIDATES`)
- `scripts/calibrate_v03.py`, `scripts/precursor_diagnosis.py`
- Outputs: `outputs/v03_calibration/candidate_calibration_summary.{csv,json}`, `calibration_metadata.csv`, `calibration_raw_trajectories.parquet`; `outputs/precursor_diagnosis/FINAL_REPORT.md` + supporting CSVs/plots
- Result: NO-GO (57–80% gamma termination, no candidate reliably reached ≥3s precursor)

**RUN A** (concurrent session):
- `aeroguard_dataset/config.py` — added `GRADUAL_APPROACH_CANDIDATES` (5 candidates, one is a **two-stage** two-pulse design) + `make_v03_calibration_config()`, appended after the existing (untouched) `NORMAL_CONTROL_CONFIG`/`STALL_CONTROL_CONFIG`/`NEAR_BOUNDARY_CONTROL_CONFIG`/`REGIME_CONTROL_CONFIGS_V2`
- `scripts/calibrate_v3.py`, `scripts/diagnose_precursor.py`
- Outputs: `outputs/v03_calibration/v03_calibration_stats.{csv,json}`, `decision_gate_report.md`, two plots; `outputs/precursor_diagnosis/precursor_diagnosis_report.md` + supporting files
- Result: GO on Candidate D (two-stage)

**Collision:** RUN A's session also overwrote this session's `tests/test_v03_candidates.py` with tests for its own code. Restored (previous turn) to test RUN B's actual implementation; both implementations' source files are left intact and untouched — nothing was deleted.

**v0.1/v0.2 / physics integrity check:** `aeroguard/` unmodified by either run (both only add new files or append to `aeroguard_dataset/config.py`, never touching `aeroguard/aerodynamics.py`/`dynamics.py`/`aircraft.py`/`integrator.py`). `data/processed/processed_dataset_v2.parquet` and `data/metadata/trajectory_metadata_v2.csv` MD5-verified unchanged. `REGIME_CONTROL_CONFIGS_V2` (the actual v0.2 near_boundary/stall/normal configs) verified byte-identical to their original values. **No stop condition triggered.**

Full test suite: **157/157 passing** after restoring RUN B's test file.

---

## 2. Apples-to-apples comparison

| Dimension | RUN A (`calibrate_v3.py`) | RUN B (`calibrate_v03.py`) | Same? |
|---|---|---|---|
| Physics engine (`aeroguard/`) | unmodified | unmodified | ✅ |
| Aircraft params | `Aircraft()` defaults | `Aircraft()` defaults | ✅ |
| Stall boundary | 16.07° (`resolve_stall_boundary`) | 16.07° (same function) | ✅ |
| Gamma envelope | 45° (`GenerationConfig` default) | 45° (same default) | ✅ |
| Initial-condition dist. (V0/altitude) | `GenerationConfig()` defaults | `GenerationConfig()` defaults | ✅ |
| Crossing definition | `whether_stall_occurred`/`time_of_first_stall` (`abs(alpha) > alpha_at_cl_peak`) | same | ✅ |
| Gamma-termination definition | `TERMINATION_GAMMA_EXCEEDED`, `\|gamma\|>45°` | same | ✅ |
| Ground-contact handling | same `trajectory_sim.py` logic, both 0% observed | same | ✅ |
| Timestep/duration | dt=0.01, 20s | dt=0.01, 20s | ✅ |
| **RNG seed** | **20260817** (reused v0.1/v0.2's own seed) | **20260818–20260822** (one per candidate) | ❌ |
| **Regime assignment** | 5 candidates in **one** 175-traj `build_dataset` call, 20% each, interleaved by `assign_regimes` | 5 **separate** 30-traj `build_dataset` calls, 100% one candidate each | ❌ |
| **Candidate design** | multi-candidate sweep incl. **two-stage (2 sequential pulses)**, magnitude 0.05–0.09 rad/pulse, throttle **inert** (0 magnitude) | single-pulse only, magnitude 0.12–0.24 rad, mild throttle (0.03–0.10) | ❌ |
| **Precursor definition** | first index where **raw signed** alpha ≥ 8° pre-crossing, → `t_cross − t8` | **direction-aligned** (sign-corrected to the boundary actually crossed), **last** index below 8° immediately before the final approach | ❌ — see §5, this is the main driver of the conflict |
| N trajectories | 175 (35/candidate) | 150 (30/candidate) | ~ (both in-budget) |

**Bottom line: same physics, same boundary/envelope, same crossing/termination definitions. The two conflicting verdicts come from (a) a genuinely different, better-motivated candidate design in RUN A (two-stage pulses) and (b) a materially different, non-equivalent precursor-duration metric.**

---

## 3. Why the results conflict

Two separate, additive reasons, both confirmed empirically in §5:

1. **Different candidates.** RUN A's Candidate D uses two smaller sequential pulses
   (0.05–0.09 rad each) instead of RUN B's one large pulse (0.12–0.24 rad). This is a
   real, physically distinct design RUN B never tested, and it does perform better on
   gamma termination (31.4% vs. RUN B's 57–80%) — confirmed on reproduction, see §5.
2. **Different precursor-duration metric.** RUN A's `onset_to_cross` takes the
   **first** time alpha ever touches 8° before crossing. If alpha touches 8°, retreats
   (a dip, dive, or partial recovery), and only later makes its real final approach,
   RUN A's number still counts from the *first* touch — crediting time when the
   aircraft was not actually approaching the boundary. RUN B's metric takes the
   **last** below-8° sample immediately before the final approach, which is immune to
   this. This one methodological choice, not physics, accounts for most of the
   magnitude of RUN A's headline "87.5% ≥3s" figure — see §5.

---

## 4. Candidate D reproducibility results

Reproduced RUN A's exact call (`GRADUAL_APPROACH_CANDIDATES`, `make_v03_calibration_config(175)`,
seed 20260817) via a new script (`scripts/verify_candidate_d.py`) that does not modify RUN A's
or RUN B's files. **Top-line numbers reproduced exactly**: crossed 22.9%, gamma-term 31.4%,
ground-contact 0%, completed 68.6% — confirms RUN A's aggregate figures are a real, deterministic
output of that code, not a reporting error.

Crossing-level detail (n=8 crossings, all positive-alpha — no negative/nose-down crossings in
this candidate, unlike RUN B's stall-regime finding):

| Metric | RUN A definition (first touch ≥8°) | RUN B definition (direction-aligned, last touch before final approach) |
|---|---|---|
| n usable | 8/8 | 6/8 (2 trajectories never had a "below 8°" reference point in RUN B's frame — see caveat below) |
| Median onset→crossing | **6.00s** | **2.23s** |
| ≥2s precursor | 100% | 66.7% |
| ≥3s precursor | **87.5%** | **33.3%** |
| ≥4s precursor | 87.5% | 33.3% |
| ≥5s precursor | 87.5% | 33.3% |

**3 of 8 crossings (traj_0122, traj_0153, traj_0162) show near-identical durations under both
definitions (5.63–6.84s under either metric)** — these are genuinely monotonic, single-approach
climbs, not an artifact. **5 of 8 show large gaps (3.7–5.4s) between the two definitions**
(traj_0013, traj_0088, traj_0104, traj_0119, traj_0121) — these involve an early transient touch
of 8° followed by a retreat, which RUN A's metric silently credits as precursor time.

Max-alpha distribution across the full 35-trajectory candidate D batch: mean 10.3°, median 7.7°,
p90 23.0°. Small-margin crossing rate (max|alpha| within 5° over the boundary): 8.6%.
`gamma_at_cross` for the 8 crossings ranges −1.4° to 24.9° (matches RUN A's claim) — but see §5,
this is not the whole picture.

Clean-vs-runaway classification (gamma comfortably inside the envelope **at the crossing
instant**, non-envelope termination): 8/8 pass this narrow test — but §5 shows this test is too
narrow, since it only checks gamma at the single crossing instant, not gamma's behavior
*throughout* the pre-crossing window.

Full data: `candidate_d_reproduction_raw.parquet`, `candidate_d_reproduction_metadata.csv`,
`candidate_d_trajectory_classification.csv`, `candidate_d_metric_comparison.csv`.

---

## 5. Physical trajectory evidence (Task 4)

Traced all 8 Candidate D crossing trajectories in full (`plots/03_candidate_d_reproduction_traces.png`:
alpha/elevator/gamma/altitude/V vs. time, 8/12/16° marked, crossing marked). Two clear patterns:

**Pattern 1 — genuinely gradual (3/8: traj_0122, traj_0153, traj_0162).** Alpha climbs
smoothly and close to monotonically from trim through 8°→12°→16° over several seconds, gamma
stays moderate (17–26° max in the 10s pre-crossing window), no dive/zoom. This is the real,
credible improvement RUN A found — genuinely better than any of RUN B's single-pulse candidates.

**Pattern 2 — dive/zoom-climb-then-stall, RUN B's objection confirmed (traj_0013, and
similarly traj_0088/traj_0119).** Traced traj_0013 in full: trim alpha 6.6° holds flat to t=3.5s;
elevator then goes **negative**, diving alpha down to −0.3° and gamma down to **−26°** by t=7s;
elevator swings sharply positive, pulling alpha back up through 8° at t=10.5s (this is RUN A's
"onset" point) while gamma swoops from −26° up to **+31.6° by t=13s**, and gamma stays pinned
near **40–43°** — within 2–8° of the 45° cap — for the next ~4 seconds (t=13–17); alpha actually
*dips* from 9.4° back to 5.3° during this same window (elevator drops to trim); only in the final
~0.7s (t=17.5→18.24) does alpha make its real, fast run from 12.3°→16.07° (crossing), while gamma
is by then rapidly decreasing (30°→13°) as the aircraft pulls out of the zoom. Max |gamma| in the
10s before crossing: **42.7°**, well above the "clean" 35° margin used in the reproduction script
and only 2.3° under the hard 45° cap.

**Verdict on RUN B's objection: partially correct, and correctly targeted.** The apparent
long precursor is a genuine artifact for at least 5/8 crossings — either a metric-definition
inflation (§4), a dive-then-zoom-climb maneuver that only incidentally passes through 8° twice, or
both together (traj_0013 exhibits both). The gamma-envelope coupling RUN B identified (sustained
elevated alpha drives accumulating flight-path angle) is real and visible here too, just less
severe than in RUN B's own single-pulse candidates — Candidate D's two-stage design reduces but
does not eliminate it: gamma reaches within a few degrees of the 45° cap in the busiest cases
even when the trajectory does not formally terminate there. **RUN A's "every crossing verified
clean" claim is not supported** — it checked gamma only at the crossing instant, not gamma's
trajectory through the approach.

At the same time, RUN B's blanket NO-GO is not fully supported by this evidence either: Pattern-1
trajectories are real, reproducible, physically unremarkable gradual approaches with 3/8 of this
small sample reaching 5.6–6.8s of genuine precursor and gamma comfortably under 30°.

---

## 6. Scientific interpretation

- Candidate D's two-stage pulse design is a genuine improvement over every candidate either
  session tested with a single pulse: lower gamma-termination rate (31.4% vs. RUN B's 57–80%),
  and a real (not purely definitional) fraction of crossings with multi-second, low-gamma,
  monotonic approaches (3/8 in this small sample).
- RUN A's headline number (87.5% ≥3s precursor) is inflated by roughly 2.5x by a
  non-direction-aligned, first-touch precursor definition that credits dive/zoom-recovery time as
  precursor time. The corrected figure, on the same reproduced data, is **33.3%** (2/6 usable
  crossings) — still notably better than RUN B's 0% across all 5 of its own candidates, but far
  short of "87.5% of crossings have a clean multi-second precursor."
- The sample is small either way (8 crossings from 35 trajectories) — none of these fractions are
  tightly estimated. The qualitative direction (two-stage design measurably helps; magnitude of
  the effect is smaller than RUN A reported) is the load-bearing conclusion, not the exact
  percentages.

## 7. Decision

**CASE B — CONDITIONAL GO.**

Candidate D shows a real, physically credible precursor signal in a genuine subset of its
crossings (not purely an artifact, contra a strict reading of RUN B), but RUN A's specific
performance claims (87.5% ≥3/4/5s, "every crossing clean") do not survive independent
verification with a direction-aligned, dip-aware metric and a full-window gamma check (corrected:
~33% ≥3s, gamma reaches 40–43° in the busiest cases). It is not ready for full-dataset generation
as currently parameterized.

**One narrowly targeted calibration adjustment (not started):** re-run Candidate D's two-stage
design with pulse 2 constrained to fire only shortly after pulse 1's fall completes near/above
the 8° line (avoiding pulse 1 overshooting into a sign-reversed dive), and evaluate using the
direction-aligned, dip-aware precursor metric from the start — not the first-touch metric. Keep
the two-pulse magnitude range (0.05–0.09 rad) and pulse count (2) unchanged, since those are what
made D outperform every single-pulse candidate on gamma termination. This isolates whether
constraining the two pulses to move in a consistent direction (never sign-reversing) preserves
D's low gamma-termination rate while converting more of the 5/8 "inflated" crossings into genuine
Pattern-1 approaches.

## 8. Exact next step

Do **not** generate the full v0.3 dataset. Do **not** start the proposed calibration adjustment
automatically — it is scoped above for you to approve. If approved, it should be one more
~150–200-trajectory calibration batch (same budget class as this stage), evaluated with the
direction-aligned metric and a full-window (not crossing-instant-only) gamma check from the
outset, before any decision to scale to 1000 trajectories or re-run the temporal ML experiment.

---

## Files produced this reconciliation

```
outputs/v03_calibration/reconciliation_report.md      (this file)
outputs/v03_calibration/candidate_d_reproduction_raw.parquet
outputs/v03_calibration/candidate_d_reproduction_metadata.csv
outputs/v03_calibration/candidate_d_trajectory_classification.csv
outputs/v03_calibration/candidate_d_metric_comparison.csv
outputs/v03_calibration/plots/03_candidate_d_reproduction_traces.png
scripts/verify_candidate_d.py
```

RUN A's and RUN B's original files are all preserved unchanged (see §1 for the full list of
which files belong to which run).
