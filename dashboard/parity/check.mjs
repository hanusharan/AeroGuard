/**
 * Verify that the TypeScript physics port matches the Python engine.
 *
 * Usage (from dashboard/):
 *   ../.venv/bin/python parity/dump_reference.py
 *   node parity/check.mjs
 *
 * Compiles src/lib/physics.ts + src/lib/stallSim.ts to a temp dir with the
 * project's own tsc, runs the same three airframes/scenarios the Python
 * dumper ran, and compares every value against parity/reference.json.
 */

import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");

const outDir = mkdtempSync(join(tmpdir(), "aeroguard-parity-"));
execFileSync(
  join(root, "node_modules/.bin/tsc"),
  [
    join(root, "src/lib/physics.ts"),
    join(root, "src/lib/stallSim.ts"),
    "--outDir", outDir,
    "--module", "esnext",
    "--target", "es2022",
    "--moduleResolution", "bundler",
    "--skipLibCheck",
    "--ignoreConfig",
  ],
  { stdio: "inherit" },
);

const physics = await import(pathToFileURL(join(outDir, "physics.js")).href);
const ref = JSON.parse(readFileSync(join(here, "reference.json"), "utf8"));

const DEG = 180 / Math.PI;
const RAD = Math.PI / 180;

/** Map a Python Aircraft dataclass dict onto the TS Aircraft interface. */
function toTsAircraft(py) {
  return {
    mass: py.mass,
    wingArea: py.wing_area,
    Iyy: py.Iyy,
    CD0: py.CD0,
    k: py.k,
    CL0: py.CL0,
    CLalpha: py.CL_alpha,
    alphaStall: py.alpha_stall,
    stallTransitionRate: py.stall_transition_rate,
    postStallDecayRate: py.post_stall_decay_rate,
    thrustMax: py.thrust_max,
    elevatorEffectiveness: py.elevator_effectiveness,
    pitchDamping: py.pitch_damping,
    alphaStiffness: py.alpha_stiffness,
  };
}

let failures = 0;
let checks = 0;
let worstRel = { label: "", rel: 0 };
let worstAbs = { label: "", abs: 0 };

function cmp(label, got, want, tol = 1e-9) {
  checks++;
  const abs = Math.abs(got - want);
  const denom = Math.max(Math.abs(want), 1e-9);
  const rel = abs / denom;
  // Relative error is meaningless for reference values sitting at ~0 (gamma at
  // trim, for one), so those are judged on absolute difference instead and are
  // excluded from the worst-relative report.
  const nearZero = Math.abs(want) < 1e-9;
  if (rel > worstRel.rel && !nearZero) worstRel = { label, rel };
  if (abs > worstAbs.abs) worstAbs = { label, abs };
  if (!(nearZero ? abs <= 1e-12 : rel <= tol)) {
    failures++;
    console.log(`  FAIL ${label}: ts=${got} py=${want} rel=${rel.toExponential(2)} abs=${abs.toExponential(2)}`);
  }
}

const DT = 0.01;
const DURATION = 20.0;

for (const [name, r] of Object.entries(ref)) {
  console.log(`\n[${name}]`);
  const ac = toTsAircraft(r.aircraft);

  // --- static aero --------------------------------------------------------
  r.alphas_deg.forEach((aDeg, i) => {
    cmp(`CL(${aDeg}deg)`, physics.liftCoefficient(aDeg * RAD, ac), r.cl[i]);
    cmp(
      `CD(${aDeg}deg)`,
      physics.dragCoefficient(physics.liftCoefficient(aDeg * RAD, ac), ac),
      r.cd[i],
    );
  });

  const { clMax, alphaAtClMax } = physics.clMaxOf(ac);
  cmp("CLmax", clMax, r.cl_max);
  cmp("alpha@CLpeak", alphaAtClMax * DEG, r.alpha_at_cl_peak_deg);
  cmp("V_stall", physics.stallSpeed(ac, clMax), r.v_stall);

  const boundary = physics.resolveStallBoundary(ac);
  cmp("boundary alpha", boundary.alphaAtClPeak * DEG, r.boundary_alpha_deg);

  // --- trim ---------------------------------------------------------------
  const trim = physics.trimLevelFlight(ac, r.scenario.v0);
  cmp("trim alpha", trim.alpha * DEG, r.trim.alpha_deg);
  cmp("trim throttle", trim.throttle, r.trim.throttle);
  cmp("trim elevator", trim.elevator * DEG, r.trim.elevator_deg);

  // --- pulse shape --------------------------------------------------------
  const pull = {
    start: r.scenario.pull.start,
    rise: r.scenario.pull.rise,
    hold: r.scenario.pull.hold,
    fall: r.scenario.pull.fall,
    magnitude: r.scenario.pull.magnitude,
  };
  r.pulse.forEach((want, i) => {
    cmp(`pulse(t=${(i * 0.5).toFixed(1)})`, physics.pulseValueAt(pull, i * 0.5), want);
  });

  // --- full 20s RK4 trajectory -------------------------------------------
  const controls = (t) => ({
    throttle: trim.throttle,
    elevator: trim.elevator + physics.pulseValueAt(pull, t),
  });
  const rhs = (t, y) => physics.equationsOfMotion(t, y, controls(t), ac);

  let state = [r.scenario.v0, 0.0, trim.alpha, 1000.0, 0.0];
  const nSteps = Math.round(DURATION / DT);
  const byIndex = new Map(r.trajectory.map((row) => [Math.round(row.t / DT), row]));

  for (let i = 0; i <= nSteps; i++) {
    const t = i * DT;
    const row = byIndex.get(i);
    if (row) {
      const [V, gamma, theta, h, q] = state;
      // Integrated state drifts by float-op ordering, so allow 1e-7 relative
      // after up to 1900 RK4 steps (still ~7 significant figures).
      const tol = 1e-7;
      cmp(`t=${row.t} V`, V, row.V, tol);
      cmp(`t=${row.t} alpha`, (theta - gamma) * DEG, row.alpha_deg, tol);
      cmp(`t=${row.t} gamma`, gamma * DEG, row.gamma_deg, tol);
      cmp(`t=${row.t} theta`, theta * DEG, row.theta_deg, tol);
      cmp(`t=${row.t} h`, h, row.h, tol);
      cmp(`t=${row.t} q`, q * DEG, row.q_deg, tol);
      cmp(`t=${row.t} CL`, physics.liftCoefficient(theta - gamma, ac), row.cl, tol);
    }
    if (i < nSteps) state = physics.rk4Step(rhs, t, state, DT);
  }
}

console.log(
  `\n${checks - failures}/${checks} checks passed\n` +
    `  largest relative difference: ${worstRel.rel.toExponential(2)} (${worstRel.label})\n` +
    `  largest absolute difference: ${worstAbs.abs.toExponential(2)} (${worstAbs.label})`,
);
process.exit(failures === 0 ? 0 : 1);
