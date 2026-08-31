# Physics parity harness

The stall simulator on the dashboard (`06 — Stall Simulator`) runs the physics
*in the browser*, so `dashboard/src/lib/physics.ts` is a TypeScript port of the
Python engine. This directory exists to prove the port is faithful rather than
merely plausible — a lookalike that drifts would quietly invalidate every number
the simulator reports.

## What is compared

`dump_reference.py` runs the **real** Python engine (`aeroguard/aerodynamics.py`,
`dynamics.py`, `integrator.py`, `scripts/simulate.py`'s trim solver,
`aeroguard_dataset/events.py`, `aeroguard_dataset/control_profiles.py`) over three
deliberately different airframes — the stock generic aircraft, a heavy/small-wing
one, and one with a reshaped lift curve — and dumps:

- `CL(alpha)` and `CD(alpha)` at 14 angles spanning pre-stall, the break, and deep post-stall
- `CLmax`, the numerically located `CL`-peak angle, and the 1g stall speed
- the trim solution (alpha, throttle, elevator) at each airframe's entry airspeed
- the elevator pulse shape at 28 sample times
- the full five-state RK4 trajectory, probed at 11 times across a 20s / 2000-step run

`check.mjs` compiles the TypeScript engine with the project's own `tsc`, runs the
identical cases, and compares all 420 values.

## Run it

```bash
../.venv/bin/python parity/dump_reference.py   # from dashboard/
node parity/check.mjs
```

Exit status is non-zero if anything drifts. Current result: **420/420 checks pass**,
largest relative difference `4.5e-14`, largest absolute difference `2.3e-13` — i.e.
floating-point rounding after 1900 RK4 steps, not modelling divergence.

## When to re-run

Any time either engine changes: edits under `aeroguard/`, a change to the trim solver
or the stall-boundary definition, or edits to `src/lib/physics.ts`. Regenerate
`reference.json` first (it is committed so the check can run without a Python
environment, but it is only as current as the last dump).
