/**
 * Stall-warning simulator.
 *
 * Runs the REAL ported physics engine (see ./physics.ts) forward in time for a
 * user-specified airframe and maneuver, then answers the question the dashboard
 * asks: *where should the stall warning be?*
 *
 * Nothing here is a lookup table, a fitted curve, or a replay of stored data.
 * Every number below comes out of the same RK4 integration of the same
 * five-state longitudinal equations of motion that generated the project's
 * datasets, using the same numerically-located CL(alpha)-peak stall boundary
 * (aeroguard_dataset/events.py) and the same causal backward-difference
 * derivatives (aeroguard_dataset/features.py).
 */

import {
  DEFAULT_AIRCRAFT,
  G,
  RHO_SEA_LEVEL,
  TrimError,
  alphaOf,
  equationsOfMotion,
  liftCoefficient,
  liftForce,
  pulseValueAt,
  resolveStallBoundary,
  rk4Step,
  trimLevelFlight,
  type Aircraft,
  type Controls,
  type Pulse,
  type StallBoundary,
  type State,
  type Trim,
} from "./physics";

export const DEG = 180 / Math.PI;
export const RAD = Math.PI / 180;

// Validity envelope, from aeroguard_dataset/config.py (Stage-1 physics findings):
// the model is only trusted above 0.5*V_stall and within |gamma| <= 45 deg.
export const V_FLOOR_FRACTION_OF_VSTALL = 0.5;
export const GAMMA_MAX_DEG = 45.0;

export type Termination = "completed" | "v_floor" | "gamma_envelope" | "ground_contact" | "nan_inf";

export interface Scenario {
  /** Entry airspeed for the level-flight trim [m/s]. */
  v0: number;
  /** Entry altitude [m]. Not fed back into the physics (constant density model). */
  h0: number;
  /** Air density [kg/m^3]. Constant for the whole run, as in the Python model. */
  rho: number;

  /** Pitch-up elevator input added on top of trim: a smooth trapezoid. */
  pull: Pulse;

  durationS: number;
  dt: number;

  /** Warn when the stall margin (alpha_crit - alpha) drops below this [rad]. */
  warningMarginRad: number;
  /** Target warning lead time [s] for the rate-based (predictive) trigger. */
  targetLeadTimeS: number;
}

export const DEFAULT_SCENARIO: Scenario = {
  v0: 42.0,
  h0: 1000.0,
  rho: RHO_SEA_LEVEL,
  // A v0.3-style slow approach: a gentle, sustained pitch-up rather than a
  // snatch. Slow enough that alpha quasi-statically tracks the elevator ramp,
  // which is what produces a multi-second precursor at all. These particular
  // numbers were picked by sweeping the real engine for a run that crosses the
  // boundary cleanly, stays inside the validity envelope for the full 20s, and
  // does not depart so far past the boundary that the approach is unreadable.
  pull: { start: 2.0, rise: 3.0, hold: 0.0, fall: 3.0, magnitude: 0.11 },
  durationS: 20.0,
  dt: 0.01,
  warningMarginRad: 3.0 * RAD,
  targetLeadTimeS: 5.0,
};

export interface Sample {
  t: number;
  V: number;
  alphaDeg: number;
  thetaDeg: number;
  gammaDeg: number;
  qDeg: number;
  h: number;
  elevatorDeg: number;
  cl: number;
  /** alpha_crit - alpha, in degrees (features.py: stall_margin). */
  stallMarginDeg: number;
  /** Causal backward difference d(alpha)/dt [deg/s]; NaN on the first sample. */
  dAlphaDtDeg: number;
  /** Load factor n = L / (m*g). */
  loadFactor: number;
  isUnsafe: boolean;
}

export interface WarningPoint {
  t: number;
  alphaDeg: number;
  V: number;
  /** Airspeed at the trigger as a multiple of the 1g stall speed. */
  vOverVstall: number;
  stallMarginDeg: number;
  loadFactor: number;
  /** Seconds between this trigger and the actual boundary crossing (null if never crossed). */
  leadTimeS: number | null;
}

export interface SimResult {
  ok: true;
  aircraft: Aircraft;
  scenario: Scenario;
  boundary: StallBoundary;
  trim: Trim;
  samples: Sample[];
  termination: Termination;

  /** First sample where |alpha| passes the CL peak, i.e. the stall event. */
  crossing: { t: number; V: number; alphaDeg: number } | null;
  /** Closest the flight ever came to the boundary [deg]. */
  minStallMarginDeg: number;
  peakAlphaDeg: number;

