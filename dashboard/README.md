# AeroGuard Dashboard

The public-facing presentation site for the AeroGuard research project. This is a
**standalone, isolated** React app — it does not import or modify any code under
`aeroguard/`, `aeroguard_dataset/`, `ml/`, `scripts/`, or `tests/` at the repository root.
It only *reads* already-frozen research outputs to populate its data.

## Stack

Vite + React + TypeScript + Tailwind CSS v4 + Framer Motion + Recharts. Fonts (Inter,
JetBrains Mono) are self-hosted via `@fontsource` — no external CDN calls, no network
dependency at runtime.

## Run it

```bash
cd dashboard
npm install
npm run dev
```

Then open the printed local URL (default `http://localhost:5173`).

Production build:

```bash
npm run build   # outputs to dashboard/dist/
npm run preview # serve the production build locally
```

## Where the data comes from

Nothing displayed on the site is hand-typed from memory. Two read-only Python scripts
(`data_export/`) generate the JSON the site actually renders, by loading the frozen
research outputs directly:

```bash
# from the repository root, with the project's own .venv active
python dashboard/data_export/export_metrics.py         # -> src/data/metrics.json
python dashboard/data_export/export_flight_replay.py    # -> src/data/flightReplay.json
```

- `export_metrics.py` copies headline numbers verbatim from
  `outputs/ml_v03/metrics/primary_model_metrics.json`,
  `outputs/ml_temporal/metrics/primary_model_metrics.json`,
  `outputs/ml_v03/metrics/generalization_check.json`, and
  `outputs/ml_v03_generalization/metrics/*.json` — no value is computed, estimated, or
  adjusted; every field is either copied directly or a straightforward unit conversion
  (e.g. a fraction to a percentage).
- `export_flight_replay.py` loads the **frozen** `primary_model_D_1s.joblib` and calls
  `.predict_proba()` on one real, held-out v0.3 TEST-split trajectory
  (`traj_00413`, chosen because its model-credited lead time matches the reported
  event-level median almost exactly — see the script's own comments). This is pure
  inference against an already-trained model; nothing is retrained, retuned, or
  recalibrated.

Re-run both scripts any time the underlying research outputs are regenerated, then
`npm run dev`/`npm run build` again to pick up the refreshed JSON.

## The stall simulator's physics

The `06 — Stall Simulator` section is the one place on the site that *computes* rather
than reports: it lets a visitor enter an airframe and a maneuver and tells them where
the stall warning belongs. It does that by running the project's real physics engine
live in the browser — `src/lib/physics.ts` is a direct port of `aeroguard/aerodynamics.py`,
`aeroguard/dynamics.py`, `aeroguard/integrator.py`, the `scripts/simulate.py` trim solver,
the `aeroguard_dataset/events.py` stall boundary, and the `aeroguard_dataset/control_profiles.py`
pulse shape. Same nonlinear CL(alpha), same emergent stall, same fixed-step RK4, same
validity envelope, same numerically-located CL peak.

Because a port can silently drift from its original, `parity/` compares the two engines
value by value across three airframes and full 20s trajectories — 420 checks, currently
agreeing to a relative difference of 4.5e-14. See [`parity/README.md`](parity/README.md)
for what is covered and how to re-run it.

No ML model runs in the browser. The simulator's two warning triggers (a fixed
angle-of-attack margin and a rate-based time-to-boundary projection) are explicit
engineering rules applied to the simulated physics — they are not the trained model's
output, and the section says so on the page.

## `public/docs/`

Static copies of `README.md`, `PROVENANCE.md`, and
`outputs/final/AEROGUARD_FINAL_RESEARCH_REPORT.md` from the repository root, served
so the site's "Read the Paper" / "View Source" links work as a fully standalone site
without needing a real external host. These are copies, not symlinks — if the source
docs are updated, re-copy them into `public/docs/` to keep the site in sync.
