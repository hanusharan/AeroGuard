# AeroGuard Phase 4 — Generalisation and more realistic simulation (Items 43–53)

| | |
|---|---|
| **Status** | Pre-specified. Written and committed **before** any Phase 4 dataset was generated, any Phase 4 model was trained, or any Phase 4 number was computed. |
| **Scope** | Items 43–53 of the research roadmap: varied aircraft parameters, held-out and unfamiliar configurations, abstention, uncertainty under shift, a JSBSim feasibility study and independent-simulator protocol, comparison with published evidence, a simulator-assumption audit, per-regime evaluation, and robustness across configurations and seeds. |
| **Evidence level** | Simulation only. Every Phase 4 number describes simulated aircraft (the AeroGuard 2D model with varied parameters, or a JSBSim model). None describes a real aircraft, an operational false-alarm rate or certified performance. Same author and code base as Phases 1–3, so nothing here is independent replication. |
| **What was looked at before writing** | The AeroGuard source code; the existing v0.3 reports; timing of the existing trajectory generator (≈0.17 s per trajectory); the list of aircraft shipped with the `jsbsim` 1.3.2 Python wheel and the `CLwbh` lift table of its `c172p` model (to decide whether item 48 is worth attempting); two web searches for published reference data (item 50). No Phase 4 trajectory, label or model output was seen. |

Deviations from this document after the commit are recorded in `experiments/phase4/DEVIATIONS.md` with the reason and whether any result had been seen when the deviation was made. This file is not edited after the commit.

---

## 0. Frozen inputs that are reused unchanged

- Physics: `aeroguard.dynamics.equations_of_motion`, `aeroguard.aerodynamics`, `aeroguard.integrator.rk4_step` (not modified). `equations_of_motion` already takes `rho` as an argument; Phase 4 passes it. The trim solver in `scripts/simulate.py` hard-codes sea-level density, so Phase 4 uses a copy that takes `rho` and is tested to agree exactly with the original at `rho = 1.225`.
- Event and label definitions: `aeroguard_dataset.events.StallBoundary` (|α| beyond the numerically located CL(α) peak of **the aircraft being simulated**), `aeroguard_dataset.labeling.compute_future_stall_label` (horizon 5 s), `aeroguard_dataset.features.compute_features_for_trajectory`.
- Control profiles: the v0.3 `normal` and `stall` configurations and the locked Candidate D v3 `gradual_approach_v3` builder. Their elevator magnitudes are rescaled per configuration (section 1.4); timing is unchanged.
- Temporal features: `ml.temporal_features.build_temporal_panel` with the 1 s window; `ml.temporal_config.model_d_features(1.0)` (23 features) and `INSTANTANEOUS_STATE_FEATURES` (8 features).
- RF hyperparameters: `ml.temporal_config_v03.FROZEN_RF_PARAMS` (`n_estimators=200, max_depth=12, min_samples_leaf=5, class_weight=balanced_subsample`).
- Threshold selection: `ml.calibration.select_threshold_train_then_val` (top-10 train F1, then best validation F1; strict `score > threshold`).
- Event metrics: `ml.events.compute_event_level_results` / `aggregate_event_results` (5 s capped lead time). False-warning episodes per simulated hour and coverage at lead times: the Items 37–39 definitions (`experiments/items33_42/items37_39/src/items37_39.py`).
- Frozen model: `outputs/ml_v03/models/primary_model_D_1s.joblib` (SHA-256 `707d4c61…03f3`), used only for scoring.

## 1. Item 43 — Varied aircraft parameters

### 1.1 Parameters and documented ranges

Each varied parameter has a full range R. The ranges describe a *generic four-seat, single-piston-engine light aircraft class*; they are chosen to be defensible, not to match a specific type. Sources are listed in `experiments/phase4/PARAMETER_RANGES.md`; where a parameter is a surrogate gain with no physical counterpart, the range is an uncertainty band around the v0.3 value and is labelled as such.

