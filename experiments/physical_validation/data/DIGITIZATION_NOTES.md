# NASA Figure 6(a) — provisional digitization notes

## Source verification

Seetharam, Rodgers and Wentz, *Experimental Studies of Flow Separation of the NACA 2412 Airfoil at Low Speeds*, Wichita State University AR77-3, report cover October 1977, NASA-CR-197497.

- NASA record: https://ntrs.nasa.gov/citations/19950002355
- PDF: https://ntrs.nasa.gov/api/citations/19950002355/downloads/19950002355.pdf
- Figure 6(a): printed report page 21, zero-index PDF page 24.
- WSU NACA 2412 section, 24-inch chord, 36-inch span, Re=2.2e6, M=0.13.
- WSU grit trip: 0.1-inch #80 carborundum strips at x/c=0.05, both surfaces.
- Figure 6 symbols: circles = WSU grit; squares = WSU clean; triangles = clean comparator from Reference 9; diamonds = NACA grit comparator from Reference 9.
- NASA-CR-197497 bibliography identifies Reference 9 as Abbott & von Doenhoff, *Theory of Wing Sections* (Dover, 1959). The triangle/diamond series are reproduced comparison data, not new WSU measurements.

## First-pass visual readings

The file nasa_cr197497_figure6a_digitized_approx.csv contains 48 approximate hand-read points across four plotted series. These values were read from the scan and rounded. They are not author-supplied raw data or a numerical table.

The columns marked ±0.20° and ±0.025 CL are provisional graph-reading tolerances only, not the experiment's measurement uncertainty.

**Status: approx_visual_only.** Do not fit parameters, claim validation, publish formal MAE/RMSE or treat these as authoritative until a second independent operator digitizes the same figure from calibrated axes. Preserve both extractions and compare them pointwise.

NASA report text says the clean WSU and clean Reference 9 datasets differ in maximum CL by about 0.15, with the reason unknown. Keep each curve and its condition separate; do not average them.

## NACA TR-824 follow-up

The NACA 2412 characteristics page is printed page 136 (PDF zero-index page 135), 24-inch chord. The report includes lift vs angle and separate Reynolds-number/surface-condition curves. The exact legend-to-line mapping must be read from the original page image before digitization. See NACA_TR824_NOTES.md. No TR-824 numerical points have yet been extracted.

## Section vs aircraft

NACA 2412 data describe an airfoil section. AeroGuard uses an unspecified generic aircraft model without finite-wing, spanwise, Reynolds, Mach, roughness or transition modelling. This graph comparison is a model-form diagnostic only; it cannot validate the generic aircraft simulator or a real aircraft's stall angle.
