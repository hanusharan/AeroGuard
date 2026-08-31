/**
 * Browser port of the AeroGuard physics engine.
 *
 * This is a line-for-line port of the Python package -- NOT a
 * reimplementation, approximation, or curve-fit of it:
 *
 *   aeroguard/aerodynamics.py  -> stallBlend, liftCoefficient, dragCoefficient,
 *                                 dynamicPressure, liftForce, dragForce, thrustForce
 *   aeroguard/dynamics.py      -> equationsOfMotion (5-state longitudinal EOM)
 *   aeroguard/integrator.py    -> rk4Step
 *   scripts/simulate.py        -> trimLevelFlight, bisectRoot
 *   scripts/validate_physics.py-> clMaxOf, stallSpeed
 *   aeroguard_dataset/events.py-> resolveStallBoundary (CL-peak stall boundary)
 *   aeroguard_dataset/control_profiles.py -> smoothstep, Pulse.valueAt
 *
 * Numeric parity with the Python engine is checked by
 * dashboard/parity/ (see dashboard/parity/README.md).
 *
 * Same caveat as the Python original: this is a simplified, educational
 * model of a *generic* aircraft. It is not validated against any real
 * airframe.
 */

export const RHO_SEA_LEVEL = 1.225; // kg/m^3, constant air density
export const G = 9.81; // m/s^2

/** aeroguard/aircraft.py :: Aircraft (same fields, same defaults). */
export interface Aircraft {
  mass: number; // kg
  wingArea: number; // m^2
  Iyy: number; // kg*m^2

  CD0: number;
  k: number;

  CL0: number;
  CLalpha: number; // 1/rad
  alphaStall: number; // rad
  stallTransitionRate: number;
  postStallDecayRate: number; // 1/rad

  thrustMax: number; // N

  elevatorEffectiveness: number;
  pitchDamping: number;
  alphaStiffness: number;
}

export const DEFAULT_AIRCRAFT: Aircraft = {
  mass: 1200.0,
  wingArea: 16.2,
  Iyy: 1285.0,

  CD0: 0.028,
  k: 0.045,

  CL0: 0.2,
  CLalpha: 5.5,
  alphaStall: 0.2793, // ~16 deg
  stallTransitionRate: 25.0,
  postStallDecayRate: 3.0,

  thrustMax: 2600.0,

  elevatorEffectiveness: 3.2e4,
  pitchDamping: 6.0e3,
  alphaStiffness: 1.0e4,
};

// ---------------------------------------------------------------------------
// Aerodynamics (aeroguard/aerodynamics.py)
// ---------------------------------------------------------------------------

/**
 * Sigmoid-like stall blending function sigma(alpha) in [0, 1].
 *
 * The Python original computes
 *     num = 1 + A + B
 *     den = (1 + A) * (1 + B)
 * with A = exp(-rate*(alpha - alpha_stall)), B = exp(rate*(alpha + alpha_stall)).
 *
 * Expanding the denominator gives den = num + A*B, and A*B collapses to the
 * ALPHA-INDEPENDENT constant exp(2*rate*alpha_stall). So
 *     sigma = num / (num + A*B) = 1 / (1 + C/num),   C = exp(2*rate*alpha_stall)
 * which is algebraically identical to the Python form but cannot produce
 * inf/inf = NaN when A or B overflows at extreme alpha (there, num -> inf and
 * sigma -> 1, which is the correct limit).
 */
export function stallBlend(alpha: number, alphaStall: number, rate: number): number {
  const A = Math.exp(-rate * (alpha - alphaStall));
  const B = Math.exp(rate * (alpha + alphaStall));
  const num = 1.0 + A + B;
  const C = Math.exp(2.0 * rate * alphaStall); // == A * B, for every alpha
  return 1.0 / (1.0 + C / num);
}

/**
 * Nonlinear lift coefficient CL(alpha): a smooth blend between a linear
 * pre-stall curve and an exponentially decaying post-stall curve. Stall is
 * emergent from this blend -- there is no `if alpha > alpha_stall` branch.
 */
export function liftCoefficient(alpha: number, ac: Aircraft): number {
  const sigma = stallBlend(alpha, ac.alphaStall, ac.stallTransitionRate);

  const clLinear = ac.CL0 + ac.CLalpha * alpha;

  const clPeak = ac.CL0 + ac.CLalpha * ac.alphaStall;
  const excess = Math.max(Math.abs(alpha) - ac.alphaStall, 0.0);
  const clPostStall = Math.sign(alpha) * clPeak * Math.exp(-ac.postStallDecayRate * excess);

  return (1.0 - sigma) * clLinear + sigma * clPostStall;
}

/** Parabolic drag polar: CD = CD0 + k * CL^2. */
export function dragCoefficient(cl: number, ac: Aircraft): number {
  return ac.CD0 + ac.k * cl * cl;
}

/** q_bar = 0.5 * rho * V^2. */
export function dynamicPressure(rho: number, V: number): number {
  return 0.5 * rho * V * V;
}

export function liftForce(V: number, alpha: number, ac: Aircraft, rho = RHO_SEA_LEVEL): number {
  return dynamicPressure(rho, V) * ac.wingArea * liftCoefficient(alpha, ac);
}

