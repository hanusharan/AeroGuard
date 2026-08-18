# AeroGuard — Stage 1: 2D Longitudinal Flight-Dynamics Simulator

A small, readable physics engine for a generic fixed-wing aircraft,
restricted to the **longitudinal (vertical-plane) dynamics**. This is
the foundation for later research into whether a machine-learning
model can recover a physics-defined flight-safety boundary (e.g. a
stall boundary). No ML, trajectory generation at scale, or website
work is part of this stage.

**This is a simplified, educational physics model. It is NOT a
validated model of any real aircraft type**, and its outputs should
not be used to make claims about real-aircraft behaviour or safety.

## Project structure

```
AeroGuard/
├── aeroguard/              # the physics engine (importable package)
│   ├── __init__.py
│   ├── aircraft.py         # Aircraft parameters (mass, wing area, aero/thrust/pitch coefficients)
│   ├── aerodynamics.py     # CL(alpha), CD(CL), lift/drag/thrust force models
│   ├── dynamics.py         # state vector + equations of motion (RHS of the ODE)
│   └── integrator.py       # generic fixed-step RK4 integrator
├── scripts/
│   └── simulate.py         # runs one example trajectory and produces plots
├── tests/
│   ├── test_aerodynamics.py
│   ├── test_dynamics.py
│   └── test_integrator.py
├── outputs/                 # simulate.py writes trajectory.png here
└── requirements.txt
```

The engine (`aeroguard/`) has no dependency on the demo script or
plotting — `aerodynamics.py`, `dynamics.py`, and `integrator.py` each
depend only on `numpy` and each other, so they can be reused directly
by a future trajectory-generation or ML pipeline without pulling in
matplotlib.

## State variables

The simulator integrates a 5-element state vector:

| symbol  | meaning               | units |
|---------|-----------------------|-------|
| `V`     | airspeed              | m/s   |
| `gamma` | flight-path angle     | rad   |
| `theta` | pitch angle           | rad   |
| `h`     | altitude              | m     |
| `q`     | pitch rate            | rad/s |

Angle of attack is **not** stored as an independent state — it is
always derived as `alpha = theta - gamma`, exactly as specified.

## Forces and equations

**Lift and drag** (`aeroguard/aerodynamics.py`):

```
L = 0.5 * rho * V^2 * S * CL(alpha)
D = 0.5 * rho * V^2 * S * CD(CL)
CD = CD0 + k * CL^2
```

`rho` is currently a constant (sea-level density, 1.225 kg/m^3, see
Assumptions) rather than a function of altitude.

**Nonlinear lift curve with emergent stall.** `CL(alpha)` is built by
smoothly blending two closed-form curves:

- a **linear** pre-stall curve, `CL_linear = CL0 + CL_alpha * alpha`
- a **flat-plate-like** post-stall curve,
  `CL_flat = 2 * sign(alpha) * sin(alpha)^2 * cos(alpha)`, which rises,
  peaks, and then falls off as `alpha` grows

The blend weight `sigma(alpha)` is a logistic-type function centered
on `+/- alpha_stall` (default ~16°) that is close to 0 deep inside the
linear region and close to 1 well past stall, with a smooth
transition controlled by `stall_transition_rate`. The final curve is
`CL = (1 - sigma) * CL_linear + sigma * CL_flat`.

Because `sigma` is a continuous function of `alpha` and both component
curves are continuous, **CL(alpha) is smooth everywhere** — the rise,
peak, and post-stall drop-off are a consequence of the curve shapes
and the blend, not of a discrete `if alpha > alpha_stall` rule. This
blending approach is a standard technique used in simplified small
fixed-wing aerodynamic models (not something specific to any one real
aircraft).

**Thrust:** `T = throttle * thrust_max`, with `throttle` clamped to
`[0, 1]` — a simple linear throttle-to-thrust map, not a real engine
model.

**Equations of motion** (`aeroguard/dynamics.py`), exactly as
specified:

```
m * dV/dt     = T*cos(alpha) - D - m*g*sin(gamma)
m * V * dgamma/dt = L + T*sin(alpha) - m*g*cos(gamma)
dh/dt         = V * sin(gamma)
```

plus the two bookkeeping/control equations:

```
dtheta/dt = q
```

**Pitch / elevator response** (simplified short-period model):

```
Iyy * dq/dt = M_elevator*delta_e - M_q*q - M_alpha*alpha
```

