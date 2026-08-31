import { AreaChart, Area, ComposedChart, XAxis, YAxis, ReferenceLine, ResponsiveContainer, Tooltip } from "recharts";
import { Reveal } from "../ui/Reveal";
import { Section, SectionTitle, GlassPanel, SourceNote, Pill } from "../ui/Primitives";
import { useScrubber } from "../../hooks/useScrubber";
import flightReplay from "../../data/flightReplay.json";
import type { FlightReplay as FlightReplayT } from "../../types";

const replay = flightReplay as FlightReplayT;
const tMax = replay.points[replay.points.length - 1].t;

export function FlightReplay() {
  const { index, setIndex, playing, togglePlaying } = useScrubber(replay.points.length, 55);
  const current = replay.points[index];
  const data = replay.points.slice(0, index + 1);

  const warningActive = current.t >= replay.firstWarningTimeS;
  const crossed = current.t >= replay.crossingTimeS;

  // Seconds remaining until the boundary; the number the whole result is about.
  const toBoundary = replay.crossingTimeS - current.t;
  // "Approach" begins where alpha has clearly left trim and is climbing — one
  // credited lead time ahead of the first warning, so the phase strip shows the
  // model firing inside a run-up the viewer can already see on the chart.
  const approachStart = Math.max(0, replay.firstWarningTimeS - replay.creditedLeadTimeS);
  const phase: PhaseId = crossed
    ? "stall"
    : warningActive
      ? "warning"
      : current.t >= approachStart
        ? "approach"
        : "normal";

  return (
    <Section id="replay">
      <SectionTitle
        kicker="06 — Interactive Flight Replay"
        title="One real held-out trajectory, scored by the frozen model."
        lede={
          <>
            Play it through the four phases — normal flight, approach, model warning, stall
            boundary — and watch the countdown at the moment the warning fires. Trajectory{" "}
            <code className="font-mono-tab text-(--color-ink)">{replay.trajectoryId}</code> is a v0.3
            TEST-split flight the model never trained on; its model-credited lead time (
            {replay.creditedLeadTimeS.toFixed(2)}s) matches the reported event-level median almost
            exactly, so this is a representative example, not a cherry-picked best case.
          </>
        }
      />

      <Reveal>
        <GlassPanel raised className="p-6 sm:p-8">
          <div className="flex flex-wrap items-center gap-4">
            <button
              onClick={togglePlaying}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-(--color-line-strong) bg-white/[0.05] text-(--color-ink) transition-colors hover:border-(--color-signal)/50 hover:text-(--color-signal)"
              aria-label={playing ? "Pause replay" : "Play replay"}
            >
              {playing ? <PauseIcon /> : <PlayIcon />}
            </button>

            <input
              type="range"
              min={0}
              max={replay.points.length - 1}
              value={index}
              onChange={(e) => setIndex(Number(e.target.value))}
              className="h-1 flex-1 min-w-[140px] cursor-pointer appearance-none rounded-full bg-white/10 accent-(--color-signal)"
              aria-label="Scrub flight replay"
            />

            <span className="font-mono-tab text-sm text-(--color-ink) tabular-nums">
              t = {current.t.toFixed(1)}s / {tMax.toFixed(1)}s
            </span>

            <div className="flex gap-2">
              {warningActive && !crossed && <Pill tone="caution">AI Warning Active</Pill>}
              {crossed && <Pill tone="critical">Boundary Crossed</Pill>}
              {!warningActive && <Pill tone="safe">Nominal</Pill>}
            </div>
          </div>

          <PhaseStrip phase={phase} toBoundary={toBoundary} crossed={crossed} />

          <div className="mt-6 grid gap-5 lg:grid-cols-[1.4fr_1fr]">
            <div className="h-64 sm:h-72">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                  <defs>
                    <linearGradient id="replayAlphaFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#4fd6ff" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#4fd6ff" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="t"
                    type="number"
                    domain={[0, tMax]}
                    tick={{ fill: "#5b6672", fontSize: 10 }}
                    tickFormatter={(v) => `${v}s`}
                    stroke="rgba(255,255,255,0.12)"
                  />
                  <YAxis
                    domain={[0, 18]}
                    tick={{ fill: "#5b6672", fontSize: 10 }}
                    tickFormatter={(v) => `${v}°`}
                    stroke="rgba(255,255,255,0.12)"
                    width={34}
                  />
                  <ReferenceLine
                    y={replay.stallBoundaryDeg}
                    stroke="#ff5f56"
                    strokeDasharray="3 6"
                    strokeOpacity={0.7}
                    label={{ value: "BOUNDARY", position: "insideTopRight", fill: "#ff8a82", fontSize: 10, fontFamily: "var(--font-mono)" }}
                  />
                  <ReferenceLine
                    x={replay.firstWarningTimeS}
                    stroke="#fbbf42"
                    strokeDasharray="2 4"
                    strokeOpacity={0.85}
                    label={{ value: "WARNING", position: "top", fill: "#fbbf42", fontSize: 10, fontFamily: "var(--font-mono)" }}
                  />
                  <Tooltip
                    contentStyle={{ background: "#0a0e15", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, fontSize: 11, fontFamily: "var(--font-mono)" }}
                    labelFormatter={(v) => `t = ${v}s`}
                  />
                  <Area type="monotone" dataKey="alphaDeg" name="alpha (deg)" stroke="#4fd6ff" strokeWidth={2} fill="url(#replayAlphaFill)" isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            <div className="h-64 sm:h-72">
              <div className="mb-1 font-mono-tab text-[11px] uppercase tracking-[0.16em] text-(--color-ink-faint)">
                AI warning probability
              </div>
              <ResponsiveContainer width="100%" height="90%">
                <AreaChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                  <defs>
                    <linearGradient id="probFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#fbbf42" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="#fbbf42" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="t" type="number" domain={[0, tMax]} hide />
                  <YAxis domain={[0, 1]} tick={{ fill: "#5b6672", fontSize: 10 }} stroke="rgba(255,255,255,0.12)" width={30} />
                  <ReferenceLine
                    y={replay.warningThreshold}
                    stroke="#fbbf42"
                    strokeDasharray="3 6"
                    strokeOpacity={0.7}
                    label={{ value: "THRESHOLD", position: "insideBottomRight", fill: "#fbbf42", fontSize: 9, fontFamily: "var(--font-mono)" }}
                  />
                  <Tooltip
                    contentStyle={{ background: "#0a0e15", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, fontSize: 11, fontFamily: "var(--font-mono)" }}
                    labelFormatter={(v) => `t = ${v}s`}
                  />
                  <Area type="monotone" dataKey="warningProbability" stroke="#fbbf42" strokeWidth={2} fill="url(#probFill)" isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
              <div className="text-center font-mono-tab text-3xl font-bold text-(--color-caution) tabular-nums">
                {(current.warningProbability * 100).toFixed(1)}%
              </div>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
            <Readout label="Airspeed" value={current.airspeed.toFixed(1)} unit="m/s" />
            <Readout label="Pitch" value={current.pitchDeg.toFixed(1)} unit="deg" />
            <Readout label="Elevator" value={current.elevatorDeg.toFixed(1)} unit="deg" />
            <Readout label="Flight-Path Angle" value={current.gammaDeg.toFixed(1)} unit="deg" />
            <Readout label="Stall Margin" value={current.stallMarginDeg.toFixed(1)} unit="deg" />
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-6 border-t border-(--color-line) pt-5">
            <Metric label="First warning" value={`t = ${replay.firstWarningTimeS.toFixed(1)}s`} />
            <Metric label="Boundary crossed" value={`t = ${replay.crossingTimeS.toFixed(1)}s`} />
            <Metric label="Credited lead time" value={`${replay.creditedLeadTimeS.toFixed(2)}s`} highlight />
          </div>

          <SourceNote>{replay.source}. Model inference only — the frozen model was not retrained.</SourceNote>
        </GlassPanel>
      </Reveal>
    </Section>
  );
}

