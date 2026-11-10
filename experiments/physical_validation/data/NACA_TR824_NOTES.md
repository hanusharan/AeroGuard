# NACA TR-824 — condition and extraction notes

**Source:** Abbott, von Doenhoff & Stivers (1945), NACA Report No. 824, *Summary of Airfoil Data*.

- NASA record: https://ntrs.nasa.gov/search.jsp?R=19930090976
- NASA PDF: https://ntrs.nasa.gov/api/citations/19930090976/downloads/19930090976.pdf
- UNT digital archive: https://digital.library.unt.edu/ark:/67531/metadc65534/
- NACA 2412 aerodynamic characteristics, 24-inch chord, printed page 136 (PDF zero-index page 135).

## Source details

TR-824 is a historical compilation of airfoil-section characteristics, with many section data obtained in Langley's two-dimensional low-turbulence pressure tunnel. Its NACA 2412 page includes:
- section lift coefficient vs section angle of attack;
- section drag and moment polars;
- an airfoil profile inset;
- multiple Reynolds-number and surface-condition curves.

The extracted-text rendering of the NACA 2412 legend indicates Reynolds-number entries around 3.1e6 and 5.7e6, plus standard roughness and different aerodynamic-center positions. The exact marker-to-condition mapping must be read from the page image before assigning each curve. OCR-derived series assignments are not sufficient.

The report's general discussion explicitly treats surface condition as a material factor. Figure 44 also illustrates that small normal model inaccuracies can reduce maximum lift on NACA 2412. Its discussion of airplane tests notes that complete-airplane lift can be more than 0.2 lower than a cited model result, due to installation and surface details. This reinforces the distinction between section-level and aircraft-level evidence.

## Extraction protocol

1. Inspect original page 136 at full resolution.
2. Record each legend symbol and its exact Reynolds number, roughness and aerodynamic-center annotation before digitizing.
3. Digitize each curve separately with calibrated axes; preserve pixel points and digitizer project.
4. Independently repeat extraction; compare both versions pointwise.
5. Do not extrapolate beyond the measured angle range or assign an ambiguous curve.
6. Record this report as a historical primary compilation; identify any reproduced/compiled curves separately from direct measurements if the page source notes so indicate.

No TR-824 data points are included in the first-pass CSV yet. Do not make numerical curve comparisons based on image/OCR summaries alone.
