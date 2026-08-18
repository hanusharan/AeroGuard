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

## `public/docs/`

Static copies of `README.md`, `PROVENANCE.md`, and
`outputs/final/AEROGUARD_FINAL_RESEARCH_REPORT.md` from the repository root, served
so the site's "Read the Paper" / "View Source" links work as a fully standalone site
without needing a real external host. These are copies, not symlinks — if the source
docs are updated, re-copy them into `public/docs/` to keep the site in sync.