export function dragForce(V: number, alpha: number, ac: Aircraft, rho = RHO_SEA_LEVEL): number {
  const cl = liftCoefficient(alpha, ac);
  return dynamicPressure(rho, V) * ac.wingArea * dragCoefficient(cl, ac);
}

/** Linear throttle-to-thrust map, throttle clamped to [0, 1]. */
export function thrustForce(throttle: number, ac: Aircraft): number {
  return Math.min(Math.max(throttle, 0.0), 1.0) * ac.thrustMax;
}

// ---------------------------------------------------------------------------
// Stall boundary (scripts/validate_physics.py + aeroguard_dataset/events.py)
// ---------------------------------------------------------------------------

export interface StallBoundary {
  /** rad; the alpha at which the model's own CL(alpha) curve peaks. */
  alphaAtClPeak: number;
  clMax: number;
  /** m/s; 1g level-flight stall speed from this model's own CLmax. */
  vStall: number;
}

/**
 * Numerically locate CLmax by direct sampling of the real CL(alpha) curve --
 * the model is treated as a black box, exactly as validate_physics.cl_max_of
 * does (same 0-40 deg range, same 2000 samples, same argmax).
 */
export function clMaxOf(ac: Aircraft, rangeDeg: [number, number] = [0.0, 40.0], n = 2000) {
  const [loDeg, hiDeg] = rangeDeg;
  let bestCl = -Infinity;
  let bestAlpha = 0.0;
  for (let i = 0; i < n; i++) {
    // np.linspace(lo, hi, n) endpoints included
    const alphaDeg = loDeg + ((hiDeg - loDeg) * i) / (n - 1);
    const alpha = (alphaDeg * Math.PI) / 180.0;
    const cl = liftCoefficient(alpha, ac);
    if (cl > bestCl) {
      bestCl = cl;
      bestAlpha = alpha;
    }
  }
  return { clMax: bestCl, alphaAtClMax: bestAlpha };
}

/** V_stall = sqrt(2*m*g / (rho*S*CLmax)). */
export function stallSpeed(ac: Aircraft, clMax: number, rho = RHO_SEA_LEVEL): number {
  return Math.sqrt((2.0 * ac.mass * G) / (rho * ac.wingArea * clMax));
}

export function resolveStallBoundary(ac: Aircraft, rho = RHO_SEA_LEVEL): StallBoundary {
  const { clMax, alphaAtClMax } = clMaxOf(ac);
  return { alphaAtClPeak: alphaAtClMax, clMax, vStall: stallSpeed(ac, clMax, rho) };
}

// ---------------------------------------------------------------------------
// Equations of motion (aeroguard/dynamics.py)
// ---------------------------------------------------------------------------

/** state = [V, gamma, theta, h, q] */
export type State = [number, number, number, number, number];

export interface Controls {
  throttle: number; // [0, 1]
  elevator: number; // rad
}

export function alphaOf(state: State): number {
  return state[2] - state[1]; // theta - gamma
}

export function equationsOfMotion(
  _t: number,
  state: State,
  controls: Controls,
  ac: Aircraft,
  rho = RHO_SEA_LEVEL,
): State {
  const [V, gamma, theta, , q] = state;
  const alpha = theta - gamma;
  const m = ac.mass;

  const T = thrustForce(controls.throttle, ac);
  const L = liftForce(V, alpha, ac, rho);
  const D = dragForce(V, alpha, ac, rho);

  const dV = (T * Math.cos(alpha) - D - m * G * Math.sin(gamma)) / m;

  const Vsafe = Math.max(V, 1e-3);
  const dGamma = (L + T * Math.sin(alpha) - m * G * Math.cos(gamma)) / (m * Vsafe);

  const dh = V * Math.sin(gamma);
  const dTheta = q;

  // Iyy * dq/dt = M_elevator*delta_e - M_q*q - M_alpha*alpha
  const M =
    ac.elevatorEffectiveness * controls.elevator - ac.pitchDamping * q - ac.alphaStiffness * alpha;
  const dq = M / ac.Iyy;

  return [dV, dGamma, dTheta, dh, dq];
}

// ---------------------------------------------------------------------------
// Integrator (aeroguard/integrator.py)
// ---------------------------------------------------------------------------

type Rhs = (t: number, y: State) => State;

export function rk4Step(f: Rhs, t: number, y: State, dt: number): State {
  const k1 = f(t, y);
  const y2 = add(y, scale(k1, dt / 2));
  const k2 = f(t + dt / 2, y2);
  const y3 = add(y, scale(k2, dt / 2));
  const k3 = f(t + dt / 2, y3);
  const y4 = add(y, scale(k3, dt));
  const k4 = f(t + dt, y4);

  const out = new Array(5) as State;
  for (let i = 0; i < 5; i++) {
    out[i] = y[i] + (dt / 6) * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]);
  }
  return out;
}

function add(a: State, b: State): State {
  return [a[0] + b[0], a[1] + b[1], a[2] + b[2], a[3] + b[3], a[4] + b[4]];
}
function scale(a: State, s: number): State {
  return [a[0] * s, a[1] * s, a[2] * s, a[3] * s, a[4] * s];
}

