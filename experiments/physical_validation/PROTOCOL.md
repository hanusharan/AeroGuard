# Experimental aerodynamic validation protocol — draft v0.1

**Status:** Draft only. Not approved, not locked, and no aerodynamic fitting or validation run has been performed.

## 1. Purpose and scope

Establish a defensible comparison between AeroGuard's assumed lift-curve construction and independently measured airfoil-section data. This protocol is deliberately narrower than validating an entire aircraft simulator.

The current AeroGuard default is a generic, assumed aircraft model. It has no named airfoil, wing planform, Reynolds-number model, Mach correction, transition/roughness state, or spanwise load model. Therefore:

- A comparison to an airfoil-section polar can test whether a candidate *section-level* curve has plausible shape and scale.
- It cannot directly validate the existing generic aircraft's whole-wing lift curve or its 16.07° model-defined boundary.
- No parameter is to be fitted to a source dataset and then described as independently validated against that same dataset.
- A good match to section data does not validate the flight-dynamics model, the stall-warning classifier, or operational aviation safety.

## 2. Candidate primary data sources

### Primary source A — NACA 2412 at moderate Reynolds number

Seetharam, H. C., Rodgers, E. J., and Wentz, W. H. (1977), *Experimental Studies of Flow Separation of the NACA 2412 Airfoil at Low Speeds*, NASA-CR-197497 / AR77-3.

- NASA NTRS record: https://ntrs.nasa.gov/citations/19950002355
- Public report PDF: https://ntrs.nasa.gov/api/citations/19950002355/downloads/19950002355.pdf
- Test section: NACA 2412, 61 cm (24 in) chord, 91.4 cm (36 in) span, in a two-dimensional insert.
- Reported conditions: Reynolds number 2.2 × 10^6 based on chord; Mach 0.13.
- Transition was tripped using 2.5 mm (0.1 in) wide #80 carborundum grit strips at 0.05c on both surfaces.
- Figure 6 reports force-balance lift, drag and pitching moment over approximately −4° to +18°. The detailed flow-field surveys focus on 12.4°, 14.4° and 16.4°.
- The report compares its force data with NACA data at Reynolds numbers 3.1 × 10^6 and 5.7 × 10^6. It explicitly notes a 0.15 difference in maximum lift coefficient between the clean WSU 2.2 × 10^6 and NACA 3.1 × 10^6 datasets, and says the reason was unknown. The grit conditions also differ.
- This documented discrepancy is a reason to preserve each surface condition and Reynolds-number series separately, not to pool or average them.

Use Figure 6's force-balance lift curve as the main section-level benchmark, and use the tuft/separation observations and Table 2 as independent qualitative evidence of separation progression. Recover the actual plotted values and all figure legend details before fitting or comparing.

### Primary source B — NACA 2412 section polar at higher Reynolds numbers

Abbott, I. H., von Doenhoff, A. E., and Stivers, L. S. (1945), NACA Report 824, *Summary of Airfoil Data*.

- Digitized public report: https://www.pdas.com/refs/rep824.pdf
- The report includes a dedicated NACA 2412, 24-inch-chord aerodynamic-characteristics page with section lift coefficient versus angle of attack.
- The NACA 2412 plot legend includes multiple Reynolds-number / surface-condition series. Extract each series only after transcribing the exact legend and matching it to the curve markers; do not collapse different Reynolds numbers or roughness states into one curve.
- The report's general discussion notes the dependence of lift characteristics and maximum lift on Reynolds number and surface condition. These effects must be retained in the comparison.

### Secondary, low-Reynolds-number dataset — separate regime only

Stringer, D. B. (2022), *Airfoil 360 v2022: Wind Tunnel Data*, Mendeley Data, DOI 10.17632/dz4bv26ncd.1.

- Dataset: https://data.mendeley.com/datasets/dz4bv26ncd/1
- Includes NACA 2412 lift and drag data through 360° at Reynolds numbers 50,000 and 100,000; CC BY 4.0.
- This is useful as a separate low-Reynolds-number stress/shape comparison, not as a substitute for the moderate/high-Reynolds-number data relevant to a light aircraft.

