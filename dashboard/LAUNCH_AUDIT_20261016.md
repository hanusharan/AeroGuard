# AeroGuard website — launch-readiness audit (2026-10-16)

Scope: the public dashboard in `dashboard/` and its GitHub Pages workflow. No
research code, data, model, protocol or historical output was modified. All
changes are uncommitted in the working tree; nothing was committed, pushed,
merged or deployed.

## 1. Repository state

| | |
|---|---|
| Branch | `claude/aeroguard-launch-audit-a8kfa9` |
| HEAD | `74d1a11` (Merge pull request #2, Items 33–42 + Phase 4 protocol/code) |
| Relation to `main` | identical to `main` and `origin/main` at audit start (no commits ahead or behind) |
| Working tree at start | clean; no stashes |
| Item 50 work | **not present in this checkout.** No `scripts/phase4_item50.py`, `tests/test_phase4_item50.py`, `outputs/phase4/` or Item 50 entry in `RESEARCH_LOG.md`. `experiments/phase4/published_reference.json` exists only in its committed form (`ab91bed`). The uncommitted Item 50 work described in the brief lives in a different working environment and was neither seen nor touched. |

Protected artifacts (untouched): `aeroguard/` (physics engine), `ml/`, frozen v0.3
model and `outputs/ml_v03*`, `outputs/ml_temporal/`, `outputs/final/`,
`outputs/items33_42/`, `phase3/`, `phase4/`, `experiments/`, `paper/`, `data/`,
`baselines/`.

## 2. Production state

- URL: https://hanusharan.github.io/AeroGuard/
- **Could not be loaded from this environment:** the network proxy refuses
  `github.io` (CONNECT 403). The production site was **not** visually inspected.
- Deployment status via the GitHub Actions API: run #15 of
  "Deploy AeroGuard Dashboard" on `main` @ `74d1a11` completed **success**
  (2026-10-15T16:01Z). Runs #11–13 were `cancelled` by the workflow's
  `cancel-in-progress` concurrency (superseded pushes), which is expected.
- So the live site should correspond to current `main`, which equals this
  audit's starting HEAD. All local checks below were run against a production
  build served under the same `/AeroGuard/` base path.

## 3. What was inspected

`App.tsx`, `Nav.tsx`, every section (Hero, Scale, Problem, PhysicsEngine,
AIPipeline, Intervention, KeyResults, Evaluation, FlightReplay, Simulator,
Generalization, Limitations, Timeline, FutureWork, FinalCTA), `ui/*`, `hooks/*`,
`lib/links.ts`, `src/data/metrics.json`, `public/`, `data_export/`, `parity/`,
`index.html`, `vite.config.ts`, `package.json`, `.gitignore`, the deploy workflow.

Browser checks used headless Chromium (Playwright) against `vite preview` at
1440×900, 1280×800, 820×1180, 390×844 (touch) and 320×640 (touch), plus a
reduced-motion context.

## 4. Findings

### P0 — none found
Build passes; no secrets, credentials or local paths in `dist/`; no materially
false scientific claim; deployment workflow succeeded.

### P1 — found and fixed
| # | Finding | Fix |
|---|---|---|
| 1 | **No mobile/tablet navigation.** Below 1024 px the section links were `hidden`; only "Key Result" was reachable. | Menu button (`aria-expanded`, `aria-controls`, Escape to close, closes on link tap or on resize past `lg`) opening a 2/3-column list of all sections, incl. Evaluation and Future Work. |
| 2 | **Horizontal page overflow on phones** (page 402 px wide at 390 and 320 viewports). Causes: Key Results headline numbers (`text-6xl`/`text-5xl` in fixed rows) and Intervention grid items sized to the min-content width of a long source path. | Smaller numerals and padding below `sm`, `flex-wrap`, `min-w-0` on grid children, and `SourceNote` uses `overflow-wrap:anywhere` (which, unlike `break-words`, shrinks min-content width). Now 0 px overflow at all five viewports. |
| 3 | **Simulator number boxes could not be typed into.** Each keystroke was clamped immediately, so typing "1500" into Mass (min 400) produced 4000. | The box keeps a draft while typing; in-range values apply live, and out-of-range or partial input is clamped on blur or Enter; Escape discards unfinished text (an in-range value already applied live stays applied). Verified: "1500" → 1500, slider follows, outputs update; "9" → clamped to 400 on blur. |
| 4 | **Section deep links did not work.** `/AeroGuard/#simulator` opened at the top, because the browser resolves the hash before React renders. | `App` scrolls to the hash target once after mount. |

### P2 — found and fixed
| # | Finding | Fix |
|---|---|---|
| 5 | **Evaluation vs Key Results coverage looked contradictory.** Same frozen model: "Warned ≥2 s / ≥4 s" = 0.66 / 0.63 in Evaluation, 64.5% / 55.3% in Key Results. Both are correct but use different denominators: Item 38 counts only events whose trajectory has evaluated rows covering the full L seconds before crossing (74 at 2 s, 67 at 4 s; same 49 / 42 warned events). | A one-sentence note under the Evaluation table explains this; `coverage_item38.json` was added to its source note. No number changed. |
| 6 | No `prefers-reduced-motion` support: reveals, count-ups, three infinite loops (hero, pipeline, physics trace) and the replay autoplay all ignored it. | `MotionConfig reducedMotion="user"`; the hero, pipeline and physics trace render static final frames; the replay does not autoplay (Play still works); counters show final values; smooth scrolling and the nav ping are disabled. |
| 7 | No skip link and only browser-default focus rings on a near-black background. | "Skip to content" link targeting `<main id="main">`; global `:focus-visible` outline in the signal colour. |
| 8 | Range sliders had a 4 px tall hit area (poor for touch). | `.range-input`: 24 px hit area, 4 px track, 18 px thumb (simulator and replay). |
| 9 | Toggle state not exposed to assistive tech. | `aria-pressed` on simulator presets, `aria-expanded` on the advanced-terms toggle, `type="button"` on both. |
| 10 | Evaluation table's sideways-scroll area not reachable by keyboard. | Wrapped in a focusable `role="region"` with a label. |
| 11 | `public/docs/PROVENANCE.md` (linked from the site) was the superseded 2026-08-18 text; root was revised 2026-08-31. `public/docs/AEROGUARD_README.md` was also behind root `README.md`. The final-report copy was already identical. | Re-copied both from the repository root, as `dashboard/README.md` instructs. |
| 12 | FinalCTA claimed every number comes from the final report and its cited files, which is untrue since the Evaluation section (Items 33–42) was added. | Wording now names the Evaluation section's separate sources. |
| 13 | Limitations had no explicit "no operational safety / not certified" card (stated only in the Hero and footer). | Added "No operational or certification claim" card. |
| 14 | At 320 px the "Key Result" pill wrapped onto two lines and crowded the logo. | Hidden below 360 px (Results is in the menu); `whitespace-nowrap`. |

### Outstanding (not fixed; none launch-blocking)
- **P3:** the AIPipeline flow diagram's horizontal-scroll panel is not keyboard-focusable (the same content is described in text beside it).
- **P3:** the JS bundle is 847 kB (246 kB gzip), triggering Vite's chunk-size warning. It works but could be code-split.
- ~~P3: 6 high-severity dev-only `npm audit` advisories~~ — resolved in the verification pass (§12).
- **P3:** Timeline shows "190/190 tests" for the v1.0 freeze. That was accurate at the time; the suite now collects 226. It is a historical milestone and was left as is.
- **P3:** the deploy workflow does not run `oxlint` or the two parity checks; it could run them before upload.
- Recharts charts rely on adjacent text and source notes rather than per-chart text alternatives.

## 5. Files changed

| File | Why |
|---|---|
| `src/components/Nav.tsx` | Mobile menu (#1), skip link (#7), pill (#14), reduced-motion ping (#6) |
| `src/App.tsx` | `MotionConfig` (#6), `main` target (#7), deep-link scroll (#4) |
| `src/components/sections/KeyResults.tsx`, `Intervention.tsx`, `ui/Primitives.tsx` | Overflow (#2) |
| `src/components/sections/Simulator.tsx` | Typed input (#3), slider (#8), ARIA (#9) |
| `src/components/sections/Evaluation.tsx` | Denominator note (#5), keyboard region (#10) |
| `src/components/sections/Limitations.tsx` | Operational-claim card (#13) |
| `src/components/sections/FinalCTA.tsx` | Sourcing statement (#12) |
| `src/components/sections/FlightReplay.tsx` | Slider (#8) |
| `src/components/HeroTrajectory.tsx`, `sections/AIPipeline.tsx`, `hooks/usePlaybackCursor.ts`, `hooks/useScrubber.ts`, `ui/Counter.tsx` | Reduced motion (#6) |
| `src/index.css` | Focus ring (#7), reduced-motion scroll (#6), header scroll padding, slider styles (#8) |
| `public/docs/PROVENANCE.md`, `public/docs/AEROGUARD_README.md` | Re-synced copies (#11) |
| `parity/check_metrics.mjs` (new), `parity/README.md` | Displayed-metric consistency check (§7) |
| `LAUNCH_AUDIT_20261016.md` (new) | This report |

No workflow, `metrics.json`, `flightReplay.json` or paper file was changed.
`package.json` and `package-lock.json` changed only in the verification pass (§12).

## 6. Scientific values checked

All values in `src/data/metrics.json` match their canonical sources (99
automated checks, §7). Spot checks of displayed rounding:

| Display | Value | Source |
|---|---|---|
| v0.3 PR-AUC / ROC-AUC | 0.890 / 0.9775 | `outputs/ml_v03/metrics/primary_model_metrics.json` |
| Event recall | 96.1% = 73/76 (computed from counts; 0.9605 would round to 96.0) | same |
| Median lead (warned events) | 4.72 s | same |
| Coverage ≥2/3/4/5 s (all 76 events) | 64.5 / 59.2 / 55.3 / 38.2% | same |
| v0.2 PR-AUC, recall, median lead | 0.813, 14/14, 0.53 s | `outputs/ml_temporal/metrics/primary_model_metrics.json` (raw 0.5249999… = 0.525; the paper and v0.3 report also state 0.53 s) |
| Forward transfer | PR-AUC 0.835, 46/46, 2.96 s (source 2.955; README and paper also say 2.96 s), 94% of in-distribution PR-AUC | `outputs/ml_v03_generalization/metrics/forward_check_*.json` |
| Reverse transfer | 0.708, 47/54 = 87%, 5.00 s | `reverse_check_*.json` |
| Zero-exposure exclusion | 0.552, 64.5% (49/76), 0.73 s | `outputs/ml_v03/metrics/generalization_check.json` |
| Splits | 3,150 = 2,205 / 472 / 473 | `data/splits/split_manifest_v3.csv` |
| Evaluation table PR-AUC [CI] | 0.890 [0.854, 0.922]; 0.875 [0.835, 0.911]; 0.709 [0.667, 0.745] | `outputs/items33_42/items40_42/run_20261015T144358282823Z/REPORT.md` §1 |
| False warnings / sim. h | 18.8 [11.6, 26.8]; 29.5 [17.6, 43.8]; 23.4 [14.9, 33.4] | same, §3 |
| Warned ≥2 s / ≥4 s | 0.66 / 0.63; 0.69 / 0.63; 0.51 / 0.19 (eligible-event denominators 74 / 67) | same, §3; `coverage_item38.json` |
| Paired PR-AUC differences, matched-rate coverage contrasts, Item 33 ablation | +0.015 [0.008, 0.023]; +0.181 [0.150, 0.219]; +0.12, +0.09, CI incl. 0 at R=40; +0.34 to +0.45; all Item 33 CIs include 0 | same, §§1–3 |
| Test population | 456 trajectories, 76 events (57 first + 19 later), 1.49 sim. h | same, §3 |

Limitations coverage on the site: simulation-only and not validated with real
flight data (Hero, Key Results, Limitations, footer); simplified 2D physics
(Limitations); no operational safety or certification claim (Limitations,
footer); generalization bounded to the evaluated mechanism class (Limitations,
Generalization). The site makes no simulator-to-simulator (JSBSim) validation
claim, because Phase 4 is not presented.

## 7. Tests and checks run (exact outcomes)

| Check | Command | Result |
|---|---|---|
| Install | `npm ci` | success |
| Type-check + build | `npm run build` (`tsc -b && vite build`) | success; chunk-size warning only |
| Lint | `npm run lint` / `npx oxlint` | exit 0, no findings |
| Physics port parity | `node parity/check.mjs` | 420/420 pass, max rel. diff 4.51e-14 (before and after changes) |
| Displayed metrics (new) | `node parity/check_metrics.mjs` | 99/99 pass; negative test (nWarned 73→72) correctly fails with exit 1 |
| Static files in `dist/` | file checks | paper HTML/PDF, figures, docs, favicon present; assets under `/AeroGuard/` |
| Secrets / paths in `dist/` | grep | none (only React-internal `password` input-type strings) |
| Browser smoke, 5 viewports | Playwright | 0 console errors, 0 failed requests, 0 broken images, all `#` anchors resolve, 9 charts render, 0 px overflow, paper/docs links 200 |
| Interaction | Playwright | mobile menu opens/closes (tap, Escape, link); typed input; presets change outputs; first Tab focuses skip link with a visible ring; reduced motion: no autoplay, counters final |
| Dependency audit | `npm audit` | 6 high (dev-only) at audit time; **0** after §12 |

Not run: Python test suite (no test covers the dashboard; research experiments
deliberately not run), `parity/dump_reference.py` (needs the research venv;
the committed `reference.json` was used, as documented). The smoke scripts were
ad hoc and are not committed.

## 8. Public-artifact and security review

- The workflow publishes only `dashboard/dist`. Permissions are `contents: read`,
  `pages: write` and `id-token: write`: the minimum for Pages. Build is followed
  by deploy, and the paper-presence step fails the build if files are missing.
  No secrets are used.
- `dashboard/.gitignore` excludes `node_modules`, `dist`, `dist-ssr`, `*.local`
  (covers `.env.local` etc.) and logs.
- `dist/` (3.3 MB) contains the app bundle, self-hosted fonts, the paper
  (HTML, PDF, 4 figures) and three Markdown docs. These are intended public
  reproducibility material. No raw datasets, models, `parity/`, `data_export/`,
  env files or local paths are included.
- The site makes no runtime network calls. External links go to GitHub,
  doi.org and the experiment log.

## 9. Item 50 — recommendation: do not add to the site now

The final Item 50 report (`outputs/phase4/item50_final_*/REPORT.md`) is not in
this repository or on `main`. Committed `experiments/phase4/STATUS.md` still
records Item 50 as "Partly done". No value could be traced to a verified final
report, so the public content was left unchanged.

When the Item 50 work is committed and reviewed, an entry may be worth adding
under Scientific Scope (not Results), labelled "Comparison with published
evidence — complete with limitations". It should keep four things apart:

1. Agreement or disagreement with the Cessna manual's flaps-up stall speed, with
   its provenance level.
2. CL-curve and CL_max differences against the JSBSim c172p model, called a
   simulator-to-simulator comparison and not validation, with the failed
   predefined tolerances stated as failed.
3. NACA 2412 and drag-polar references that were unavailable.
4. Independent experimental validation that remains open.

It should not imply that Phase 4 as a whole has passed.

## 10. Remaining limitations of this audit

- Production was not loaded in a browser (proxy). Equivalence with the local
  build is inferred from the successful run on the same commit.
- Only Chromium was tested; Safari and Firefox were not, so the
  `::-moz-range-*` styles were not exercised. Testing was automated only, not
  on physical devices.
- Contrast: measured and fixed in the verification pass (§12).

## 11. Steps to deploy safely

Production deploys on every push to `main`. This branch currently equals `main`
plus only the uncommitted dashboard edits above, so no research work is mixed in.

1. Review the diff: `git diff -- dashboard/` and `git status` (only
   `dashboard/` paths should appear).
2. From `dashboard/`, re-run `npm ci && npm run build && npm run lint && node parity/check.mjs && node parity/check_metrics.mjs`.
3. Commit **only** `dashboard/` on this branch (e.g. `git add dashboard/`), and
   push `claude/aeroguard-launch-audit-a8kfa9`.
4. Open a PR into `main`. Confirm it touches only `dashboard/**` and that it does
   not include any Item 50 / Phase 4 files from the other working environment.
5. Merge. The workflow builds, verifies the paper files and deploys. Confirm the
   run is green, then load https://hanusharan.github.io/AeroGuard/ on a phone and
   a desktop: menu, `#simulator` deep link, typing in the simulator, paper and
   PDF links.
6. Rollback if needed: revert the merge commit on `main`, which redeploys the
   previous site automatically.

## 12. Verification pass (same day, same checkout)

An independent re-verification of the changes above, in the same working tree
(HEAD `74d1a11`, nothing staged, all 21 files present, no foreign changes).

**Additional fixes**

| Priority | Finding | Fix |
|---|---|---|
| P2 | **Contrast measured:** `--color-ink-faint` #5b6672 was 2.9–3.5:1 on the panel backgrounds actually used (WCAG AA needs 4.5:1). It coloured 144 text nodes, including source notes and the Evaluation denominator caveat. | Token raised to `#788796`, the same hue (≥4.66:1 on every panel background, still 1.5× dimmer than `ink-soft`); chart tick labels and the v0.2 legend/bar use the same value. Re-measured: 0 HTML text failures. |
| P2 | Pressing Escape with focus inside the mobile menu sent focus to `<body>`. | Focus returns to the menu toggle. |
| P3 → fixed | 6 high `npm audit` findings (dev/build only). `gh-pages` was referenced only in `package.json` (no script, workflow or doc) and was the sole path to `globby → fast-glob → micromatch → braces`. `source-map-js@1.2.1` came via `vite → postcss` and `@tailwindcss/node`. | `npm uninstall gh-pages` (lockfile: 686 lines removed, 0 added) and `npm update source-map-js` (one lockfile entry, 1.2.1 → 1.2.2, within existing ranges). Clean `npm ci` OK; `npm audit`: **0 vulnerabilities**. Deployment uses `actions/deploy-pages` and is unaffected. |

Files touched in this pass: `package.json`, `package-lock.json`,
`src/index.css`, `src/components/Nav.tsx`, and chart tick colours in
`sections/{Generalization,Simulator,FlightReplay,PhysicsEngine,KeyResults}.tsx`.

**Re-verified (all exit 0):** clean `npm ci`; `npm audit` 0; build; lint;
`parity/check.mjs` 420/420; `parity/check_metrics.mjs` 99/99. The negative test
used an isolated scratch copy with symlinked outputs (3 corruptions → exit 1,
clean copy → exit 0); no tracked file was modified.

**Browser (Chromium, local production build):**
- 0 px overflow at 320/360/390/768/1440, with no console errors or failed requests.
- The menu lists all 12 sections; Tab enters the menu; Escape closes it and restores focus; links land at the section top; it closes on resize.
- The simulator handles 1500, 0.5, −0.1, 12.5 and 1.005. Out-of-range input clamps on blur/Enter, empty input reverts, and no NaN appears. All 4 presets and 8 advanced fields work.
- Deep links to 9 sections land below the header on fresh loads (both widths, both motion modes); back/forward works; the skip link moves focus to `<main>`; the table region scrolls by keyboard.
- Reduced motion: the pipeline dot, hero and physics trace are static (the control run moves); counters are final; the replay does not autoplay but plays on request.

**Still not verified:** the live site (the proxy refuses `github.io`); browsers
other than Chromium; physical devices. Contrast measurement covered HTML text
only; SVG chart labels are covered by calculation.
