# NASA Figure 6(a) — provisional digitization notes

## Source verification

The scanned report is Seetharam, Rodgers and Wentz, *Experimental Studies of Flow Separation of the NACA 2412 Airfoil at Low Speeds*, Wichita State University AR77-3, October 1977, NASA-CR-197497.

- NASA catalogue publication date is 1 October 1997; the report cover itself says October 1977.
- PDF: https://ntrs.nasa.gov/api/citations/19950002355/downloads/19950002355.pdf
- Figure 6(a) is on printed report page 21 (zero-index PDF page 24).
- Lift coefficient is section lift divided by free-stream dynamic pressure times chord.
- WSU experimental test condition: NACA 2412, 24-inch chord, 36-inch span, Re_c=2.2e6, M=0.13. The WSU transition tripping uses 0.1-inch #80 carborundum strips at x/c=0.05 on both surfaces.
- Symbols: circles = WSU grit; squares = WSU clean; triangles = clean comparison from Reference 9; diamonds = NACA grit comparison from Reference 9.
- Reference 9 in the report bibliography is Abbott & von Doenhoff, *Theory of Wing Sections*, Dover, 1959. The triangle/diamond series are reproduced comparison data in this report, not new measurements in the WSU test. They remain secondary-provenance values in this dataset.

## First-pass visual readings

The file nasa_cr197497_figure6a_digitized_approx.csv contains approximate visual readings of the traces at selected angle intervals. These were hand-read from the scanned figure and rounded. They are **not** the original experiment's machine-readable raw points, and the stated ±0.20° / ±0.025 CL are provisional digitizer-reading estimates only, not the experiment's measurement uncertainty.

The CSV is exploratory material only. Before any fitting, publication claim, or formal RMSE/MAE comparison:
1. A second person must independently digitize the same figure with calibrated axes (e.g. WebPlotDigitizer).
2. Both extractions must be retained and their pointwise differences documented.
3. The original Reference 9 source and its relevant Reynolds-number / surface-condition information must be checked directly.
4. The WSU clean and WSU grit conditions must remain separate. Do not average them.
5. Report 10 of NASA-CR-197497 states that clean WSU and clean Reference 9 differ by about 0.15 in maximum lift coefficient and that the reason was unknown. This is a meaningful source inconsistency, not a reason to tune AeroGuard to one convenient trace.

## Section-vs-aircraft warning

NACA 2412 is an airfoil section. AeroGuard's generic aircraft defaults are not identified as a NACA 2412 wing and do not include finite-wing, spanwise, Reynolds-number, Mach, surface, or transition modelling. This first-pass comparison is a model-form diagnostic only. It does not establish aircraft-level validation or invalidate/validate a universal stall angle.
