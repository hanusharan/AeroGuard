# Phase 4 parameter ranges — basis and provenance (Item 43)

Companion to `PROTOCOL.md` section 1.1. The ranges describe a **generic four-seat,
single-piston-engine light-aircraft class**. They are meant to be defensible
orders of magnitude for that class, not the properties of any one type.

Provenance levels used below:

- **J** — read from a JSBSim aircraft definition file shipped with the `jsbsim`
  1.3.2 Python wheel (checkable locally: `python -c "import jsbsim; print(jsbsim.get_default_root_dir())"`, then `aircraft/<name>/<name>.xml`). JSBSim files are community models, themselves approximations.
- **S** — secondary source found by web search on 2026-10-15 (a manufacturer data
  summary or teaching material). Primary documents (POH, NACA reports) could not
  be opened from the research environment (network policy blocked NTRS and the
  type-data sites), so these are not checked against the primary document.
- **E** — engineering estimate from a standard textbook relation, stated explicitly.
- **B** — uncertainty band around the v0.3 surrogate value; there is no physical
  quantity to compare it with.

| Parameter | Range | Level | Basis |
|---|---|---|---|
| `mass` | 900–1400 kg | S, J | C172R maximum takeoff 2,450 lb ≈ 1,111 kg (S). JSBSim c172p empty weight 1,500 lb ≈ 680 kg; c182 empty 1,700 lb ≈ 771 kg (J). The range spans a lightly loaded C172-class aircraft to a heavy C182-class aircraft. |
| `wing_area` | 14.5–17.5 m² | J | c172p/c172x/c182 174 ft² ≈ 16.2 m²; pa28 160 ft² ≈ 14.9 m²; c310 175 ft² ≈ 16.3 m² (J). Range extends ±~1 m² beyond these. |
| `CL_alpha` | 4.5–5.8 /rad | E, J | Lifting line: a = a0/(1 + a0/(π e AR)); a0 ≈ 6.0/rad (thin-airfoil 2π reduced by thickness/viscous effects), AR 6–9, e 0.7–0.9 gives ≈ 4.3–5.1/rad (E). The c172p `CLwbh` table rises from 0.25 at α = 0 to 1.25 at α = 0.21 rad, ≈ 4.8/rad (J). The v0.3 value 5.5 is at the upper end, so the range extends below it. |
| `alpha_stall` | 14–18° | J, E | c172p `CLwbh` peak at α = 0.28 rad ≈ 16.0° (J). Clean-wing light aircraft with NACA 4-digit/23xxx sections typically stall around 14–18° (E; textbook range, not checked against a primary source). |
| `CL0` | 0.15–0.30 | J | c172p `CLwbh` at α = 0 is 0.25 (J). |
| `CD0` | 0.025–0.036 | E | Fixed-gear light singles are commonly quoted around 0.025–0.035 (E; not checked against a primary source). |
| `k` | 0.040–0.060 | E | k = 1/(π e AR) with e 0.7–0.9 and AR 6–9 gives 0.039–0.076; the range keeps the better-efficiency half (E). |
| `thrust_max` | 2200–3200 N | E | Order-of-magnitude static/low-speed thrust of 150–230 hp propellers (E). Throttle only scales thrust in this model; thrust does not vary with airspeed (assumption A7). |
| `Iyy` | 1000–1900 kg m² | J | c172p/c172x/c182 1,346 slug ft² ≈ 1,825 kg m²; pa28 1,249 slug ft² ≈ 1,693 kg m² (J). v0.3 uses 1,285 kg m², so the range covers v0.3 and the JSBSim values. |
| `elevator_effectiveness`, `pitch_damping`, `alpha_stiffness` | ×0.75–×1.25 | B | Gains of the linear pitch surrogate (`aeroguard/dynamics.py`). They are not aerodynamic derivatives of a real aircraft, so only a ±25% band is defensible. |
| `stall_transition_rate`, `post_stall_decay_rate` | 15–35; 2.0–4.5 /rad | B | Shape parameters of the smooth stall blend; uncertainty band. |
| `rho` | 0.905–1.225 kg/m³ | E | ISA density from sea level (1.225) to 10,000 ft (≈ 0.905) (E; standard atmosphere). Constant within a configuration (assumption A3). |

Conversions: 1 ft² = 0.092903 m²; 1 slug ft² = 1.35582 kg m²; 1 lb = 0.453592 kg.
