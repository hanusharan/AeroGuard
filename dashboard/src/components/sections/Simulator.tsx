import { useMemo, useState } from "react";
import {
  Area,
  ComposedChart,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Reveal } from "../ui/Reveal";
import { Section, SectionTitle, GlassPanel, SourceNote, Pill } from "../ui/Primitives";
import {
  DEFAULT_AIRCRAFT,
  DEFAULT_SCENARIO,
  DEG,
  RAD,
  TERMINATION_LABELS,
  runSimulation,
  thin,
  type Scenario,
} from "../../lib/stallSim";
import type { Aircraft } from "../../lib/physics";

const AXIS_TICK = { fill: "#5b6672", fontSize: 10 };
const AXIS_STROKE = "rgba(255,255,255,0.12)";
const TOOLTIP_STYLE = {
  background: "#0a0e15",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 8,
  fontSize: 11,
  fontFamily: "var(--font-mono)",
};

interface Preset {
  name: string;
  blurb: string;
  aircraft: Aircraft;
  scenario: Scenario;
}

const PRESETS: Preset[] = [
  {
    name: "Generic trainer",
    blurb: "The project's stock airframe, eased into a v0.3-style slow approach.",
    aircraft: DEFAULT_AIRCRAFT,
    scenario: DEFAULT_SCENARIO,
  },
  {
    name: "Heavy, small wing",
    blurb: "Higher wing loading — a much higher stall speed, and less room to play with.",
    aircraft: { ...DEFAULT_AIRCRAFT, mass: 1850, wingArea: 12.4, thrustMax: 3300 },
    scenario: {
      ...DEFAULT_SCENARIO,
      v0: 50,
      pull: { start: 2.0, rise: 4.5, hold: 1.5, fall: 3.0, magnitude: 0.07 },
    },
  },
  {
    name: "Light, big wing",
    blurb: "Low wing loading and a gentler stall break — a far lower stall speed.",
    aircraft: {
      ...DEFAULT_AIRCRAFT,
      mass: 980,
      wingArea: 19.0,
      CL0: 0.35,
      CLalpha: 4.9,
      alphaStall: 13.5 * RAD,
      stallTransitionRate: 14.0,
      postStallDecayRate: 2.1,
    },
    scenario: {
      ...DEFAULT_SCENARIO,
      v0: 36,
      pull: { start: 2.0, rise: 2.5, hold: 0.0, fall: 3.0, magnitude: 0.11 },
    },
  },
  {
    name: "Abrupt pull",
    blurb: "Same airframe, snatched instead of eased — watch the lead time collapse.",
    aircraft: DEFAULT_AIRCRAFT,
    scenario: {
      ...DEFAULT_SCENARIO,
      v0: 45,
      pull: { start: 2.0, rise: 0.4, hold: 1.0, fall: 1.0, magnitude: 0.2 },
    },
  },
];

