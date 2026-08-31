# CHANGELOG — AeroGuard research paper

Records how `AeroGuard_Research_Paper.md` was produced from the frozen research
report, what was deliberately left alone, and where the source material did not
support an edit.

**Source of truth:** `outputs/final/AEROGUARD_FINAL_RESEARCH_REPORT.md` (frozen),
plus the experiment artifacts it cites under `outputs/*/`. That report was **not
modified** — it is byte-identical to its committed version, verified by SHA-256.

---

## What was produced

| Artifact | Path |
|---|---|
| Editable source (single source of truth) | `paper/AeroGuard_Research_Paper.md` |
| Typeset PDF, 4 pages, two-column | `paper/AeroGuard_Research_Paper.pdf` |
| Web reading version | `paper/AeroGuard_Research_Paper.html` |
| Figures | `paper/figures/fig1–fig4*.png` |
| Figure build script | `paper/make_figures.py` |
| Paper build script (md → HTML → PDF) | `paper/build_paper.py` |
| Published copy served by the site | `dashboard/public/paper/` |

`build_paper.py` renders the Markdown to print-styled HTML and then to PDF via
headless Chrome, and copies the result into `dashboard/public/paper/`. No LaTeX
toolchain is installed on this machine (`pdflatex`, `xelatex`, `tectonic` and
`pandoc` are all absent), so the two-column typesetting is done in CSS rather
than in LaTeX. Rebuild everything with:

```bash
.venv/bin/python paper/make_figures.py && .venv/bin/python paper/build_paper.py
```

## What was improved

**Structure.** Reorganised the frozen report's 24 chronological sections into a
conventional paper: Abstract, Introduction, Methods (dynamics / data / model /
evaluation), Experimental Design and Results, Cross-Mechanism Generalization,
Discussion, Limitations and Threats to Validity, Conclusion, References.

**Framing.** The paper leads with the research question rather than with the
result, and keeps the chronology intact: the short-precursor problem is
presented as a finding, the physics diagnosis as its explanation, and the v0.3
control-profile change as the intervention it motivated.

**Experimental-design clarity (§3.3).** Added an explicit statement of what was
*not* changed — physics engine, aircraft parameters, `C_L(α)` curve, stall
boundary, features, model family, label definition, evaluation procedure — and
why changing only the control-input timing tests the hypothesis rather than
making the task easier: the boundary, the 5 s label horizon and the metrics are
identical, and a slow approach spends *longer* in the ambiguous region near the
boundary.

**Discussion (§5).** New section separating the two claims the results support —
multi-second early warning, and family-level generalization — from the zero-shot
claim they do not. The zero-exposure exclusion result is discussed as evidence
in its own right, not as a caveat.

**Quantitative presentation.** Added Table 1 comparing all five evaluation
conditions on PR-AUC, event recall, median credited lead time, and warning
coverage at ≥2 s and ≥4 s. Defined "credited lead time" and "warning coverage"
explicitly in §2.4 before using them.

**Figures.** Four figures, each composed only from values already recorded under
`outputs/`: pipeline schematic; v0.2 flat-α diagnosis vs. v0.3 precursor
coverage; v0.2 vs. v0.3 temporal performance; cross-mechanism transfer vs. the
regime-exclusion control. Captions state what each panel shows and cite the
source artifact.

**References.** Eleven external references, all real and verifiable, covering
aerodynamics, flight dynamics, the sigmoid stall-blend technique, random
forests, scikit-learn, precision–recall evaluation, early-warning signals for
critical transitions, and dataset shift. Repository artifacts are cited
separately as [A1]–[A5] so external background and project-internal evidence are
never conflated.

**Tone.** Removed superlatives and any language implying deployment relevance.
Every claim is scoped to "within this simulator."

## What was intentionally left unchanged

- **Every numerical result.** All 50 numeric claims were checked
  programmatically against the source JSON/CSV metrics files; 48 match exactly
  and 2 (`0.53 s`, `4.90 s`) are the frozen report's own roundings of `0.525`
  and `4.895`. No number was recomputed, re-derived, or re-run.
- **The central conclusion**, reproduced verbatim from the frozen report:
  multi-second early warning and transfer across structurally distinct
  control-input mechanisms are supported; universal zero-shot stall prediction
  across arbitrary unseen regimes is not.
- **Every limitation** in the frozen report's §20–21, including the ones that
  weaken the result: the `stall` regime is still imminent-only, per-event lead
  time is only moderately calibrated (r = 0.337, n = 22), event counts are
  small, Candidate F tests transfer *within* the elevator-driven family, and the
  concurrent-session calibration conflict.
- **The frozen report, physics engine, datasets, and models.** No file under
  `aeroguard/`, `aeroguard_dataset/`, `ml/`, `data/`, `scripts/`, `tests/` or
  `outputs/` was touched. No experiment, simulation, or model fit was run.

## Deviations and judgement calls, stated explicitly

1. **Figure 1 was redrawn.** The existing pipeline diagram
   (`outputs/final/figures/01_aeroguard_pipeline.png`) has a 1.8:1 aspect ratio;
   at a width that fits a two-column page its labels fall below ~4 pt. It was
   re-laid-out at 3.5:1 with the same stages and the same flow. It is a
   documentation schematic, not a plot of experimental data. The caption says so.

2. **Figures 2–4 were composed rather than reused.** The existing plots under
   `outputs/*/plots/` are single-topic and sized for a full page. Figures 2–4
   read the recorded metrics files directly (`make_figures.py` names the exact
   source for each series) and plot them at column width. No value is computed;
   every number plotted appears verbatim in a frozen artifact.

3. **Post-stall lift curve described from the code, not the report.** The frozen
   report §5 calls the post-stall branch "flat-plate-like." The current
   `aeroguard/aerodynamics.py` docstring records that the flat-plate curve was
   replaced with a monotonic exponential decay, because the flat-plate form
   produced a non-physical lift rebound near 25–30°. The paper describes the
   exponential-decay blend that the code actually implements. **This is the one
   place where the paper does not follow the frozen report's wording**, and it
   follows the code instead.

4. **Equations are written in `d·/dt` form.** The frozen report states the
   dynamics in prose and the code docstring uses `dV/dt`. Dot notation rendered
   unreliably in the available fonts, and `d/dt` matches the source anyway.

5. **v0.1 is summarised in one sentence.** The frozen report devotes §7 and §9
   to v0.1 and the ground-contact fix. At 4 pages this detail does not survive;
   v0.1's trajectory and row counts are stated and the reader is pointed at
   [A1]. Nothing about it is contradicted.

## Where the source did not support an edit

- **No confidence intervals or significance tests.** The frozen report records
  point estimates only (the single exception being the Wilson interval used to
  size v0.3's trajectory count, which is quoted). The paper therefore reports
  point estimates and states the sampling-uncertainty concern qualitatively
  under Limitations rather than inventing error bars.
- **No baseline comparison against published stall-warning systems.** Nothing in
  the repository benchmarks against an external system, so no such comparison is
  made or implied.
- **No per-regime breakdown for the transfer experiments.** The generalization
  report records aggregate metrics for the forward and reverse checks; the paper
  reports exactly those.
- **Hyperparameters are described as "frozen" without listing them.** The
  frozen report refers to `FROZEN_RF_PARAMS` without enumerating the values, so
  the paper says the hyperparameters were fixed on v0.2 and reused unchanged,
  and points to the repository for the values.

## Status

Published on the AeroGuard project website. **Not peer-reviewed, not submitted
to any venue, not flight-tested, and not validated against any real aircraft.**
