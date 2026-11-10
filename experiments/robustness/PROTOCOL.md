# Realism and robustness experiment — draft v0.1

**Status:** Draft only. Not approved, not locked, and no new simulator, trajectories, models or metrics have been run under this protocol.

## 1. Research question

Does the apparent early-warning advantage observed in AeroGuard's simplified simulation persist when the simulated aircraft and observation pipeline include selected effects that are absent or idealised in v0.3?

This is a simulation robustness study. It is not a real-aircraft safety demonstration.

## 2. Hypotheses

- H1: Temporal warning performance degrades as sensor noise, sensor delay and disturbance intensity increase.
- H2: The relative advantage of temporal features over an instantaneous-state baseline may shrink when the dynamics and aerodynamic response are made less deterministic.
- H3: A warning system calibrated only under clean conditions may experience a higher false-warning burden or lower event coverage under shifted observation/flight conditions.
- H4: Dynamic-stall and nonlinear pitch-response effects can change precursor timing; the direction and magnitude are empirical outcomes, not assumptions.

Null and negative outcomes must be reported. No minimum PR-AUC or recall is a pass criterion unless specified before data generation.

## 3. Separate model and data namespace

Create a new simulator package/version and new output namespace, for example:

- Model: `aeroguard_robust_v1`
- Protocol: this file, once reviewed and locked
- Data: `data/robustness_v1/` (gitignored if large)
- Outputs: `outputs/robustness_v1/run_<UTC>/`

Do not change or regenerate v0.3 or Phase 4 data. Do not silently replace the existing lift curve or pitch model. Keep a baseline run using the unchanged v0.3 simulator for paired comparisons.

## 4. Physics and observation factors

Implement and validate each factor independently before crossing them.

### A. Unsteady lift / dynamic stall

Use a documented, cited dynamic-stall formulation with explicit state variables and parameters (for example, a suitable Leishman–Beddoes-family formulation or another defensible low-order unsteady-aerodynamics model). State its applicability envelope and calibration source. Do not simply add an arbitrary lag and call it dynamic stall.

At minimum distinguish attached-flow lag, separation development, and reattachment/hysteresis where supported by the selected model. If a defensible parameter set cannot be identified, label the factor exploratory and do not make a physical-fidelity claim.

### B. Nonlinear pitch dynamics

Replace the fixed linear pitch-moment surrogate only in the new simulator branch. Use documented dimensional/sign conventions and dynamic-pressure scaling for aerodynamic moment derivatives, including relevant `Cm_alpha`, `Cm_q`, `Cm_alpha_dot` and `Cm_delta_e` terms where the selected source/model supports them. Check trim, stability and unit consistency before generating trajectories.

### C. Atmospheric disturbances

Add reproducible gust/turbulence inputs with a named model and recorded seeds. Prefer a documented Dryden or von Kármán turbulence implementation within a stated envelope. Include deterministic discrete-gust cases as a separately labelled stress condition. Record intensity, scale length, direction and time history.

### D. Sensor realism

Apply observation effects after the simulator state is generated:

- Angle-of-attack measurement noise with a declared distribution and scale.
- Sensor bias/drift as a separate factor, not conflated with random noise.
- Fixed measurement latency and sample/hold behaviour.
- Missing/dropout samples only as a separate factor.
- Derivatives and temporal features must be computed from the observed, delayed signal, never from hidden ground-truth state.

Keep ground-truth states and observed signals in separate columns. Document units, timestamps and causal filtering.

## 5. Factorial design

Use a staged design to avoid an unmanageable full factorial:

1. **Component verification:** test each new physics/observation component independently with analytic or synthetic checks.
2. **One-factor stress tests:** vary dynamic-stall treatment, pitch-model fidelity, gust intensity, AoA noise and sensor delay one at a time around a locked baseline.
3. **Selected interactions:** pre-select interactions with physical rationale, especially dynamic-stall × gust, sensor-noise × sensor-delay, and pitch-model × control-input mechanism.
4. **Combined stress set:** a small, fixed set of realistic combinations, selected and documented before any model evaluation.

The protocol must state numeric factor levels, seeds, number of trajectories, initial-condition distributions, and stopping criteria before data generation. Do not choose levels after inspecting test metrics. Ranges must be justified from cited sources or clearly labelled as engineering stress-test assumptions.

## 6. Dataset, model and evaluation discipline

- Split by complete trajectory and by condition/configuration; prevent trajectory fragments or repeated seeds from leaking across splits.
- Use a development set for model fitting and threshold selection, a validation set for any pre-declared model decisions, and a final held-out test set that is not repeatedly inspected.
- Compare a temporal model, an instantaneous-state baseline, and simple physical/rule baselines.
- Evaluate both the same frozen v0.3 model where its feature contract remains valid and newly trained models. Do not compare a retrained model to a frozen model without making the distinction explicit.
- Thresholds must be chosen only on development/validation data and frozen before test evaluation.
- Report PR-AUC, event recall, precision, false-warning episodes per simulated hour, median/mean credited lead time among warned events, warning coverage at ≥2 s and ≥4 s, calibration, and per-condition results.
- Report the number of eligible, excluded, warned and missed events. Define warning episode persistence and event attribution before running.
- Use paired trajectory-level uncertainty intervals for paired comparisons; configurations, not individual rows, are the unit of claims about generalisation.

## 7. Validity and verification gates

Before any scientific run:

1. Unit-test equations, units, limiting cases and deterministic seeded replay.
2. Validate trim and stable flight in the selected operating envelope.
3. Check dynamic-stall entry and recovery loops against the chosen model's published reference cases.
4. Check gust spectra/statistics against the selected turbulence model's expected properties.
5. Check sensor latency, noise, bias, missing-data and causal-feature implementation with known synthetic signals.
6. Confirm that all models see only the observation channel and never hidden simulator truth.
7. Freeze the protocol, code commit, environment, seeds and configuration manifest before test data generation.

A passing software test suite is not evidence that the aerodynamic model is physically accurate.

## 8. Reporting rules

Report each realism factor's effect separately before combined effects. State which effects are physically parameterised, which are simplified, and which are stress-test assumptions. Do not call JSBSim or another simulation model an experimental aircraft. Do not use the words "flight validated", "aircraft safe", or "operationally reliable" based on this study.

## 9. Frozen-artifact protection

No modification is authorised to frozen v0.3 trajectories, labels, model, paper, PDF, DOI record, canonical reports, locked Phase 3 protocol, baseline manifest, or `credibility-v1.1`. All new code, data, protocols and results remain on a new branch and under the new namespace. This protocol must receive review and be locked before execution.
