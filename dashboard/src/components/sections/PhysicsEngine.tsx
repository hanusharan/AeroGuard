import { AreaChart, Area, XAxis, YAxis, ReferenceLine, ResponsiveContainer, Tooltip } from "recharts";
import { Reveal } from "../ui/Reveal";
import { Section, SectionTitle, GlassPanel, SourceNote } from "../ui/Primitives";
import { usePlaybackCursor } from "../../hooks/usePlaybackCursor";
import flightReplay from "../../data/flightReplay.json";
import type { FlightReplay } from "../../types";

const replay = flightReplay as FlightReplay;

const STATE_VARS: { key: keyof (typeof replay.points)[number]; label: string; unit: string }[] = [
  { key: "alphaDeg", label: "Angle of Attack", unit: "deg" },
  { key: "airspeed", label: "Airspeed", unit: "m/s" },
  { key: "pitchDeg", label: "Pitch", unit: "deg" },
  { key: "pitchRateDeg", label: "Pitch Rate", unit: "deg/s" },
  { key: "elevatorDeg", label: "Elevator Input", unit: "deg" },
  { key: "gammaDeg", label: "Flight-Path Angle", unit: "deg" },
];

export function PhysicsEngine() {
  const idx = usePlaybackCursor(replay.points.length, 55, 1100);
  const current = replay.points[idx];
  const chartData = replay.points.slice(0, idx + 1);

  return (
    <Section id="physics">
      <SectionTitle
        kicker="02 — Physics Engine"
        title="A five-state longitudinal flight-dynamics model."
        lede="AeroGuard simulates a fixed-wing aircraft with a nonlinear lift curve that produces stall as an emergent property, not a threshold rule. Every trajectory tracks the same six quantities shown here."
      />

      <div className="grid gap-5 lg:grid-cols-[1.6fr_1fr]">
        <Reveal>
          <GlassPanel className="p-6 sm:p-8">
            <div className="flex items-baseline justify-between">
              <span className="font-mono-tab text-[11px] uppercase tracking-[0.18em] text-(--color-ink-faint)">
                Angle of attack vs. time
              </span>
              <span className="font-mono-tab text-[11px] text-(--color-ink-faint)">
                t = {current.t.toFixed(1)}s
              </span>
            </div>
            <div className="mt-4 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                  <defs>
                    <linearGradient id="alphaFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#4fd6ff" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="#4fd6ff" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="t"
                    type="number"
                    domain={[0, replay.points[replay.points.length - 1].t]}
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
                    label={{
                      value: "STALL BOUNDARY",
                      position: "insideTopRight",
                      fill: "#ff8a82",
                      fontSize: 10,
                      fontFamily: "var(--font-mono)",
                    }}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#0a0e15",
                      border: "1px solid rgba(255,255,255,0.12)",
                      borderRadius: 8,
                      fontSize: 11,
                      fontFamily: "var(--font-mono)",
                    }}
                    labelFormatter={(v) => `t = ${v}s`}
                    formatter={(v) => [`${Number(v).toFixed(2)}°`, "alpha"]}
                  />
                  <Area
                    type="monotone"
                    dataKey="alphaDeg"
                    stroke="#4fd6ff"
                    strokeWidth={2}
                    fill="url(#alphaFill)"
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <SourceNote>
              Real trajectory {replay.trajectoryId} — {replay.source}
            </SourceNote>
          </GlassPanel>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="grid h-full grid-cols-2 gap-3">
            {STATE_VARS.map((v) => (
              <GlassPanel key={v.key} className="flex flex-col justify-between p-4">
                <span className="font-mono-tab text-[10px] uppercase leading-tight tracking-[0.12em] text-(--color-ink-faint)">
                  {v.label}
                </span>
                <span className="mt-2 font-mono-tab text-2xl font-semibold text-(--color-ink)">
                  {(current[v.key] as number).toFixed(1)}
                  <span className="ml-1 text-xs font-medium text-(--color-ink-soft)">{v.unit}</span>
                </span>
              </GlassPanel>
            ))}
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