type PhaseId = "normal" | "approach" | "warning" | "stall";

const PHASES: { id: PhaseId; label: string; color: string }[] = [
  { id: "normal", label: "Normal flight", color: "var(--color-safe)" },
  { id: "approach", label: "Approach", color: "var(--color-ink-soft)" },
  { id: "warning", label: "Model warning", color: "var(--color-caution)" },
  { id: "stall", label: "Stall boundary", color: "var(--color-critical)" },
];

/**
 * Turns the credited lead time into something the eye reads directly: which of
 * the four phases the flight is in right now, and how many seconds are left
 * before the boundary. The countdown is what makes 4.72s feel like a duration
 * rather than a table cell.
 */
function PhaseStrip({
  phase,
  toBoundary,
  crossed,
}: {
  phase: PhaseId;
  toBoundary: number;
  crossed: boolean;
}) {
  const activeIndex = PHASES.findIndex((p) => p.id === phase);

  return (
    <div className="mt-6 rounded-2xl border border-(--color-line) bg-white/[0.02] p-4 sm:p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 items-center">
          {PHASES.map((p, i) => {
            const active = i === activeIndex;
            const passed = i < activeIndex;
            return (
              <div key={p.id} className="flex flex-1 items-center">
                <div className="flex flex-1 flex-col gap-1.5">
                  <div
                    className="h-[3px] rounded-full transition-colors duration-300"
                    style={{
                      background: active || passed ? p.color : "rgba(255,255,255,0.08)",
                      opacity: passed ? 0.45 : 1,
                    }}
                  />
                  <span
                    className="font-mono-tab text-[9px] uppercase leading-tight tracking-[0.1em] transition-colors duration-300 sm:text-[10px]"
                    style={{
                      color: active ? p.color : "var(--color-ink-faint)",
                      fontWeight: active ? 600 : 400,
                    }}
                  >
                    {p.label}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        <div className="shrink-0 text-right sm:w-[132px]">
          <div className="font-mono-tab text-[9px] uppercase tracking-[0.14em] text-(--color-ink-faint)">
            {crossed ? "Boundary" : "To boundary"}
          </div>
          <div
            className="font-mono-tab text-2xl font-bold tabular-nums"
            style={{ color: crossed ? "var(--color-critical)" : "var(--color-ink)" }}
          >
            {crossed ? "STALL" : `T − ${toBoundary.toFixed(2)}s`}
          </div>
        </div>
      </div>
    </div>
  );
}

function Readout({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div className="rounded-xl border border-(--color-line) bg-white/[0.02] p-3">
      <div className="font-mono-tab text-[9px] uppercase tracking-[0.1em] text-(--color-ink-faint)">{label}</div>
      <div className="mt-1 font-mono-tab text-lg font-semibold text-(--color-ink)">
        {value}
        <span className="ml-1 text-[10px] font-medium text-(--color-ink-soft)">{unit}</span>
      </div>
    </div>
  );
}

function Metric({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div>
      <div className="font-mono-tab text-[10px] uppercase tracking-[0.14em] text-(--color-ink-faint)">{label}</div>
      <div className={"mt-1 font-mono-tab text-xl font-bold " + (highlight ? "text-(--color-signal)" : "text-(--color-ink)")}>
        {value}
      </div>
    </div>
  );
}

function PlayIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
      <path d="M3 1.5L12.5 7L3 12.5V1.5Z" />
    </svg>
  );
}
function PauseIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
      <rect x="2.5" y="1.5" width="3.2" height="11" />
      <rect x="8.3" y="1.5" width="3.2" height="11" />
    </svg>
  );
}