## 3. Data extraction and provenance

Before any fitting:

1. Download and archive the exact primary-source PDFs and record retrieval date, URL, document identifier, file size and SHA-256.
2. Record airfoil geometry, chord, tunnel/test type, Reynolds number, Mach number, turbulence/transition treatment, roughness, corrections and measurement uncertainty for every curve.
3. Digitize the plotted data with calibrated axes. Preserve the original page image and digitizer project. Record pixel-to-axis calibration points and extracted coordinate table.
4. Independently repeat digitization of the key pre-stall and near-stall points. Resolve discrepancies before analysis; preserve both raw extractions.
5. Do not infer missing uncertainty bars. Mark values read from plots as digitized estimates and propagate the pixel-resolution uncertainty.
6. Do not use the NACA 2412 series as if it were AeroGuard's unspecified aircraft wing. The section/wing-body distinction must remain explicit.

## 4. Analysis design

### 4.1 Comparisons

Report separate comparisons for each source curve and condition:

- Linear-region lift-curve slope over a pre-declared attached-flow interval.
- Zero-lift angle and lift coefficient at selected matched angles.
- Maximum section lift coefficient and angle of attack at maximum lift, only where the measured curve resolves the peak.
- Post-peak trend and any abrupt lift loss / separation behaviour.
- Full-curve RMSE and MAE over the common measured angle interval.

Use radians consistently for derivatives and explicitly state coefficient conventions. Do not extrapolate outside the measured angle range.

### 4.2 Model comparisons

Compare at least:

- The existing AeroGuard smooth-blend/exponential-decay curve with its current defaults, unchanged.
- A candidate section-specific curve whose parameters are estimated only from a designated calibration curve.
- A simple linear-attached-flow baseline, to show how much the nonlinear model improves the near-stall/post-stall representation.

If a parameter is fitted, reserve a different condition/source for holdout evaluation. A source at a different Reynolds number is a *cross-condition transfer test*, not an exact matched-condition holdout. Do not pool the low-Reynolds-number Mendeley curves with the NACA 2412 high-Reynolds-number data.

### 4.3 Error and uncertainty reporting

Report point estimates and uncertainty ranges from digitization resolution and any source-reported experimental uncertainty. Do not manufacture statistical confidence intervals from digitized graph pixels. Keep measurement uncertainty, digitization uncertainty and model discrepancy separate.

## 5. Pre-specified interpretation

- **Section-level agreement:** the candidate reproduces the measured section polar within the pre-declared errors at matched geometry and flow conditions.
- **Partial agreement:** attached-flow slope is plausible but near-stall, peak, or post-stall behaviour is not.
- **Not comparable:** geometry, Reynolds/Mach conditions, surface state or coefficient definition cannot be matched or reconstructed.
- **Not validated:** no suitable primary data or sufficient condition metadata can be recovered.

Even a section-level agreement does not validate a finite wing or full aircraft. A later aircraft-level study would require a named aircraft configuration, wing planform/spanwise corrections, and preferably aircraft-specific wind-tunnel or flight-test evidence.

## 6. Stop conditions

Stop and document the blocker rather than substitute convenient values if:

- The raw report does not provide enough information to identify the correct curve/condition.
- The lift-balance data or plot cannot be digitized with defensible resolution.
- Reynolds number, Mach number, roughness or correction conditions are unknown.
- A proposed comparison would mix section and whole-aircraft coefficients.
- The candidate model's functional form cannot represent the observed data without arbitrary changes.

## 7. Frozen-artifact protection

This protocol authorizes no edits to frozen v0.3 trajectories, labels, model, paper, PDF, DOI record, canonical reports, locked Phase 3 protocol, baseline manifest, or `credibility-v1.1`. Any future fit or simulation must use a new model version, dataset namespace, run directory and provenance record. No result is to be called aircraft validation until the stated evidence exists.