  /** Fixed angle-of-attack trigger: alpha >= alpha_crit - margin. */
  marginWarning: WarningPoint | null;
  /** Rate-based trigger: projected time-to-boundary <= target lead time. */
  predictiveWarning: WarningPoint | null;
  /** Whichever of the two fires first -- the recommended warning point. */
  recommended: (WarningPoint & { source: "margin" | "predictive" }) | null;

  /** Angle of attack of the fixed trigger [deg] -- a property of the airframe alone. */
  warningAlphaDeg: number;
  /**
   * Level-flight airspeed at which the aircraft would be sitting exactly on the
   * fixed AoA trigger: V_warn = sqrt(2mg / (rho*S*CL(alpha_warn))). This is the
   * airspeed-domain answer to "where should the warning be".
   */
  warningSpeed: number;
  warningSpeedRatio: number;

  /** CL(alpha) curve for plotting -- sampled from the real lift model. */
  clCurve: { alphaDeg: number; cl: number }[];
}

export interface SimFailure {
  ok: false;
  reason: string;
  boundary: StallBoundary;
}

/** Build the control law: constant trim throttle, trim elevator + the pull pulse. */
function controlsAt(t: number, trim: Trim, pull: Pulse): Controls {
  return { throttle: trim.throttle, elevator: trim.elevator + pulseValueAt(pull, t) };
}

