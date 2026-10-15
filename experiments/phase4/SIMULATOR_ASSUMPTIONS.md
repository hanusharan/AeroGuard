# Phase 4 simulator assumption audit (Item 51)

What the AeroGuard simulator models, simplifies and omits, with where it lives in code and the expected effect on stall-warning results. JSBSim column: whether the JSBSim `c172p` model used for Items 48–49 includes the effect.

| # | Assumption | Code | Expected effect on results | In JSBSim c172p? |
|---|---|---|---|---|
| A1 | 2D longitudinal only: no roll, yaw, sideslip; no wing drop at stall | `aeroguard/dynamics.py` | Stalls are symmetric and benign; no departure cues. Optimistic. | Yes (6-DOF; lateral hold added by us) |
| A2 | Pitch dynamics are a linear surrogate `Iyy q̇ = Me δe − Mq q − Mα α`; no Cm(α) nonlinearity, no Cm_q/Cm_α̇ from aerodynamics, no dependence on q̄ | `dynamics.py` | Elevator authority does not fade at low speed; AoA response time scale is fixed. Likely makes the precursor more regular than reality. | Yes (Cm tables, Cmq, Cmα̇, Cmδe scale with q̄) |
| A3 | Constant air density within a trajectory; altitude does not feed ρ | `aerodynamics.RHO_SEA_LEVEL`; Phase 4 passes a per-configuration ρ | Small for 500–2000 m; density altitude only varies between configurations. | Yes (standard atmosphere) |
| A4 | Lift is a function of α only (no CL_q, CL_α̇, CL_δe) | `aerodynamics.lift_coefficient` | No dynamic lift overshoot; stall happens exactly at the static α peak. | Yes (CLq, CLadot, CLDe) |
| A5 | Quasi-steady aerodynamics; no dynamic stall, no stall hysteresis | `aerodynamics.py` | Recovery is symmetric with entry; real wings stay stalled longer. | Partly (hysteresis column `aero/stall-hyst-norm`) |
| A6 | Smooth symmetric stall blend; post-stall decay is exponential and monotonic | `aerodynamics._stall_blend` | Boundary is a sharp, known α; real stalls vary with Reynolds number, contamination, flaps. | Tabulated to 0.36 rad only, clamped beyond |
| A7 | Thrust = throttle × T_max, independent of speed and altitude; no propwash or P-factor | `aerodynamics.thrust_force` | Power effects on stall speed and pitch are absent. | Yes (piston engine + propeller model) |
| A8 | Parabolic drag polar CD = CD0 + k CL² everywhere, including post-stall | `aerodynamics.drag_coefficient` | Post-stall drag is underestimated, so energy loss after the boundary is too slow. | Tabulated CD(α) |
| A9 | No flaps, gear, ground effect, wind, gusts or turbulence | — | No disturbance-driven false alarms or missed warnings; false-alarm rates are optimistic. | Flaps/ground effect yes; no turbulence by default |
| A10 | Perfect, noise-free, delay-free sensors at 100 Hz | dataset pipeline | Derivatives and 1 s window slopes are cleaner than any real AoA vane would give. Strongly optimistic for derivative features. | Same (we read true states) |
| A11 | Point-mass translational dynamics; no CG shift, fuel burn or mass change within a trajectory | `dynamics.py` | Negligible over 20 s. | Constant over 20 s too |
| A12 | Phase 4 control scaling: elevator pulses scaled by α-response gain and stall-α ratio so different aircraft get "pilot-equivalent" inputs | `phase4/sim.scale_profile` | Keeps crossing rates comparable across configurations; removes one real source of variation (pilots do not scale perfectly). | Not applicable (one gain mapping) |
| A13 | Validity envelope stops trajectories at V < 0.5 V_stall, \|γ\| > 45°, h ≤ 0 | `trajectory_sim.py` | Deep post-stall behaviour is never observed; labels only concern entry. | Same envelope + \|bank\| > 30° |
| A14 | Open-loop pulse inputs; no pilot reaction to the approaching stall | `control_profiles*.py` | Approaches are smoother and more predictable than a pilot-in-the-loop entry. | Same |

**Summary:** A2, A4, A9 and A10 are the assumptions most likely to make AeroGuard's early-warning skill optimistic relative to a real aircraft. JSBSim relaxes A1–A8 but not A9–A10 or A13–A14, so a JSBSim result is a test against a more detailed *model*, not against reality.
