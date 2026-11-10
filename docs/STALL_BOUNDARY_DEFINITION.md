# Stall-boundary definition and justification

**Status:** Documentation supplement. This note clarifies the operational boundary used by the simulator and the v0.1–v0.3 labels. It does not change the physics model, regenerate data, or revise any frozen result.

## 1. What 16.07° means in AeroGuard

AeroGuard defines its simulator-specific stall boundary from the maximum of its implemented lift-coefficient function, not from a manually inserted event-trigger rule and not from measurements of a real aircraft.

The default aircraft parameterisation in `aeroguard/aircraft.py` is:

| Parameter | Value | Role |
|---|---:|---|
| (C_{L0}) | 0.2 | Zero-angle lift coefficient in the linear branch |
| (C_{L\alpha}) | 5.5 rad⁻¹ | Pre-stall lift-curve slope |
| (alpha_{stall}) | 0.2793 rad | Centre/anchor of the pre-/post-stall transition |
| Stall transition rate | 25 | Controls smoothness/sharpness of the blend |
| Post-stall decay rate | 3 rad⁻¹ | Controls decay of the post-stall branch |

The code constructs a smooth blend between

[
C_{L,linear}(\alpha)=C_{L0}+C_{L\alpha}\alpha
]

and an exponentially decaying post-stall branch

[
C_{L,post}(\alpha)=\operatorname{sign}(\alpha)C_{L,peak}
\exp[-k_p\max(|\alpha|-\alpha_{stall},0)],
quad
C_{L,peak}=C_{L0}+C_{L\alpha}\alpha_{stall}.
]

The blend is implemented by `_stall_blend` and `lift_coefficient` in `aeroguard/aerodynamics.py`. Since the transition is smooth, the parameter `alpha_stall` is an anchor for the transition, not by itself the mathematical definition of the final peak.

The project locates the peak numerically by sampling the implemented (C_L(\alpha)) curve over 0°–40° (2,000 evenly spaced samples) in `scripts/validate_physics.py::cl_max_of`. The peak is reported at approximately **16.07°**. The labeling code uses that numerically determined peak angle as the simulator's critical angle (alpha^*). Thus, 16.07° is a property of this particular chosen lift-curve function and parameter set.

For scale, the linear extrapolation at the anchor gives

[
C_{L,peak}=0.2+5.5(0.2793)\approx1.736.
]

This is an internally defined model quantity. It is **not** an empirically established (C_{L,max}) or stall angle for a named aircraft.

## 2. Why this is a defensible operational boundary inside this study

Within the simulator, the peak of (C_L(\alpha)) is the point at which further increasing angle of attack stops increasing modeled lift and begins decreasing it. It is therefore a coherent, reproducible threshold for defining a model-internal transition from the rising-lift branch to the falling-lift branch.

The existing physics-validation script checks that the numerically located peak lies within 0.5° of the `alpha_stall` anchor, that the modeled lift curve increases through the pre-stall range, and that it decreases monotonically after its peak over the tested post-stall interval. Those checks establish internal numerical/shape consistency for the specified curve. They do not establish that the curve is aerodynamically accurate for a real aircraft.

The distinction matters: the event called “stall” in the dataset is an **operational label defined by this simulator's chosen lift-curve peak**. It should not be read as a validated prediction of the onset, progression, or consequences of aerodynamic stall on an actual airframe.

## 3. Assumptions and limitations that qualify the boundary

- **Generic, assumed coefficients.** The default values describe a generic small fixed-wing aircraft and are not measured, identified, or fitted to a specific aircraft.
- **Prescribed functional form.** The smooth sigmoid blend, linear pre-stall branch, and exponential post-stall decay are modeling choices. The resulting peak depends on the selected `alpha_stall`, blend rate, decay rate, and lift-curve coefficients.
- **Symmetric positive/negative formulation.** The implementation uses (|\alpha|) and `sign(alpha)` in the post-stall branch and a symmetric blend. This imposes symmetric behavior for positive and negative angle of attack. It does not model the potentially different aerodynamics of upright and inverted flow, asymmetric separation, or airframe-specific effects.
- **No Reynolds/Mach/configuration dependence.** The lift curve is a function of angle of attack and fixed parameters; it does not account for changes in Reynolds number, Mach number, flap/gear configuration, surface condition, or other flight-condition dependencies.
- **Quasi-steady and low-order aerodynamics.** There is no dynamic-stall hysteresis, unsteady separation, three-dimensional flow, wing planform/spanwise stall progression, or detailed control-surface aerodynamics.
- **Simplified flight dynamics.** The surrounding model is 2-D longitudinal and point-mass, with a linear short-period pitch-response surrogate. It omits roll, yaw, sideslip, and departure dynamics.
- **No empirical calibration.** The model has not been validated against wind-tunnel measurements, flight-test data, or a validated aircraft-specific aerodynamic database.

These assumptions mean the numerical peak is useful as a controlled and reproducible boundary for experiments **inside this model**, but it should not be described as a physically verified stall angle in general aviation.

## 4. Recommended wording for the paper and professor outreach

> In AeroGuard, the stall boundary is defined operationally as the angle of attack at which the simulator's implemented lift-coefficient function reaches its numerical maximum. With the default generic parameterisation ((C_{L0}=0.2), (C_{L\alpha}=5.5\;\mathrm{rad}^{-1}), (alpha_{stall}=0.2793\;\mathrm{rad}), blend rate 25, and post-stall decay rate 3\;\mathrm{rad}^{-1})), a numerical sweep locates this peak at approximately 16.07°. This is a simulator-internal threshold resulting from an assumed, symmetric, quasi-steady lift-curve construction; it is not an aircraft-specific or experimentally validated stall angle. Accordingly, all stall labels and reported precursor durations refer to crossings of this model-defined boundary.

Avoid saying that 16.07° is “the real stall angle,” “validated,” or “standard for small aircraft.” Also avoid describing the model as validated aircraft physics: existing checks validate selected numerical and qualitative properties of the implementation, not its fidelity to a real airframe.

## 5. Work needed to strengthen the physical justification

This note clarifies the current basis; it does **not** complete the scientific validation. The next defensible study should:

1. Perform a pre-specified sensitivity analysis over plausible ranges for `alpha_stall`, blend rate, post-stall decay rate, (C_{L0}), and (C_{L\alpha}), reporting how both (alpha^*) and downstream precursor/event results change.
2. Justify the parameter ranges from authoritative aerodynamic references or aircraft-specific data, rather than choosing ranges solely because the simulator remains numerically well behaved.
3. Compare candidate lift curves against published wind-tunnel or aircraft-polar data for a clearly identified reference configuration, with units, Reynolds/Mach regime, and source provenance.
4. Revisit the symmetric (|\alpha|) boundary. Unless symmetric inverted-flight behavior is deliberately in scope and supported, define and evaluate positive-angle and negative-angle behavior separately.
5. Keep all such analyses separate from the frozen v0.3 dataset/model/report. Any new dataset or results should have a new protocol, version, and provenance trail.

Until those steps are completed, the correct claim is that AeroGuard uses a **model-defined lift-curve-peak boundary**, not that it has established a physically general critical stall angle.