export function Simulator() {
  const [aircraft, setAircraft] = useState<Aircraft>(PRESETS[0].aircraft);
  const [scenario, setScenario] = useState<Scenario>(PRESETS[0].scenario);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [activePreset, setActivePreset] = useState(0);

  const result = useMemo(() => runSimulation(aircraft, scenario), [aircraft, scenario]);

  const setAc = (patch: Partial<Aircraft>) => {
    setAircraft((a) => ({ ...a, ...patch }));
    setActivePreset(-1);
  };
  const setSc = (patch: Partial<Scenario>) => {
    setScenario((s) => ({ ...s, ...patch }));
    setActivePreset(-1);
  };
  const setPull = (patch: Partial<Scenario["pull"]>) => {
    setScenario((s) => ({ ...s, pull: { ...s.pull, ...patch } }));
    setActivePreset(-1);
  };
  const applyPreset = (i: number) => {
    setAircraft(PRESETS[i].aircraft);
    setScenario(PRESETS[i].scenario);
    setActivePreset(i);
  };

  return (
    <Section id="simulator">
      <SectionTitle
        kicker="07 — Stall Simulator"
        title="Enter an airframe. Find out where its stall warning belongs."
        lede={
          <>
            Type in a mass, a wing area, a lift curve, and a maneuver. The simulator runs the same
            five-state RK4 flight model and the same nonlinear CL(α) stall boundary that generated
            this project's datasets — ported to run live in your browser — and reports the angle of
            attack, airspeed, and moment at which the stall warning should fire.
          </>
        }
      />

      <div className="grid gap-5 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
        {/* ------------------------------ inputs ------------------------------ */}
        <Reveal>
          <GlassPanel className="p-5 sm:p-6">
            <FieldGroup label="Presets">
              <div className="grid grid-cols-2 gap-2">
                {PRESETS.map((p, i) => (
                  <button
                    key={p.name}
                    onClick={() => applyPreset(i)}
                    title={p.blurb}
                    className={
                      "rounded-lg border px-2.5 py-2 text-left font-mono-tab text-[10px] uppercase leading-tight tracking-[0.08em] transition-colors " +
                      (activePreset === i
                        ? "border-(--color-signal)/50 bg-(--color-signal)/10 text-(--color-signal)"
                        : "border-(--color-line) bg-white/[0.02] text-(--color-ink-soft) hover:border-(--color-line-strong) hover:text-(--color-ink)")
                    }
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </FieldGroup>

            <FieldGroup label="Airframe">
              <Field
                label="Mass"
                unit="kg"
                value={aircraft.mass}
                min={400}
                max={4000}
                step={10}
                onChange={(v) => setAc({ mass: v })}
              />
              <Field
                label="Wing area"
                unit="m²"
                value={aircraft.wingArea}
                min={6}
                max={40}
                step={0.1}
                decimals={1}
                onChange={(v) => setAc({ wingArea: v })}
              />
              <Field
                label="Max thrust"
                unit="N"
                value={aircraft.thrustMax}
                min={500}
                max={8000}
                step={50}
                onChange={(v) => setAc({ thrustMax: v })}
              />
            </FieldGroup>

            <FieldGroup label="Lift curve">
              <Field
                label="Critical AoA"
                unit="deg"
                value={aircraft.alphaStall * DEG}
                min={8}
                max={24}
                step={0.1}
                decimals={1}
                onChange={(v) => setAc({ alphaStall: v * RAD })}
              />
              <Field
                label="Lift slope CL_α"
                unit="1/rad"
                value={aircraft.CLalpha}
                min={3}
                max={7}
                step={0.05}
                decimals={2}
                onChange={(v) => setAc({ CLalpha: v })}
              />
              <Field
                label="Zero-α lift CL₀"
                unit=""
                value={aircraft.CL0}
                min={-0.2}
                max={0.8}
                step={0.01}
                decimals={2}
                onChange={(v) => setAc({ CL0: v })}
              />
            </FieldGroup>

            <FieldGroup label="Flight setup">
              <Field
                label="Entry airspeed"
                unit="m/s"
                value={scenario.v0}
                min={20}
                max={110}
                step={0.5}
                decimals={1}
                onChange={(v) => setSc({ v0: v })}
              />
              <Field
                label="Altitude"
                unit="m"
                value={scenario.h0}
                min={100}
                max={4000}
                step={50}
                onChange={(v) => setSc({ h0: v })}
              />
              <Field
                label="Air density"
                unit="kg/m³"
                value={scenario.rho}
                min={0.6}
                max={1.3}
                step={0.005}
                decimals={3}
                onChange={(v) => setSc({ rho: v })}
              />
            </FieldGroup>

            <FieldGroup label="Pitch-up maneuver">
              <Field
                label="Elevator pull"
                unit="deg"
                value={scenario.pull.magnitude * DEG}
                min={0}
                max={25}
                step={0.1}
                decimals={1}
                onChange={(v) => setPull({ magnitude: v * RAD })}
              />
              <Field
                label="Rise time"
                unit="s"
                value={scenario.pull.rise}
                min={0.1}
                max={8}
                step={0.1}
                decimals={1}
                onChange={(v) => setPull({ rise: v })}
              />
              <Field
                label="Hold"
                unit="s"
                value={scenario.pull.hold}
                min={0}
                max={8}
                step={0.1}
                decimals={1}
                onChange={(v) => setPull({ hold: v })}
              />
              <Field
                label="Release time"
                unit="s"
                value={scenario.pull.fall}
                min={0.1}
                max={8}
                step={0.1}
                decimals={1}
                onChange={(v) => setPull({ fall: v })}
              />
            </FieldGroup>

            <FieldGroup label="Warning policy">
              <Field
                label="AoA warning margin"
                unit="deg"
                value={scenario.warningMarginRad * DEG}
                min={0.5}
                max={10}
                step={0.1}
                decimals={1}
                onChange={(v) => setSc({ warningMarginRad: v * RAD })}
              />
              <Field
                label="Target lead time"
                unit="s"
                value={scenario.targetLeadTimeS}
                min={1}
                max={10}
                step={0.1}
                decimals={1}
                onChange={(v) => setSc({ targetLeadTimeS: v })}
              />
            </FieldGroup>

            <button
              onClick={() => setShowAdvanced((s) => !s)}
              className="mt-5 w-full rounded-lg border border-(--color-line) bg-white/[0.02] px-3 py-2 font-mono-tab text-[10px] uppercase tracking-[0.14em] text-(--color-ink-soft) transition-colors hover:border-(--color-line-strong) hover:text-(--color-ink)"
            >
              {showAdvanced ? "− Hide" : "+ Show"} drag & pitch-response terms
            </button>

            {showAdvanced && (
              <>
                <FieldGroup label="Drag polar">
                  <Field
                    label="Zero-lift drag CD₀"
                    unit=""
                    value={aircraft.CD0}
                    min={0.01}
                    max={0.09}
                    step={0.001}
                    decimals={3}
                    onChange={(v) => setAc({ CD0: v })}
                  />
                  <Field
                    label="Induced-drag k"
                    unit=""
                    value={aircraft.k}
                    min={0.01}
                    max={0.12}
                    step={0.001}
                    decimals={3}
                    onChange={(v) => setAc({ k: v })}
                  />
                </FieldGroup>

                <FieldGroup label="Stall shape">
                  <Field
                    label="Break sharpness"
                    unit=""
                    value={aircraft.stallTransitionRate}
                    min={5}
                    max={45}
                    step={0.5}
                    decimals={1}
                    onChange={(v) => setAc({ stallTransitionRate: v })}
                  />
                  <Field
                    label="Post-stall decay"
                    unit="1/rad"
                    value={aircraft.postStallDecayRate}
                    min={0.5}
                    max={8}
                    step={0.1}
                    decimals={1}
                    onChange={(v) => setAc({ postStallDecayRate: v })}
                  />
                </FieldGroup>

                <FieldGroup label="Pitch response">
                  <Field
                    label="Pitch inertia Iyy"
                    unit="kg·m²"
                    value={aircraft.Iyy}
                    min={300}
                    max={5000}
                    step={25}
                    onChange={(v) => setAc({ Iyy: v })}
                  />
                  <Field
                    label="Elevator power"
                    unit="×10³"
                    value={aircraft.elevatorEffectiveness / 1e3}
                    min={5}
                    max={80}
                    step={0.5}
                    decimals={1}
                    onChange={(v) => setAc({ elevatorEffectiveness: v * 1e3 })}
                  />
                  <Field
                    label="Pitch damping"
                    unit="×10³"
                    value={aircraft.pitchDamping / 1e3}
                    min={1}
                    max={20}
                    step={0.25}
                    decimals={2}
                    onChange={(v) => setAc({ pitchDamping: v * 1e3 })}
                  />
                  <Field
                    label="α stiffness"
                    unit="×10³"
                    value={aircraft.alphaStiffness / 1e3}
                    min={1}
                    max={30}
                    step={0.25}
                    decimals={2}
                    onChange={(v) => setAc({ alphaStiffness: v * 1e3 })}
                  />
                </FieldGroup>
              </>
            )}
          </GlassPanel>
        </Reveal>

        {/* ------------------------------ results ------------------------------ */}
        <Reveal delay={0.08}>
          {result.ok ? <Results result={result} /> : <Failure result={result} />}
        </Reveal>
      </div>

      <SourceNote>
        Live integration of the project's own physics engine (aeroguard/aerodynamics.py,
        dynamics.py, integrator.py and the scripts/simulate.py trim solver), ported to TypeScript
        and verified against the Python original to a relative difference below 1e-13 across three
        airframes and full 20s trajectories (dashboard/parity/). No ML model runs here — the two
        warning triggers below are explicit engineering rules applied to the simulated physics, not
        the trained model's output. As everywhere else in this project: a simplified, educational
        model of a generic aircraft, not a validated model of any real airframe.
      </SourceNote>
    </Section>
  );
}

/* ------------------------------------------------------------------ results */

function Results({ result }: { result: Extract<ReturnType<typeof runSimulation>, { ok: true }> }) {
  const {
    boundary,
    trim,
    samples,
    crossing,
    recommended,
    marginWarning,
    predictiveWarning,
    warningAlphaDeg,
    warningSpeed,
    warningSpeedRatio,
    minStallMarginDeg,
    peakAlphaDeg,
    termination,
    clCurve,
    scenario,
  } = result;

  const alphaCritDeg = boundary.alphaAtClPeak * DEG;
  const chartData = thin(samples, 420);
  const tMax = samples.length ? samples[samples.length - 1].t : scenario.durationS;
  const alphaTop = Math.max(alphaCritDeg + 4, peakAlphaDeg + 2);

  return (
    <div className="flex flex-col gap-5">
      {/* verdict */}
      <GlassPanel raised className="p-6 sm:p-7">
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-mono-tab text-[11px] uppercase tracking-[0.2em] text-(--color-ink-faint)">
            Where the stall warning belongs
          </span>
          {crossing ? (
            <Pill tone="critical">Stall reached at t = {crossing.t.toFixed(2)}s</Pill>
          ) : (
            <Pill tone="safe">Boundary never reached</Pill>
          )}
        </div>

        {recommended ? (
          <>
            <p className="mt-4 text-2xl leading-snug font-semibold tracking-tight text-(--color-ink) sm:text-[28px]">
              Warn at{" "}
              <span className="text-(--color-caution)">{recommended.alphaDeg.toFixed(1)}° AoA</span>
              {" — "}
              <span className="text-(--color-caution)">{recommended.V.toFixed(1)} m/s</span>, at{" "}
              <span className="text-(--color-caution)">t = {recommended.t.toFixed(2)}s</span>.
            </p>
            <p className="mt-3 text-[15px] leading-relaxed text-(--color-ink-soft)">
              {recommended.leadTimeS !== null ? (
                <>
                  That gives the pilot{" "}
                  <strong className="font-semibold text-(--color-signal)">
                    {recommended.leadTimeS.toFixed(2)}s
                  </strong>{" "}
                  of lead before this aircraft crosses its stall boundary at{" "}
                  {alphaCritDeg.toFixed(1)}°. Triggered by the{" "}
                  {recommended.source === "margin"
                    ? "fixed angle-of-attack margin"
                    : "rate-based projection"}
                  , which fired first.
                </>
              ) : (
                <>
                  The maneuver never actually reaches the boundary — closest approach was{" "}
                  {minStallMarginDeg.toFixed(1)}° of margin — so this is a precautionary alert with
                  no stall behind it.
                  {termination !== "completed" && (
                    <> {TERMINATION_LABELS[termination]}, so there may be more to this story than the run shows.</>
                  )}
                </>
              )}
            </p>
          </>
        ) : (
          <p className="mt-4 text-xl leading-snug font-semibold text-(--color-ink)">
            No warning fires. The flight stays {minStallMarginDeg.toFixed(1)}° clear of the stall
            boundary the whole time, never closing to within the{" "}
            {(scenario.warningMarginRad * DEG).toFixed(1)}° warning margin.
          </p>
        )}

        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Critical AoA" value={alphaCritDeg.toFixed(2)} unit="deg" />
          <Stat label="CL max" value={boundary.clMax.toFixed(3)} unit="" />
          <Stat label="Stall speed (1g)" value={boundary.vStall.toFixed(1)} unit="m/s" />
          <Stat
            label="Warning speed"
            value={Number.isFinite(warningSpeed) ? warningSpeed.toFixed(1) : "—"}
            unit="m/s"
            accent
          />
        </div>
        <p className="mt-3 font-mono-tab text-[11px] leading-relaxed text-(--color-ink-faint)">
          Warning speed is the level-flight airspeed that requires exactly {warningAlphaDeg.toFixed(1)}°
          of AoA — {warningSpeedRatio.toFixed(2)} × the 1g stall speed. Fly slower than that in level
          flight and you are inside the warning band.
        </p>
      </GlassPanel>

      {/* the two triggers */}
      <div className="grid gap-5 sm:grid-cols-2">
        <TriggerCard
          title="Fixed AoA margin"
          rule={`Fire when AoA reaches ${warningAlphaDeg.toFixed(1)}° (${(scenario.warningMarginRad * DEG).toFixed(1)}° short of critical)`}
          note="Ignores how fast the aircraft is getting there, so a slow drift warns early and a snatch warns late."
          point={marginWarning}
          highlight={recommended?.source === "margin"}
        />
        <TriggerCard
          title="Rate-based projection"
          rule={`Fire when AoA is closing fast enough to reach critical within ${scenario.targetLeadTimeS.toFixed(1)}s`}
          note="Projects the current rate of change forward, so an easing pull buys more lead than the target and a tightening one buys less."
          point={predictiveWarning}
          highlight={recommended?.source === "predictive"}
        />
      </div>

      {/* alpha vs time */}
      <GlassPanel className="p-5 sm:p-6">
        <div className="flex items-baseline justify-between">
          <span className="font-mono-tab text-[11px] uppercase tracking-[0.18em] text-(--color-ink-faint)">
            Angle of attack vs. time
          </span>
          <span className="font-mono-tab text-[11px] text-(--color-ink-faint)">
            trim α {(trim.alpha * DEG).toFixed(1)}° · throttle {(trim.throttle * 100).toFixed(0)}%
          </span>
        </div>
        <div className="mt-4 h-64 sm:h-72">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
              <defs>
                <linearGradient id="simAlphaFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#4fd6ff" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#4fd6ff" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="t"
                type="number"
                domain={[0, tMax]}
                tick={AXIS_TICK}
                tickFormatter={(v) => `${v}s`}
                stroke={AXIS_STROKE}
              />
              <YAxis
                domain={[Math.min(0, Math.floor(trim.alpha * DEG) - 2), Math.ceil(alphaTop)]}
                tick={AXIS_TICK}
                tickFormatter={(v) => `${v}°`}
                stroke={AXIS_STROKE}
                width={36}
              />
              <ReferenceArea
                y1={warningAlphaDeg}
                y2={alphaCritDeg}
                fill="#fbbf42"
                fillOpacity={0.09}
                stroke="none"
              />
              <ReferenceLine
                y={alphaCritDeg}
                stroke="#ff5f56"
                strokeDasharray="3 6"
                strokeOpacity={0.75}
                label={{
                  value: "STALL BOUNDARY",
                  position: "insideTopRight",
                  fill: "#ff8a82",
                  fontSize: 10,
                  fontFamily: "var(--font-mono)",
                }}
              />
              <ReferenceLine
                y={warningAlphaDeg}
                stroke="#fbbf42"
                strokeDasharray="2 5"
                strokeOpacity={0.7}
                label={{
                  value: "WARNING AoA",
                  position: "insideBottomRight",
                  fill: "#fbbf42",
                  fontSize: 10,
                  fontFamily: "var(--font-mono)",
                }}
              />
              {recommended && (
                <ReferenceLine
                  x={recommended.t}
                  stroke="#fbbf42"
                  strokeDasharray="2 4"
                  strokeOpacity={0.9}
                  label={{
                    value: "WARN",
                    position: "top",
                    fill: "#fbbf42",
                    fontSize: 10,
                    fontFamily: "var(--font-mono)",
                  }}
                />
              )}
              {crossing && (
                <ReferenceLine
                  x={crossing.t}
                  stroke="#ff5f56"
                  strokeDasharray="2 4"
                  strokeOpacity={0.9}
                  label={{
                    value: "STALL",
                    position: "top",
                    fill: "#ff8a82",
                    fontSize: 10,
                    fontFamily: "var(--font-mono)",
                  }}
                />
              )}
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                labelFormatter={(v) => `t = ${Number(v).toFixed(2)}s`}
                formatter={(v, n) => [
                  `${Number(v).toFixed(2)}°`,
                  n === "alphaDeg" ? "AoA" : "elevator",
                ]}
              />
              <Area
                type="monotone"
                dataKey="alphaDeg"
                stroke="#4fd6ff"
                strokeWidth={2}
                fill="url(#simAlphaFill)"
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="elevatorDeg"
                stroke="#9aa7b5"
                strokeWidth={1.25}
                strokeDasharray="4 4"
                dot={false}
                isAnimationActive={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <SourceNote>
          Solid = angle of attack, dashed grey = elevator deflection. Shaded band = the warning
          zone. {TERMINATION_LABELS[termination]}.
        </SourceNote>
      </GlassPanel>

      {/* CL curve */}
      <GlassPanel className="p-5 sm:p-6">
        <span className="font-mono-tab text-[11px] uppercase tracking-[0.18em] text-(--color-ink-faint)">
          This airframe's lift curve
        </span>
        <div className="mt-4 h-52">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={clCurve} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
              <XAxis
                dataKey="alphaDeg"
                type="number"
                domain={[-4, 30]}
                tick={AXIS_TICK}
                tickFormatter={(v) => `${v}°`}
                stroke={AXIS_STROKE}
              />
              <YAxis tick={AXIS_TICK} stroke={AXIS_STROKE} width={36} />
              <ReferenceArea
                x1={warningAlphaDeg}
                x2={alphaCritDeg}
                fill="#fbbf42"
                fillOpacity={0.09}
                stroke="none"
              />
              <ReferenceLine
                x={alphaCritDeg}
                stroke="#ff5f56"
                strokeDasharray="3 6"
                strokeOpacity={0.75}
                label={{
                  value: "CL PEAK",
                  position: "top",
                  fill: "#ff8a82",
                  fontSize: 10,
                  fontFamily: "var(--font-mono)",
                }}
              />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                labelFormatter={(v) => `α = ${Number(v).toFixed(2)}°`}
                formatter={(v) => [Number(v).toFixed(3), "CL"]}
              />
              <Line
                type="monotone"
                dataKey="cl"
                stroke="#4fd6ff"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <SourceNote>
          The stall boundary is not a threshold anyone typed in — it is the peak of this curve,
          located numerically at {alphaCritDeg.toFixed(2)}°, exactly as
          aeroguard_dataset/events.py does it.
        </SourceNote>
      </GlassPanel>
    </div>
  );
}

function Failure({ result }: { result: Extract<ReturnType<typeof runSimulation>, { ok: false }> }) {
  return (
    <GlassPanel raised className="flex h-full flex-col justify-center p-8">
      <Pill tone="critical">No solution</Pill>
      <p className="mt-4 text-xl leading-snug font-semibold text-(--color-ink)">{result.reason}</p>
      <p className="mt-4 text-sm leading-relaxed text-(--color-ink-soft)">
        The trim solver refuses to guess rather than returning a wrong equilibrium: below the stall
        speed there is no angle of attack at which lift and drag balance weight in level flight.
      </p>
      <div className="mt-6 grid grid-cols-2 gap-3">
        <Stat label="Critical AoA" value={(result.boundary.alphaAtClPeak * DEG).toFixed(2)} unit="deg" />
        <Stat label="Stall speed (1g)" value={result.boundary.vStall.toFixed(1)} unit="m/s" accent />
      </div>
    </GlassPanel>
  );
}

function TriggerCard({
  title,
  rule,
  note,
  point,
  highlight,
}: {
  title: string;
  rule: string;
  note: string;
  point: { t: number; alphaDeg: number; V: number; leadTimeS: number | null } | null;
  highlight?: boolean;
}) {
  return (
    <GlassPanel
      className={
        "p-5 " + (highlight ? "border-(--color-caution)/40 bg-(--color-caution)/[0.06]" : "")
      }
    >
      <div className="flex items-center gap-2">
        <span className="font-mono-tab text-[11px] uppercase tracking-[0.16em] text-(--color-ink)">
          {title}
        </span>
        {highlight && <Pill tone="caution">Fires first</Pill>}
      </div>
      <p className="mt-2 text-[13px] leading-relaxed text-(--color-ink-soft)">{rule}</p>
      <p className="mt-1.5 font-mono-tab text-[10px] leading-relaxed text-(--color-ink-faint)">
        {note}
      </p>
      {point ? (
        <div className="mt-4 grid grid-cols-3 gap-3">
          <Stat label="Time" value={point.t.toFixed(2)} unit="s" />
          <Stat label="AoA" value={point.alphaDeg.toFixed(1)} unit="deg" />
          <Stat
            label="Lead"
            value={point.leadTimeS === null ? "—" : point.leadTimeS.toFixed(2)}
            unit="s"
            accent
          />
        </div>
      ) : (
        <p className="mt-4 font-mono-tab text-[12px] text-(--color-ink-faint)">Never fires.</p>
      )}
    </GlassPanel>
  );
}

function Stat({
  label,
  value,
  unit,
  accent,
}: {
  label: string;
  value: string;
  unit: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded-xl border border-(--color-line) bg-white/[0.02] p-3">
      <div className="font-mono-tab text-[9px] uppercase tracking-[0.1em] text-(--color-ink-faint)">
        {label}
      </div>
      <div
        className={
          "mt-1 font-mono-tab text-lg font-semibold " +
          (accent ? "text-(--color-signal)" : "text-(--color-ink)")
        }
      >
        {value}
        {unit && <span className="ml-1 text-[10px] font-medium text-(--color-ink-soft)">{unit}</span>}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------- inputs */

function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mt-5 first:mt-0">
      <div className="mb-2.5 font-mono-tab text-[10px] uppercase tracking-[0.18em] text-(--color-ink-faint)">
        {label}
      </div>
      <div className="flex flex-col gap-3">{children}</div>
    </div>
  );
}

function Field({
  label,
  unit,
  value,
  min,
  max,
  step,
  decimals = 0,
  onChange,
}: {
  label: string;
  unit: string;
  value: number;
  min: number;
  max: number;
  step: number;
  decimals?: number;
  onChange: (v: number) => void;
}) {
  const commit = (raw: string) => {
    const n = Number(raw);
    if (Number.isFinite(n)) onChange(Math.min(Math.max(n, min), max));
  };

  return (
    <label className="block">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[12px] text-(--color-ink-soft)">{label}</span>
        <span className="flex items-baseline gap-1">
          <input
            type="number"
            value={Number(value.toFixed(decimals))}
            min={min}
            max={max}
            step={step}
            onChange={(e) => commit(e.target.value)}
            className="w-[68px] rounded border border-(--color-line) bg-white/[0.04] px-1.5 py-0.5 text-right font-mono-tab text-[12px] text-(--color-ink) outline-none focus:border-(--color-signal)/50"
          />
          {unit && (
            <span className="w-[38px] font-mono-tab text-[10px] text-(--color-ink-faint)">
              {unit}
            </span>
          )}
        </span>
      </div>
      <input
        type="range"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-1.5 h-1 w-full cursor-pointer appearance-none rounded-full bg-white/10 accent-(--color-signal)"
        aria-label={`${label} (${unit})`}
      />
    </label>
  );
}