export function runSimulation(ac: Aircraft, sc: Scenario): SimResult | SimFailure {
  const boundary = resolveStallBoundary(ac, sc.rho);

  let trim: Trim;
  try {
    trim = trimLevelFlight(ac, sc.v0, sc.rho);
  } catch (e) {
    if (e instanceof TrimError) {
      return {
        ok: false,
        boundary,
        reason:
          `No level-flight trim exists at ${sc.v0.toFixed(1)} m/s — this airframe's 1g stall ` +
          `speed is ${boundary.vStall.toFixed(1)} m/s. Raise the entry airspeed, or lower the ` +
          `wing loading (less mass or more wing area).`,
      };
    }
    throw e;
  }

  const vFloor = V_FLOOR_FRACTION_OF_VSTALL * boundary.vStall;
  const gammaMax = GAMMA_MAX_DEG * RAD;

  const theta0 = trim.alpha; // gamma0 = 0
  let state: State = [sc.v0, 0.0, theta0, sc.h0, 0.0];

  const nSteps = Math.round(sc.durationS / sc.dt);
  const samples: Sample[] = [];
  let termination: Termination = "completed";

  const rhs = (t: number, y: State): State =>
    equationsOfMotion(t, y, controlsAt(t, trim, sc.pull), ac, sc.rho);

  for (let i = 0; i <= nSteps; i++) {
    const t = i * sc.dt;

    if (!state.every(Number.isFinite)) {
      termination = "nan_inf";
      break;
    }

    const [V, gamma, theta, h, q] = state;

    // Hard physical impossibility, checked BEFORE recording: the last recorded
    // sample is always the last physically valid (h > 0) one.
    if (h <= 0) {
      termination = "ground_contact";
      break;
    }

    const alpha = alphaOf(state);
    const cl = liftCoefficient(alpha, ac);
    const L = liftForce(V, alpha, ac, sc.rho);
    const elevator = trim.elevator + pulseValueAt(sc.pull, t);

    const prev = samples[samples.length - 1];
    const dAlphaDtDeg =
      prev === undefined ? NaN : (alpha * DEG - prev.alphaDeg) / sc.dt; // causal backward difference

    samples.push({
      t,
      V,
      alphaDeg: alpha * DEG,
      thetaDeg: theta * DEG,
      gammaDeg: gamma * DEG,
      qDeg: q * DEG,
      h,
      elevatorDeg: elevator * DEG,
      cl,
      stallMarginDeg: (boundary.alphaAtClPeak - alpha) * DEG,
      dAlphaDtDeg,
      loadFactor: L / (ac.mass * G),
      isUnsafe: Math.abs(alpha) > boundary.alphaAtClPeak,
    });

    // Soft validity thresholds: the crossing sample itself is informative, so
    // it is recorded first and simulation stops after it.
    if (V < vFloor) {
      termination = "v_floor";
      break;
    }
    if (Math.abs(gamma) > gammaMax) {
      termination = "gamma_envelope";
      break;
    }

    if (i < nSteps) state = rk4Step(rhs, t, state, sc.dt);
  }

  // --- event + warning analysis -------------------------------------------
  const crossIdx = samples.findIndex((s) => s.isUnsafe);
  const crossing =
    crossIdx >= 0
      ? { t: samples[crossIdx].t, V: samples[crossIdx].V, alphaDeg: samples[crossIdx].alphaDeg }
      : null;

  const alphaCritDeg = boundary.alphaAtClPeak * DEG;
  const warningAlphaDeg = alphaCritDeg - sc.warningMarginRad * DEG;

  const toWarning = (s: Sample): WarningPoint => ({
    t: s.t,
    alphaDeg: s.alphaDeg,
    V: s.V,
    vOverVstall: s.V / boundary.vStall,
    stallMarginDeg: s.stallMarginDeg,
    loadFactor: s.loadFactor,
    leadTimeS: crossing ? crossing.t - s.t : null,
  });

  // Trigger 1 — fixed AoA margin: fire as soon as the stall margin closes to
  // within the configured threshold. This is the classic stall-warning logic.
  const marginIdx = samples.findIndex((s) => s.alphaDeg >= warningAlphaDeg);
  const marginWarning = marginIdx >= 0 ? toWarning(samples[marginIdx]) : null;

  // Trigger 2 — rate-based: fire as soon as alpha is closing on the boundary
  // fast enough that, at the current rate, it will reach it within the target
  // lead time. Uses the same causal derivative the ML model is fed, so it can
  // fire far earlier than the fixed threshold during a fast pull, and later
  // during a slow drift.
  const predIdx = samples.findIndex(
    (s) =>
      Number.isFinite(s.dAlphaDtDeg) &&
      s.dAlphaDtDeg > 0 &&
      s.stallMarginDeg > 0 &&
      s.stallMarginDeg / s.dAlphaDtDeg <= sc.targetLeadTimeS,
  );
  const predictiveWarning = predIdx >= 0 ? toWarning(samples[predIdx]) : null;

  let recommended: SimResult["recommended"] = null;
  if (marginWarning && predictiveWarning) {
    recommended =
      predictiveWarning.t <= marginWarning.t
        ? { ...predictiveWarning, source: "predictive" }
        : { ...marginWarning, source: "margin" };
  } else if (marginWarning) {
    recommended = { ...marginWarning, source: "margin" };
  } else if (predictiveWarning) {
    recommended = { ...predictiveWarning, source: "predictive" };
  }

  // Airspeed-domain trigger: the level-flight speed that requires exactly the
  // trigger angle of attack. Below this speed, holding altitude means sitting
  // inside the warning band.
  const clAtWarning = liftCoefficient(warningAlphaDeg * RAD, ac);
  const warningSpeed =
    clAtWarning > 0 ? Math.sqrt((2 * ac.mass * G) / (sc.rho * ac.wingArea * clAtWarning)) : NaN;

  const clCurve: { alphaDeg: number; cl: number }[] = [];
  for (let d = -4; d <= 30; d += 0.25) {
    clCurve.push({ alphaDeg: d, cl: liftCoefficient(d * RAD, ac) });
  }

  const minStallMarginDeg = samples.reduce((m, s) => Math.min(m, s.stallMarginDeg), Infinity);
  const peakAlphaDeg = samples.reduce((m, s) => Math.max(m, s.alphaDeg), -Infinity);

  return {
    ok: true,
    aircraft: ac,
    scenario: sc,
    boundary,
    trim,
    samples,
    termination,
    crossing,
    minStallMarginDeg,
    peakAlphaDeg,
    marginWarning,
    predictiveWarning,
    recommended,
    warningAlphaDeg,
    warningSpeed,
    warningSpeedRatio: warningSpeed / boundary.vStall,
    clCurve,
  };
}

/** Downsample for charting without changing the integration step. */
export function thin<T>(arr: T[], maxPoints = 400): T[] {
  if (arr.length <= maxPoints) return arr;
  const stride = Math.ceil(arr.length / maxPoints);
  const out: T[] = [];
  for (let i = 0; i < arr.length; i += stride) out.push(arr[i]);
  const last = arr[arr.length - 1];
  if (out[out.length - 1] !== last) out.push(last);
  return out;
}

export const TERMINATION_LABELS: Record<Termination, string> = {
  completed: "Ran the full duration",
  v_floor: "Stopped early — airspeed fell below 0.5 × V_stall (outside the model's validity envelope)",
  gamma_envelope: "Stopped early — flight-path angle exceeded ±45° (outside the model's validity envelope)",
  ground_contact: "Stopped early — reached ground level",
  nan_inf: "Stopped early — state became non-finite",
};

export { DEFAULT_AIRCRAFT };
