# Phase 4 deviations from PROTOCOL.md

Each entry: what changed, why, and what had been seen when the change was made. No Phase 4 model had been trained or scored on any data when entries P4-D1 to P4-D4 were written; only JSBSim pilot runs (seed 20261099, crossing rates and termination reasons, no model outputs) and the AeroGuard Phase 4 datasets' generation logs (row counts) had been seen.

### P4-D1 — JSBSim top start speed capped at every altitude (2026-10-15)

- **Protocol:** V0 upper limit lowered to the fastest trimmable speed (section 1.3, applied to JSBSim in section 11).
- **Change:** the cap is the minimum over the altitude range (500 m and 2000 m), not the value at 2000 m only. At the same true airspeed the c172p needs more thrust at low altitude, so the 2000 m cap (69.3 m/s) left starts at 500 m that could not trim (31 of 60 pilot trajectories failed). With the fix: 68.7 m/s.
- **Kind:** implementation bug fix that makes the code do what the protocol says.

### P4-D2 — JSBSim elevator mapping derived from the aircraft's pitching-moment derivatives (2026-10-15)

- **Protocol (section 11):** one gain from AeroGuard elevator magnitude to the normalised command, "chosen from pilot runs so that the stall profile crosses α_peak in roughly the v0.3 proportion" (61%).
- **What the pilots showed:** with a single linear gain (1.5–4.0) the stall-profile crossing rate stayed at 3–12%. The cause is physical: AeroGuard's pitch surrogate gives a static angle-of-attack change of 3.2 rad per rad of elevator, the c172p about 0.62 rad per rad (|Cmδe/Cmα| = 1.122/1.8), so the AeroGuard inputs were far too weak once converted. An intermediate attempt that scaled the command by (1.6 V_stall/V0)² was discarded unrun on the cross-simulator data: static angle-of-attack response does not depend on dynamic pressure in either model, so that scaling had no physical basis.
- **Change:** the AeroGuard elevator increment is converted to the c172p deflection that gives the **same static angle-of-attack change** (×3.2/0.623), then to the normalised command with the c172p's own travel (−28° nose-up at command −1, +23° nose-down at +1), clipped to [−1, 1]. No free parameter is tuned to a crossing rate. Propwash on the tail (`qbar-induced-psf`), Cmq and lift-moment coupling are ignored in the conversion.
- **Consequence, stated before any model is scored:** the pilot crossing rates are stall 35%, gradual 22% and normal 3% (v0.3: 61%, 13%, 0%). The AeroGuard stall-regime magnitudes saturate the c172p elevator at full nose-up travel, because the c172p cannot reach AeroGuard's commanded static angle of attack. The roughly-v0.3-proportion target is dropped; the achieved rates are reported.

### P4-D3 — Fresh JSBSim instance per trajectory (2026-10-15)

- **Change:** each trajectory loads a new `FGFDMExec`. Reusing one instance after some trajectories made later trims fail (58 of 60 in one gradual pilot) in an order-dependent way, which is a harness defect, not aircraft behaviour.

### P4-D4 — JSBSim sample size and evaluation population (2026-10-15)

- **Protocol:** 300 JSBSim trajectories (80/60/160), split 70/15/15; cross-simulator models evaluated on the test split only.
- **Change:** 1,000 trajectories with the same regime proportions (267 normal, 200 stall, 533 gradual), same split fractions. Reason: at the observed crossing rates 300 trajectories would give about 8 stall events in the test split, too few for any event metric. Cross-simulator models (`X_D`, `X_D_noSM`, rules) are reported on the test split (the population shared with the native reference, primary) **and** on all 1,000 trajectories (secondary; legitimate because these models never see JSBSim data).

### P4-D5 — Novelty score for JSBSim abstention in the actuator-free feature space (2026-10-15)

- **Protocol (section 11):** abstention rate under `U_nov` "(τ from section 6)", whose novelty space is the 23 `M_D` features.
- **Change:** for JSBSim, `U_nov` is computed in the 20-feature `X_D` space (no `elevator`, `throttle`, `elevator_change_1s`) with its own τ, set the same way (5% of TRAIN-configuration validation rows). Reason: the actuator features have different units and meaning in JSBSim (section 11 already removes them from the cross-simulator models), so including them would make every JSBSim row novel by construction. Written before any JSBSim row was scored.