This is a **linear surrogate** for the pitching-moment equation, not a
full aerodynamic-moment model: elevator deflection `delta_e` directly
drives pitch-rate acceleration, `M_q*q` damps pitch rate, and
`M_alpha*alpha` is a weak angle-of-attack restoring term. It gives the
elevator authority over pitch rate (and hence, through `dtheta/dt = q`
and `alpha = theta - gamma`, over angle of attack) without modeling
the underlying aerodynamic moments in detail.

## Key assumptions (read before using this for anything else)

1. **2D / longitudinal only.** No roll, yaw, sideslip, or lateral-directional
   dynamics. The aircraft is treated as a point mass with pitch attitude.
2. **Not a validated real-aircraft model.** All coefficients (`CD0`,
   `k`, `CL_alpha`, `alpha_stall`, `thrust_max`, pitch-response gains,
   etc., in `aeroguard/aircraft.py`) are plausible, order-of-magnitude
   defaults for a small generic fixed-wing aircraft, not measured or
   fitted data for any specific airframe.
3. **Constant air density.** `rho` = 1.225 kg/m^3 (sea level) at all
   altitudes — no atmosphere model. Reasonable for the modest altitude
   excursions expected in this stage; would need revisiting for
   large-altitude trajectories.
4. **Rigid body, constant mass.** No fuel burn, no structural flexibility.
5. **Simplified pitch dynamics.** The elevator-to-pitch-rate model is a
   linear surrogate (see above), not a full moment-coefficient (Cm)
   aerodynamic model with its own angle-of-attack- and rate-dependent
   nonlinearities.
6. **Simplified propulsion.** Thrust is a linear function of throttle
   only — no engine lag, altitude/speed lapse, or spool-up dynamics.
7. **Stall model is illustrative, not empirical.** The CL(alpha) curve
   shape (linear region blended with a flat-plate post-stall curve) is
   chosen to produce qualitatively correct, smooth stall behaviour
   (rise, peak near the critical angle, fall-off after), not to match
   wind-tunnel data for a particular wing/airfoil.
8. **Small-angle / basic trim only.** The trim procedure in
   `scripts/simulate.py` is an algebraic approximation (assumes the
   linear lift region and `gamma = 0`), not an iterative numerical
   trim solver — it is only accurate near the linear lift region.

## Running the simulation

From the `AeroGuard/` directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/simulate.py
```

This runs one 20-second trajectory: the aircraft starts in an
approximately trimmed level-flight condition, then a pitch-up elevator
step (t = 2s to 5s) drives the angle of attack up toward and past the
stall region before the elevator is released. It prints trim
conditions and key trajectory stats, and saves a 4-panel figure to
`outputs/trajectory.png` with:

1. Airspeed vs time
2. Angle of attack vs time
3. Altitude vs time
4. Lift coefficient vs angle of attack (this is the panel that shows
   the emergent stall behaviour — CL rises, peaks near ~16°, then
   falls)

Set `AEROGUARD_SHOW_PLOT=1` before running to also open an interactive
matplotlib window (in addition to saving the PNG).

## Running the tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Test coverage:

- **`tests/test_aerodynamics.py`** — CL(alpha) matches the linear model
  near alpha=0, CL0 case, CL increases through the linear region, CL
  is lower deep past stall than right at the critical angle (stall
  emerges from the curve, not a threshold), CL has a genuine peak
  followed by a decrease, the CL curve is odd-symmetric when CL0=0,
  the drag polar formula (`CD = CD0 + k*CL^2`) holds and `CD >= CD0`
  always, lift/drag scale with `V^2`, thrust is linear in throttle and
  clamped to `[0, 1]`.
- **`tests/test_dynamics.py`** — `alpha = theta - gamma` bookkeeping,
  `dh/dt = V*sin(gamma)`, `dtheta/dt = q`, elevator increases `dq/dt`,
  higher pitch rate is damped (lower `dq/dt`), higher throttle gives
  higher forward acceleration, and at an algebraically-computed level
  trim point both `dV/dt` and `dgamma/dt` are close to zero.
- **`tests/test_integrator.py`** — the RK4 step/integrate functions are
  checked against problems with known analytical solutions: exponential
  decay (`dy/dt = -y`) for accuracy, and constant-derivative motion for
  exactness, plus a basic shape/time-grid sanity check.

## Status

Stage 1 complete: physics engine + demo trajectory + tests, as scoped.
**Stopping here** — no trajectory-at-scale generation, ML, or website
work has been started, per the project instructions.