| Parameter | v0.3 value | Range R | Basis (detail in PARAMETER_RANGES.md) |
|---|---|---|---|
| `mass` [kg] | 1200 | 900 – 1400 | light-loaded to heavy four-seat single (C172R max 1111 kg, C182 class ≈1400 kg) |
| `wing_area` [m²] | 16.2 | 14.5 – 17.5 | PA-28 ≈14.9 m², C172/C182 ≈16.2 m² (JSBSim model files) |
| `CL_alpha` [1/rad] | 5.5 | 4.5 – 5.8 | lifting-line estimate for aspect ratio 6–9 with a section slope ≈6/rad; JSBSim c172p table ≈4.8 |
| `alpha_stall` [deg] | 16.0 | 14 – 18 | typical clean-wing stall AoA for NACA 4-digit/23xxx-section light aircraft |
| `CL0` | 0.20 | 0.15 – 0.30 | cambered section plus wing incidence |
| `CD0` | 0.028 | 0.025 – 0.036 | fixed-gear light singles |
| `k` | 0.045 | 0.040 – 0.060 | 1/(π e AR) for e 0.7–0.9, AR 6–9 |
| `thrust_max` [N] | 2600 | 2200 – 3200 | static/low-speed thrust of 150–230 hp fixed-pitch/constant-speed propellers (order of magnitude) |
| `Iyy` [kg m²] | 1285 | 1000 – 1900 | JSBSim c172p 1346 slug ft² ≈ 1825 kg m², pa28 ≈ 1693 kg m² |
| `elevator_effectiveness` | 3.2e4 | ×0.75 – ×1.25 | surrogate gain: uncertainty band only |
| `pitch_damping` | 6.0e3 | ×0.75 – ×1.25 | surrogate gain: uncertainty band only |
| `alpha_stiffness` | 1.0e4 | ×0.75 – ×1.25 | surrogate gain: uncertainty band only |
| `stall_transition_rate` | 25 | 15 – 35 | stall-break sharpness: uncertainty band |
| `post_stall_decay_rate` [1/rad] | 3.0 | 2.0 – 4.5 | post-stall lift loss: uncertainty band |
| `rho` [kg/m³] | 1.225 | 0.905 – 1.225 | ISA sea level to 10,000 ft density altitude (constant within a configuration) |

Each parameter is mapped to normalised coordinate u ∈ [0, 1] linearly over R. The **core box** is u ∈ [0.2, 0.8] for every parameter; the **outer band** is the rest of R.

### 1.2 Configuration set (fixed before data generation)

| Set | n | Construction |
|---|---|---|
| `C00` | 1 | the v0.3 aircraft at ρ = 1.225 (reference; never trained on) |
| `TRAIN` (T01–T12) | 12 | scrambled Sobol sequence (`scipy.stats.qmc.Sobol`, d = 15, scramble seed 20261020), first 12 points (after skipping none), mapped into the core box |
| `IDH` (H01–H04) — item 44 | 4 | a second Sobol sequence (seed 20261021), first 4 points, in the core box |
| `OOD` (O01–O06) — item 45 | 6 | a third Sobol sequence (seed 20261022), first 6 points in the core box, then the named parameter groups below are moved into the outer band |

OOD groups (u values set exactly as listed; other parameters keep their core-box value):

| Config | Story | Parameters moved to the outer band |
|---|---|---|
| O01 | heavy, high density altitude, small wing | `mass` u=0.98, `rho` u=0.02, `wing_area` u=0.02 |
| O02 | light, large wing, sea level | `mass` u=0.02, `wing_area` u=0.98, `rho` u=0.98 |
| O03 | early, sharp stall | `alpha_stall` u=0.02, `stall_transition_rate` u=0.98, `post_stall_decay_rate` u=0.98 |
| O04 | late, soft stall | `alpha_stall` u=0.98, `stall_transition_rate` u=0.02, `post_stall_decay_rate` u=0.02 |
| O05 | sluggish pitch | `Iyy` u=0.98, `pitch_damping` u=0.02, `elevator_effectiveness` u=0.02 |
| O06 | everything unfamiliar | every parameter: u = 0.1·s if the core-box u < 0.5, else 0.9 + 0.1·s, with s the core-box u rescaled to [0, 1] |

Unfamiliarity is quantified per configuration as the normalised distance `d_OOD` = minimum Euclidean distance in u-space to any TRAIN configuration, and the number of parameters outside the per-parameter [min, max] of the TRAIN configurations.

### 1.3 Initial conditions

V0 is sampled uniformly in [1.148, 2.869] × V_stall,cfg, the same multiples of stall speed as v0.3 (30 and 75 m/s over 26.14 m/s), where V_stall,cfg uses the configuration's own CLmax, mass, wing area and ρ. If trim throttle would exceed 1 at the upper V0, the upper limit is lowered to the fastest speed with trim throttle ≤ 1 (bisection, recorded). Altitude h0 ∈ [500, 2000] m as v0.3; altitude does not feed back into ρ (assumption A3 in section 9).

### 1.4 Control-input scaling (pilot-equivalent inputs)

