# Stall-boundary sensitivity analysis — 2026-11-11

**Status:** New deterministic curve-level analysis of the implemented lift function. Not real-aircraft validation, not a rerun of Phase 4, and not a change to frozen v0.3 results.

## Method
- Evaluated the exact source equations in `aeroguard/aerodynamics.py` using default `Aircraft` parameters.
- Positive angle grid: 0°–40° at 0.0001° spacing; peak refined by local parabolic interpolation.
- One-factor-at-a-time: nine evenly spaced values across each range declared in `experiments/phase4/PARAMETER_RANGES.md`, holding other parameters at v0.3 defaults.
- Interaction check: 7×7×7 factorial (343 cases) over `alpha_stall`, `stall_transition_rate`, `post_stall_decay_rate`; `CL0` and `CL_alpha` fixed.
- These are modelling ranges, not confidence intervals or empirically validated distributions.

## Baseline
- Numerical lift-curve peak: **16.06907°**
- Peak lift coefficient: **1.736234**
- Configured transition anchor: **16.00271°**
- The peak is not mathematically identical to the transition-anchor parameter.

## OAT results

| Parameter | Declared range | Computed peak-angle range | CLmax range |
|---|---:|---:|---:|
| `alpha_stall` | 14°–18° | 14.2089°–18.0000° | 1.54469–1.92788 |
| `stall_transition_rate` | 15–35 | 16.0493°–16.1173° | 1.73621–1.73629 |
| `post_stall_decay_rate` | 2.0–4.5 rad⁻¹ | 16.0027°–16.5453° | 1.73615–1.74092 |
| `CL0` | 0.15–0.30 | 16.0028°–16.1046° | 1.68635–1.83615 |
| `CL_alpha` | 4.5–5.8 rad⁻¹ | 16.0383°–16.0763° | 1.45687–1.82005 |

All 45 OAT curves showed a monotonic decrease after the computed positive-angle peak through 40° under the numerical check used.

## Shape-parameter interaction check
Across 343 combinations:
- Computed peak angle: **14.0000°–18.7200°**
- Peak lift coefficient: **1.54390–1.93301**
- Monotonic post-peak decrease through 40°: **343/343 cases**

The peak can lie above the configured 18° anchor. This confirms that the operational peak is an emergent property of the blend, not a synonym for `alpha_stall`.

## Interpretation
The model-defined boundary is sensitive mainly to the transition anchor and, secondarily, to post-stall decay. Blend sharpness over its declared range produces a much smaller change by itself. `CL0` and `CL_alpha` substantially change peak lift, with comparatively small changes in peak location.

The original approximately 16.07° value is reproducible for the default parameter set, but it is not universal or empirically established. The declared shape-parameter bands permit the numerical boundary to move materially.

## Limitations and next step
1. Ranges are the previously documented Phase 4 modelling ranges; some are engineering estimates or surrogate-only bands.
2. OAT does not capture interactions. The factorial covers only three shape parameters, not all five lift-curve parameters jointly.
3. This is a static mathematical curve analysis. No trajectories were regenerated, no v0.3 labels changed, and no frozen model was evaluated.
4. Monotonicity is an internal shape property, not proof of aerodynamic accuracy.
5. No primary wind-tunnel or aircraft-specific experimental lift data were used.

This result is suitable for disclosing model sensitivity to professors, but it does **not** complete physical validation. The next scientific step is comparison with primary aerodynamic data for a named configuration under stated Reynolds number, Mach number and configuration conditions. A separate pre-specified trajectory study would be needed to assess the effect on precursor durations and ML metrics.

## Files
- `one_factor_at_a_time_summary.csv`: aggregate results for all five OAT parameters.
- `shape_parameter_factorial_summary.json`: bounds over all 343 factorial cases.
- `sensitivity_method.md`: ranges and method.
- `scripts/analyze_stall_boundary_sensitivity.py`: executable analysis script.