// ---------------------------------------------------------------------------
// Trim solver (scripts/simulate.py)
// ---------------------------------------------------------------------------

const TRIM_ALPHA_LOWER_BOUND_DEG = 20.0;

export class TrimError extends Error {}

/**
 * Deterministic bisection, ported from simulate._bisect_root. Requires the
 * bracket to straddle a sign change; throws rather than guessing if it does not.
 */
export function bisectRoot(
  f: (x: number) => number,
  lo: number,
  hi: number,
  tol = 1e-12,
  maxIter = 200,
): number {
  let fLo = f(lo);
  const fHi = f(hi);
  if (fLo === 0.0) return lo;
  if (fHi === 0.0) return hi;
  if (Math.sign(fLo) === Math.sign(fHi)) {
    throw new TrimError(
      `trim bracket [${((lo * 180) / Math.PI).toFixed(2)}, ${((hi * 180) / Math.PI).toFixed(2)}] deg ` +
        `does not straddle a root`,
    );
  }

  for (let i = 0; i < maxIter; i++) {
    const mid = 0.5 * (lo + hi);
    const fMid = f(mid);
    if (fMid === 0.0 || hi - lo < tol) return mid;
    if (Math.sign(fMid) === Math.sign(fLo)) {
      lo = mid;
      fLo = fMid;
    } else {
      hi = mid;
    }
  }
  return 0.5 * (lo + hi);
}

/**
 * Level-flight (gamma=0) force-balance residual in alpha alone:
 *     L(alpha) + D(alpha)*tan(alpha) - m*g = 0
 * An exact combination of dV/dt=0 and dgamma/dt=0 (the thrust vector's
 * vertical component is folded in via D*tan(alpha)) -- not an L=W assumption,
 * and it uses the real nonlinear lift/drag, not a linear approximation.
 */
function levelFlightResidual(alpha: number, V0: number, ac: Aircraft, rho: number): number {
  const L = liftForce(V0, alpha, ac, rho);
  const D = dragForce(V0, alpha, ac, rho);
  return L + D * Math.tan(alpha) - ac.mass * G;
}

export interface Trim {
  alpha: number; // rad
  throttle: number; // [0, 1]
  elevator: number; // rad
  /** true if the required thrust exceeded thrustMax and throttle was clamped. */
  throttleSaturated: boolean;
}

/**
 * Numerically-exact trim alpha / throttle / elevator for steady level flight,
 * solved against the actual nonlinear aero model.
 *
 * The bracket's upper edge is capped at alphaStall for the reason documented at
 * length in simulate.trim_level_flight: the residual is non-monotonic past the
 * CL peak and has a second "back side of the power curve" root above it. Since
 * CL(alpha) has a single peak exactly at alphaStall, capping there provably
 * excludes that undesired root.
 *
 * Throws TrimError when no level-flight trim exists (V0 at or below stall speed).
 */
export function trimLevelFlight(ac: Aircraft, V0: number, rho = RHO_SEA_LEVEL): Trim {
  const lo = (-TRIM_ALPHA_LOWER_BOUND_DEG * Math.PI) / 180.0;
  const hi = ac.alphaStall;

  const alphaTrim = bisectRoot((a) => levelFlightResidual(a, V0, ac, rho), lo, hi);

  const Dtrim = dragForce(V0, alphaTrim, ac, rho);
  const throttleRaw = Dtrim / (ac.thrustMax * Math.cos(alphaTrim));
  const throttle = Math.min(Math.max(throttleRaw, 0.0), 1.0);

  const elevator = (ac.alphaStiffness * alphaTrim) / ac.elevatorEffectiveness;

  return { alpha: alphaTrim, throttle, elevator, throttleSaturated: throttleRaw > 1.0 };
}

// ---------------------------------------------------------------------------
// Control profile (aeroguard_dataset/control_profiles.py)
// ---------------------------------------------------------------------------

/** Cubic Hermite smoothstep, clamped to [0, 1]. C1-continuous at both edges. */
export function smoothstep(x: number): number {
  if (x <= 0.0) return 0.0;
  if (x >= 1.0) return 1.0;
  return x * x * (3.0 - 2.0 * x);
}

export interface Pulse {
  start: number;
  rise: number;
  hold: number;
  fall: number;
  magnitude: number;
}

/** Smooth trapezoid pulse, added on top of trim -- never replacing it. */
export function pulseValueAt(p: Pulse, t: number): number {
  if (t < p.start) return 0.0;
  const endRise = p.start + p.rise;
  if (t < endRise) {
    const frac = p.rise > 0 ? (t - p.start) / p.rise : 1.0;
    return p.magnitude * smoothstep(frac);
  }
  const endHold = endRise + p.hold;
  if (t < endHold) return p.magnitude;
  const endFall = endHold + p.fall;
  if (t < endFall) {
    const frac = p.fall > 0 ? (t - endHold) / p.fall : 1.0;
    return p.magnitude * (1.0 - smoothstep(frac));
  }
  return 0.0;
}