The v0.3 elevator magnitudes were calibrated for one aircraft. The static AoA response per radian of elevator is `elevator_effectiveness / alpha_stiffness`, so a fixed elevator deflection would push a different aircraft to a different fraction of its stall AoA. Every elevator pulse magnitude is therefore multiplied by

  s_cfg = [(alpha_stiffness/elevator_effectiveness)_cfg / (alpha_stiffness/elevator_effectiveness)_v0.3] × [α_peak,cfg / α_peak,v0.3].

Pulse timing and throttle pulses are unchanged. This is a modelling choice (a pilot flying a different aircraft scales inputs to that aircraft); it is recorded as assumption A12.

### 1.5 Per-configuration dataset

300 trajectories per configuration: 80 `normal`, 60 `stall`, 160 `gradual_approach_v3`, shuffled, dt = 0.01 s, duration 20 s, the v0.3 validity envelope resolved for the configuration (V floor 0.5 V_stall,cfg, |γ| ≤ 45°, h > 0). Within a configuration, trajectories are split 70/15/15 into train/val/test by trajectory (seeded permutation). Data seeds: **D0 = 20261015** (primary) and **D1 = 20261016** (item 53 only). Trajectory RNG streams are derived as `SeedSequence([data_seed, config_index])`.

**Evaluability gate (pre-specified, not a replacement rule):** a configuration is *evaluable* for event metrics if its evaluation trajectories contain at least 15 stall events in usable rows. Non-evaluable configurations are reported with their counts and excluded from event-level aggregates only. No configuration is replaced or redrawn.

## 2. Models (all fitted only on TRAIN configurations' train split; thresholds on their val split)

