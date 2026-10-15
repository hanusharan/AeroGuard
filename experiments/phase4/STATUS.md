# Phase 4 status (2026-10-15)

Protocol: `PROTOCOL.md` (committed before any data). This file records exactly what is built, what was run, and what is still open. Work stopped early because the session's compute budget ran low.

| Item | State | Notes |
|---|---|---|
| 43 Vary aircraft parameters | **Built.** | `phase4/configs.py` (15 parameters, 23 fixed configurations), `phase4/sim.py` (density-aware trim/sim, tested bit-identical to the original at ρ = 1.225; pilot-equivalent control scaling), `PARAMETER_RANGES.md`. All 23 configurations trim; no V0 cap was needed. Generation script `scripts/phase4_generate.py`; D0/D1 generation was started in scratch storage (not in Git). |
| 44 Hold out configurations | **Code built, not run.** | Partition P0/P1/P2 in `configs.partition`; models in `phase4/models.py`; metrics with trajectory bootstrap in `phase4/metrics.py` (weighted PR-AUC tested equal to scikit-learn). The experiment runner that ties these together is not written. |
| 45 Unfamiliar configurations | **Code built, not run.** | OOD set O01–O06 and `d_OOD`. Note before any result: with 12 Sobol points in 15 dimensions, the IDH configurations already have 0–3 parameters outside the TRAIN per-parameter range. |
| 46 Abstention | **Code built, not run.** | `phase4/uncertainty.py`: ambiguity, ensemble spread, kNN novelty, abstention report, risk–coverage. |
| 47 Uncertainty under shift | **Code built, not run.** | ECE/Brier, split conformal with coverage report. |
| 48 JSBSim | **Done (feasibility).** | `phase4/jsbsim_sim.py`. `c172p`: F1–F4 pass (lift-table peak α = 0.28 rad, CLmax 1.47; trims 1.3–2.0 V_stall; full nose-up ramp reaches α ≈ 0.73 rad). `c172x`, `c182`: F3 failed (α not driven past the peak by the probe ramp); `pa28`, `c310`: F2 failed (trim did not converge with this harness). Not investigated further. **c172p is suitable.** |
| 49 Independent-simulator protocol | **Protocol defined; pilot calibration showed a problem.** | Gain pilot (seed 20261099, stall profiles only, 60 trajectories per gain 1.5–4.0): 31/60 trims failed and the crossing rate was only 3–8%, far below the v0.3 target 61%. Cause not yet diagnosed (likely the V0 range above the c172p's trimmable speed at altitude, and the random-sign pulses: half push nose-down). Must be fixed and recorded in `DEVIATIONS.md` before the cross-simulator run. No model was evaluated on JSBSim data. |
| 50 Published evidence | **Partly done.** | Primary sources (NACA TR-824, POH) could not be opened from the environment (network policy). Reference values with provenance levels are in `published_reference.json`; only a secondary C172R stall speed and JSBSim table values are available. Comparison numbers below are computed from those, labelled accordingly. |
| 51 Simulator assumptions | **Done.** | `SIMULATOR_ASSUMPTIONS.md` (A1–A14). |
| 52 Operating conditions | **Not run.** | Slices fixed in the protocol. |
| 53 Robustness | **Not run.** | Partitions and seeds fixed in the protocol; D1 data generation started. |

## Item 50 comparison (secondary/U-level references only — not called agreement)

| Quantity | AeroGuard v0.3 | Reference | Level |
|---|---|---|---|
| CLmax | 1.736 at α = 16.07° | JSBSim c172p `CLwbh` table: 1.47 at 16.0° | J (model, not experiment) |
| Lift slope | 5.5 /rad | c172p table ≈ 4.8 /rad (α 0–0.21 rad) | J |
| CL at α = 0 | 0.20 | c172p 0.25; NACA 2412 section ≈ 0.25 | J; S |
| 1 g stall speed at 1,111 kg, sea level | 24.7 m/s (48 kt) from CLmax 1.736 | C172R data sheet 51 KCAS flaps up, power off (≈ 26.2 m/s) → implied CLmax ≈ 1.60 | S |

AeroGuard's CLmax is about 8% above the value implied by the secondary C172R stall speed and 18% above the JSBSim c172p table; its lift slope is about 15% above the c172p table. Both differences are at or beyond the protocol's agreement bands, but neither reference is a checked primary experimental source.

## Next steps to finish Phase 4

1. Write `scripts/run_phase4.py` (load D0 panels → fit M_D/M_D_noSM/M_A × 5 seeds on P0 TRAIN with stride 5 → thresholds on TRAIN val → score SEEN/IDH/OOD/C00 → `metrics.evaluate`, `uncertainty` reports → per-slice tables), then robustness loop (P0–P2 × D0/D1).
2. Diagnose the JSBSim calibration (trim range, sign of stall pulses), record a deviation, generate 300 c172p trajectories, run section 11.
3. Append RL-008 results.
