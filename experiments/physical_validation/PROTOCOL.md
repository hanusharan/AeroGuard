# Experimental aerodynamic validation protocol — draft v0.2

**Status:** Draft only; not approved, not locked. No model parameter fitting or aircraft-level validation has been performed.

## 1. Scope and claim boundary

The AeroGuard default simulator uses a generic assumed lift law and has no named airfoil or aircraft. Validation is therefore staged:

1. **Section-curve comparison:** compare a declared two-dimensional NACA 2412 section model to experimental section-polar data at matched conditions.
2. **Cross-condition check:** compare across distinct Reynolds number and surface conditions; do not call this same-condition validation.
3. **Finite-wing / aircraft validation:** out of scope for this protocol. It would require geometry-specific 3-D corrections or aircraft-specific experimental/flight data.

No result here validates AeroGuard's flight-dynamics simulator, stall-warning ML, real-aircraft performance or safety.

## 2. Primary experimental source A: WSU NACA 2412

Seetharam, H. C., Rodgers, E. J., and Wentz, W. H., Jr., *Experimental Studies of Flow Separation of the NACA 2412 Airfoil at Low Speeds*, Wichita State University AR77-3, report cover October 1977, NASA-CR-197497.

- NASA record: https://ntrs.nasa.gov/citations/19950002355
- PDF: https://ntrs.nasa.gov/api/citations/19950002355/downloads/19950002355.pdf
- NACA 2412 section, 24-inch chord, 36-inch span, two-dimensional test insert.
- WSU conditions: Reynolds (2.2\times10^6), Mach 0.13.
- WSU grit transition trip: 0.1-inch #80 carborundum strips at (x/c=0.05) on both surfaces.
- Figure 6(a), printed report page 21 (zero-index PDF page 24), contains WSU force-balance lift curves and comparison curves.
- Figure 6 legend: circles are WSU grit, squares WSU clean, triangles clean Ref. 9, diamonds NACA grit Ref. 9.
- Reference 9 in the report bibliography is Abbott & von Doenhoff, *Theory of Wing Sections* (Dover, 1959). Triangle/diamond values are reproduced comparison data, not new WSU test measurements.
- Report notes ~0.15 difference in maximum (c_l) between WSU clean and Ref. 9 clean and says the reason is unknown. Keep these conditions separate.
- NASA record catalogue date is 1997; the report cover itself is October 1977.

The report's detailed flow field is measured at 12.4°, 14.4° and 16.4°. It describes separation moving upstream from about 0.925c at 12.4° to 0.80c at 14.4° and 0.40c at 16.4°. The report labels 14.4° as the stall condition for that test. These are section-specific observations, not a general aircraft stall angle.

## 3. Primary experimental source B: NACA TR-824

Abbott, I. H., von Doenhoff, A. E., and Stivers, L. S., Jr. (1945), *Summary of Airfoil Data*, NACA Report No. 824.

- NASA record: https://ntrs.nasa.gov/search.jsp?R=19930090976
- NASA PDF: https://ntrs.nasa.gov/api/citations/19930090976/downloads/19930090976.pdf
- UNT digital archive: https://digital.library.unt.edu/ark:/67531/metadc65534/
- NACA 2412 aerodynamic-characteristics sheet is printed page 136 (PDF zero-index page 135), 24-inch chord.
- This is a historical low-turbulence pressure-tunnel compilation with separate Reynolds-number and surface-condition traces. The NACA 2412 figure legend identifies a (3.1\times10^6) series, additional (5.7\times10^6) series, and a standard-roughness series. The curves and legends must be read directly from the page image before assigning exact marker-to-condition mapping.
- Do not use OCR-derived curve values or infer which curve is smooth/rough when marker mapping is unclear.
- The report's general discussion states that surface condition materially affects airfoil performance. Its discussion of airplane tests also notes that full-airplane lift can be more than 0.2 lower than the cited model result, so section results cannot be substituted for full-aircraft data.

## 4. Additional same-condition experimental cross-check

Rodgers, E. J., Seetharam, H. C., and Wentz, W. H., Jr. (1982), *Experimental Studies of Flow Separation of Three Airfoils at Low Speeds*, NASA-CR-3530 / AR-79-2.

- NASA record/PDF: https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/19840020667.pdf
- This report includes NACA 2412 section tests at (Re=2.2\times10^6), (M=0.13), with force, pressure, tuft, hot-film, skin-friction and boundary-layer data.
- It is a related Wichita State/NASA campaign with overlapping investigators and institutional provenance; it is not an independent-laboratory replication. Use it as an additional source/test campaign, not as statistically independent confirmation.

## 5. Data extraction and evidence labels

Every extracted point must carry:
- report, printed page/figure, curve label and source provenance;
- airfoil, chord, Reynolds number, Mach, surface/trip condition and test facility;
- extraction operator, tool/version, axis calibration points and date;
- raw pixel coordinates plus calibrated ((\alpha,c_l));
- digitization uncertainty separately from source measurement uncertainty.

Use the following labels:
- `primary_digitized`: curve digitized directly from a primary experimental report page;
- `secondary_reproduced`: curve reproduced in another report from a cited source;
- `approx_visual_only`: preliminary hand-read estimate; not fit-eligible;
- `unresolved_curve_identity`: do not include in quantitative comparison.

A second independent digitization is required for every curve included in a formal quantitative comparison. Preserve both raw extractions and report their pointwise discrepancy. If the difference is larger than the declared reading tolerance, resolve it before proceeding.

The current file `data/nasa_cr197497_figure6a_digitized_approx.csv` is `approx_visual_only`. It is a rough first-pass visual estimate, not an author-supplied table, and must not be treated as final evidence.

## 6. Comparison plan

1. Use WSU clean at (Re=2.2\times10^6), (M=0.13) as a candidate calibration reference only after independent digitization and complete condition metadata.
2. Keep WSU grit as a separate surface-condition sensitivity curve.
3. Keep TR-824 curves by Reynolds number and roughness separate. The matching Reynolds number does not erase differences in transition, tunnel, surface or model condition.
4. Report attached-flow slope, zero-lift angle, (c_l) at matched angles, measured peak (c_l)/angle where captured, and post-peak trend.
5. Compare the existing AeroGuard default curve unchanged as a diagnostic baseline.
6. If fitting a NACA 2412-specific curve, fit only on a predeclared calibration curve/condition, hold out a distinct curve/condition, and report this as cross-condition transfer where conditions differ.
7. Report MAE/RMSE only on validated, second-digitized points over the common measured alpha range. Keep pointwise measurement and digitization uncertainties separate. Do not manufacture confidence intervals from graph pixels.

## 7. Interpretation rules

- **Matched-condition section agreement:** supported only if geometry, Reynolds number, Mach number, transition and surface condition are sufficiently matched and the independent digitization checks pass.
- **Partial section agreement:** attached-flow slope matches but peak or post-peak shape does not.
- **Cross-condition transfer:** performance holds across distinct Reynolds-number/surface conditions; this is not matched-condition validation.
- **Not comparable:** data provenance, coefficient definition or condition metadata cannot be matched.
- **Not validated:** evidence is insufficient or the quantitative extraction has not been independently checked.

No section-curve comparison proves that AeroGuard's generic aircraft model is physically validated.

## 8. Stop conditions and frozen artifacts

Stop rather than guess if curve identities, test conditions, axis calibration or digitization are unclear.

This protocol authorizes no changes to frozen v0.3 trajectories, labels, model, paper, PDF, DOI, canonical reports, locked Phase 3 protocol, baseline manifest or `credibility-v1.1`. Any later fit or new simulator must use a separate version, dataset, run directory and provenance record.