| Name | Features / rule | Role |
|---|---|---|
| `M_D` | Model D, 1 s (23 features incl. `stall_margin`) | **primary** |
| `M_D_noSM` | Model D without `stall_margin` (22 features; no knowledge of the configuration's stall AoA) | secondary: is the stall-AoA input what carries transfer? |
| `M_A` | the 8 instantaneous-state features | instantaneous baseline |
| `R_AoA` | existing `AoAThresholdRule` on signed α | rule baseline |
| `R_SM` | existing `StallMarginThresholdRule` | rule baseline (no longer equivalent to `R_AoA` once α_peak varies) |
| `F_v03` | frozen v0.3 primary model and its stored threshold, no refitting | zero-shot reference |

Training rows: usable rows (target available and full 1 s window) taken every 5th row (0.05 s stride), to bound memory and fit time. Validation rows: same stride. Evaluation rows: every usable row (0.01 s) in the primary run (P0, D0, all five seeds); 0.05 s stride in the other item-53 runs. Model seeds: 20260817, 20261101, 20261102, 20261103, 20261104; the primary reported model is seed 20260817, with across-seed summaries alongside.

## 3. Evaluation groups and metrics

Groups: `SEEN` (TRAIN configurations, test split), `IDH` (all trajectories of H01–H04), `OOD` (all trajectories of O01–O06), `C00` (all trajectories). Metrics per group and per configuration: row PR-AUC, ROC-AUC, Brier score, ECE (10 equal-width bins); event recall, median and mean credited lead time, coverage at ≥2 s and ≥4 s lead (Items 37–39 primary definition), false-warning episodes per simulated hour (Items 37–39 primary definition), episode precision. Uncertainty: trajectory bootstrap within group, B = 1000, seed 20261015, percentile 95% intervals. Configuration-level summaries (median, min, max across configurations) are reported next to pooled values because the configuration — not the trajectory — is the unit of a generalisation claim, and with 4 and 6 holdout configurations those summaries are weak; this is stated wherever they are used.

## 4. Item 44 — Held-out configurations (interpolation)

Pre-specified comparison: `M_D` on `IDH` vs `SEEN`. Δ = IDH − SEEN for PR-AUC and event recall, with a paired-free (independent groups) bootstrap interval of Δ.

- **Generalises within the training envelope** if Δ PR-AUC ≥ −0.05 and Δ event recall ≥ −0.10 (point estimates) and no individual IDH configuration has PR-AUC more than 0.10 below SEEN.
- Otherwise **degrades within the envelope**, with the configurations responsible named.

## 5. Item 45 — Unfamiliar configurations (extrapolation)

`M_D`, `M_D_noSM`, `M_A`, rules and `F_v03` on each OOD configuration and pooled. Reported against `d_OOD`. Pre-specified expectation (recorded, not a pass criterion): O03 and O04 (stall-AoA shifts) hurt `M_D_noSM` and `R_AoA` more than `M_D` and `R_SM`, because only the latter receive the configuration's stall AoA. The relation between per-configuration PR-AUC drop and `d_OOD` is reported as a Spearman correlation over all 23 configurations (descriptive).

## 6. Item 46 — Abstention

Uncertainty scores, per evaluated row:

- `U_amb`: ambiguity of `M_D`, p(1 − p) with p the predicted probability.
- `U_ens`: standard deviation of the five seed models' probabilities.
- `U_nov`: input novelty, mean Euclidean distance to the 10 nearest neighbours among 20,000 TRAIN-train rows (fixed sample, seed 20261015) in the `M_D` feature space standardised with TRAIN-train means and standard deviations.

Abstention thresholds τ are set on TRAIN-configuration **validation** rows so that 5% of validation rows abstain (95% coverage). On every group, report: abstention rate; error rate (at the model threshold) on all rows and on retained rows; AUROC of the score for discriminating erroneous from correct rows; risk–coverage curve and AURC; event-level: fraction of missed events with any abstention in the 5 s before the crossing, and fraction of warned events whose warning onset was abstained.

**Abstention is useful** for a score if, in every group, retained-row error < all-row error, **and** abstention rate on OOD > abstention rate on SEEN. Both parts are reported separately.

## 7. Item 47 — Uncertainty under distribution shift

Per group: ECE and Brier score of `M_D` (and `F_v03`); AUROC of each U score for errors; split-conformal prediction sets for the binary label (nonconformity 1 − p̂(y), calibrated on TRAIN-configuration validation rows, target 90% marginal coverage); empirical marginal and positive-class coverage and average set size per group. **Uncertainty remains informative under shift** for a score if its error-AUROC on IDH and OOD is ≥ 0.6 and no more than 0.1 below SEEN. Conformal coverage on OOD below 0.85 is reported as a coverage failure under shift.

## 8. Item 52 — Distinct operating conditions (predefined regimes)

Every metric of section 3 for `M_D` (and `M_A`, `R_AoA` for comparison) on these predefined slices of the evaluation groups pooled (SEEN ∪ IDH ∪ OOD ∪ C00), and within OOD:

- configuration set and individual configuration;
- generation regime: `normal`, `stall`, `gradual_approach_v3`;
- V0/V_stall,cfg: [1.148, 1.6), [1.6, 2.2), [2.2, 2.869];
- density ρ: [0.905, 1.012), [1.012, 1.118), [1.118, 1.225];
- wing loading W/S (N/m²): tertiles of the 23 configurations' W/S computed from the configuration table (no trajectory data);
- event entry rate (event-level metrics only): dα/dt at the crossing < 2°/s, 2–5°/s, ≥ 5°/s.

Cells with fewer than 10 events are reported but marked *insufficient* and not interpreted. Rows are not independent; intervals are trajectory bootstrap.

## 9. Item 51 — Simulator assumption audit

`experiments/phase4/SIMULATOR_ASSUMPTIONS.md` lists, for the AeroGuard simulator and for the JSBSim model used: what is modelled, what is simplified, what is absent, where in code, and the expected direction of effect on the stall-warning results. Numbered A1…An; A3 (altitude does not change ρ) and A12 (control scaling) are referenced above.

## 10. Item 48 — JSBSim feasibility

Candidate models: `c172p` (primary), `c172x`, `pa28`, `c182`, `c310` from the `jsbsim` 1.3.2 wheel. Feasibility checks, each pass/fail:

- **F1** lift data define a stall: a tabulated or functional CL(α) with a maximum strictly inside its α range (flaps 0, no hysteresis), giving α_peak.
- **F2** 1 g wings-level trim converges over a speed range of at least 1.3–2.0 V_stall.
- **F3** open-loop elevator inputs drive α past α_peak, with lateral motion held near wings-level by a minimal lateral hold (proportional aileron on bank angle and rudder on sideslip; it never touches the elevator or throttle), without numerical failure.
- **F4** the AeroGuard state variables can be read with known units and sign conventions.

A model is **suitable** if F1–F4 pass. If `c172p` is not suitable, the first suitable candidate in the order listed is used; if none is, items 49's execution is reported as blocked, and only the protocol is delivered.

## 11. Item 49 — Independent-simulator protocol

- **Where models are trained:** AeroGuard Phase 4 TRAIN configurations only (D0). No JSBSim row is used to fit, threshold or select any cross-simulator model.
- **Cross-simulator models:** actuator semantics differ (JSBSim's normalised elevator command and its own moment derivatives versus the AeroGuard surrogate), so the cross-simulator models drop the actuator features `elevator`, `throttle` and `elevator_change_1s`: `X_D` (Model D minus those three, 20 features) and `X_D_noSM` (also without `stall_margin`). They are fitted and thresholded exactly as in section 2. `R_AoA` and `R_SM` keep their AeroGuard-fitted thresholds.
- **`stall_margin` in JSBSim** uses the JSBSim model's own α_peak from F1 (a known design characteristic of the aircraft, not a learned quantity).
- **JSBSim data:** 300 trajectories, 80 `normal`, 60 `stall`, 160 `gradual` with elevator-command profiles that reuse the AeroGuard pulse samplers, magnitudes mapped to normalised elevator command by a single gain chosen from pilot runs (separate seed 20261099) so that the `stall` profile crosses α_peak in roughly the v0.3 proportion; the pilot runs inspect only α and crossing rates, never a model output. Throttle at trim. dt = 0.01 s, 20 s, same validity envelope plus |bank| ≤ 30°. Data seed 20261017. Split 70/15/15 by trajectory.
- **Native reference (held out data only):** the same model classes fitted on the JSBSim train split and thresholded on the JSBSim val split. It shows what is achievable in that simulator; it is not a competitor.
- **Compared outputs:** on the JSBSim test split only — row PR-AUC, ROC-AUC, ECE, event recall, median lead time, coverage ≥2 s/≥4 s, false-warning episodes per simulated hour, abstention rate under `U_nov` (τ from section 6). The same metrics of `X_D` on AeroGuard IDH are shown next to them.
- **Interpretation rule:** a cross-simulator result says only that the warning learned in one simplified simulator does or does not carry over to a second, more detailed simulator model. JSBSim's c172 aerodynamics are themselves an approximation; agreement is not validation against a real aircraft.

## 12. Item 50 — Comparison with published evidence

Quantities and range (fixed): (Q1) lift-curve slope and CL(α) over α ∈ [0°, 14°]; (Q2) CLmax and α at CLmax; (Q3) 1 g flaps-up power-off stall speed at a stated weight; (Q4) drag-polar parameters CD0 and k. AeroGuard v0.3 values are compared with each reference value in `experiments/phase4/published_reference.json`, which records for every value its source, the exact quantity, conditions (Reynolds number, weight, flap setting), and a provenance level: **P** primary document checked, **S** secondary source, **U** unverified. Section data are converted to finite wing with the lifting-line slope correction a = a0 / (1 + a0/(π e AR)) for stated e and AR. Agreement bands, fixed now: slope ±15%, CLmax ±10%, α at CLmax ±2°, stall speed ±10%, CD0 ±25%, k ±25%. Comparisons with a U-level reference are shown but not called agreement or disagreement.

## 13. Item 53 — Robustness of conclusions

Runs: partitions P0 (section 1.2), P1, P2 — for P1/P2 the 16 core-box configurations (TRAIN ∪ IDH) are re-partitioned 12/4 by a seeded permutation (seeds 20261031, 20261032); OOD and C00 unchanged — crossed with data seeds D0, D1. Model seeds: five for (P0, D0), three (20260817, 20261101, 20261102) for the other five combinations.

Claims tested (each on IDH and on OOD):

- **K1** `M_D` PR-AUC > `M_A` PR-AUC.
- **K2** `M_D` median lead time > `M_A` median lead time.
- **K3** `M_D` event recall ≥ `R_AoA` event recall.
- **K4** `M_D` PR-AUC ≥ `M_D_noSM` PR-AUC (OOD only).

An advantage **persists** if its sign holds in at least 90% of the (partition × data seed × model seed) runs **and** the paired trajectory-bootstrap 95% interval of the difference excludes zero in the primary run (P0, D0, seed 20260817). It is **fragile** if the sign holds in 50–90% of runs, and **not supported** otherwise.

## 14. Outputs

Code: `phase4/` (package) and `scripts/run_phase4.py`, `scripts/run_phase4_jsbsim.py`. Tests: `tests/test_phase4_*.py` (synthetic, no research data). Results: `outputs/phase4/run_<UTC>/` (small JSON/CSV/Markdown and figures; no datasets). Large data live in a gitignored directory. A `REPORT.md` in the run directory states every pre-specified outcome above, including null and negative results. A `RESEARCH_LOG.md` entry (RL-008, planned block written before the run) records hypothesis, run and outcome.
