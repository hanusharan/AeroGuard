import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid, Legend } from "recharts";
import { Reveal } from "../ui/Reveal";
import { Section, SectionTitle, GlassPanel, SourceNote, Pill } from "../ui/Primitives";
import { Counter } from "../ui/Counter";
import metrics from "../../data/metrics.json";
import type { Metrics } from "../../types";

const m = metrics as Metrics;

const coverageData = [
  { threshold: "≥1s", v02: m.v02.warningCoverage[">=1s"] * 100, v03: m.v03.warningCoverage[">=1s"] * 100 },
  { threshold: "≥2s", v02: m.v02.warningCoverage[">=2s"] * 100, v03: m.v03.warningCoverage[">=2s"] * 100 },
  { threshold: "≥3s", v02: m.v02.warningCoverage[">=3s"] * 100, v03: m.v03.warningCoverage[">=3s"] * 100 },
  { threshold: "≥4s", v02: m.v02.warningCoverage[">=4s"] * 100, v03: m.v03.warningCoverage[">=4s"] * 100 },
  { threshold: "≥5s", v02: m.v02.warningCoverage[">=5s"] * 100, v03: m.v03.warningCoverage[">=5s"] * 100 },
];

const coverageCards = [
  { key: ">=2s", label: "≥2s coverage" },
  { key: ">=3s", label: "≥3s coverage" },
  { key: ">=4s", label: "≥4s coverage" },
  { key: ">=5s", label: "≥5s coverage" },
] as const;

export function KeyResults() {
  return (
    <Section id="results">
      <SectionTitle
        kicker="05 — Key Results"
        title="From an imminent-event detector to a multi-second early warning."
        lede="v0.3 introduced a re-timed control-input regime producing a genuine multi-second stall precursor. The same model family, features, and evaluation methodology as v0.2 — only the underlying precursor changed."
      />

      <div className="grid gap-5 lg:grid-cols-2 [&>*]:min-w-0">
        <Reveal>
          <GlassPanel raised className="p-6 sm:p-8">
            <span className="font-mono-tab text-[11px] uppercase tracking-[0.18em] text-(--color-ink-faint)">
              Median warning lead time
            </span>
            <div className="mt-4 flex flex-wrap items-end gap-x-4 gap-y-2">
              <div>
                <div className="font-mono-tab text-2xl font-medium text-(--color-ink-faint) line-through decoration-(--color-critical)/50">
                  {m.v02.medianLeadTimeS.toFixed(2)}s
                </div>
                <div className="mt-1 text-[11px] text-(--color-ink-faint)">v0.2</div>
              </div>
              <ArrowRight />
              <div>
                <div className="font-mono-tab text-5xl font-bold text-(--color-signal) sm:text-6xl">
                  <Counter to={m.v03.medianLeadTimeS} decimals={2} suffix="s" />
                </div>
                <div className="mt-1 text-[11px] text-(--color-signal)">v0.3, final</div>
              </div>
            </div>
            <p className="mt-6 text-sm leading-relaxed text-(--color-ink-soft)">
              Median credited lead time before the stall-boundary crossing, over the{" "}
              {m.v03.nWarned} warned events (of {m.v03.nEvents} evaluated), capped at the 5s
              label horizon. Missed events have no lead time and are not included.
            </p>
          </GlassPanel>
        </Reveal>

        <Reveal delay={0.1}>
          <GlassPanel raised className="p-6 sm:p-8">
            <span className="font-mono-tab text-[11px] uppercase tracking-[0.18em] text-(--color-ink-faint)">
              Event recall &amp; PR-AUC
            </span>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div>
                <div className="font-mono-tab text-4xl font-bold text-(--color-ink) sm:text-5xl">
                  {/* From the counts, not the stored rounded rate: 73/76 is
                      96.1% in the source report, but 0.9605 renders as 96.0. */}
                  <Counter to={(m.v03.nWarned / m.v03.nEvents) * 100} decimals={1} suffix="%" />
                </div>
                <div className="mt-1 text-[11px] text-(--color-ink-faint)">
                  event recall ({m.v03.nWarned}/{m.v03.nEvents} evaluated events)
                </div>
              </div>
              <div>
                <div className="font-mono-tab text-4xl font-bold text-(--color-ink) sm:text-5xl">
                  <Counter to={m.v03.prAuc} decimals={3} />
                </div>
                <div className="mt-1 text-[11px] text-(--color-ink-faint)">PR-AUC, primary model</div>
              </div>
            </div>
            <p className="mt-6 text-sm leading-relaxed text-(--color-ink-soft)">
              vs. v0.2: PR-AUC {m.v02.prAuc.toFixed(3)}, event recall{" "}
              {(m.v02.eventRecall * 100).toFixed(0)}% on only {m.v02.nEvents} usable events (vs.{" "}
              {m.v03.nEvents} at v0.3 scale).
            </p>
          </GlassPanel>
        </Reveal>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {coverageCards.map((c, i) => (
          <Reveal key={c.key} delay={0.05 * i}>
            <GlassPanel className="p-5">
              <div className="font-mono-tab text-3xl font-semibold text-(--color-ink)">
                <Counter to={(m.v03.warningCoverage as never)[c.key] * 100} decimals={1} suffix="%" />
              </div>
              <div className="mt-1.5 font-mono-tab text-[11px] uppercase tracking-[0.14em] text-(--color-ink-faint)">
                {c.label}
              </div>
            </GlassPanel>
          </Reveal>
        ))}
      </div>

      <Reveal delay={0.1}>
        <GlassPanel className="mt-5 p-6 sm:p-8">
          <div className="flex items-center justify-between">
            <span className="font-mono-tab text-[11px] uppercase tracking-[0.18em] text-(--color-ink-faint)">
              Warning coverage by lead-time threshold
            </span>
            <Pill tone="signal">v0.2 → v0.3</Pill>
          </div>
          <div className="mt-5 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={coverageData} barGap={6} margin={{ left: -12, right: 8 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                <XAxis dataKey="threshold" tick={{ fill: "#788796", fontSize: 11 }} stroke="rgba(255,255,255,0.12)" />
                <YAxis
                  tick={{ fill: "#788796", fontSize: 11 }}
                  tickFormatter={(v) => `${v}%`}
                  stroke="rgba(255,255,255,0.12)"
                  width={40}
                />
                <Tooltip
                  contentStyle={{
                    background: "#0a0e15",
                    border: "1px solid rgba(255,255,255,0.12)",
                    borderRadius: 8,
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                  }}
                  formatter={(v) => `${Number(v).toFixed(1)}%`}
                />
                <Legend wrapperStyle={{ fontSize: 11, fontFamily: "var(--font-mono)" }} />
                <Bar dataKey="v02" name="v0.2" fill="#788796" radius={[4, 4, 0, 0]} />
                <Bar dataKey="v03" name="v0.3" fill="#4fd6ff" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <SourceNote>
            outputs/ml_v03/metrics/v02_vs_v03_warning_coverage.csv,
            outputs/ml_v03/metrics/primary_model_metrics.json
          </SourceNote>
        </GlassPanel>
      </Reveal>

      <Reveal delay={0.12}>
        <GlassPanel className="mt-5 p-6 sm:p-8">
          <span className="font-mono-tab text-[11px] uppercase tracking-[0.18em] text-(--color-ink-faint)">
            Reading the event metrics
          </span>
          <ul className="mt-4 space-y-3 text-sm leading-relaxed text-(--color-ink-soft)">
            <li>
              <span className="font-semibold text-(--color-ink)">Evaluated events.</span> The{" "}
              {m.v03.nEvents} events are 57 first crossings plus 19 second episodes in trajectories
              that re-enter the unsafe region. They come from the 456 of {m.dataset.testTrajectories}{" "}
              test trajectories that have rows with a complete 5s future window and a full 1s
              feature window.
            </li>
            <li>
              <span className="font-semibold text-(--color-ink)">Outside the evaluated rows.</span>{" "}
              Ten first crossings, each in a different test trajectory, fall in the last 5s of
              their trajectory. They are counted neither as warned nor as missed, and their effect
              on recall has not been measured. Later episodes in these trajectories also fall
              outside the evaluated rows, but the available metadata does not establish how many
              such episodes there are.
            </li>
            <li>
              <span className="font-semibold text-(--color-ink)">Lead time.</span> The median covers
              warned events only. Coverage by threshold is measured over all {m.v03.nEvents}{" "}
              evaluated events.
            </li>
          </ul>
          <SourceNote>
            Counts of 456, 57, 19 and 10 are from outputs/ml_v03/metrics/primary_model_metrics.json,
            physics_vs_ml_summary.json and data/metadata/trajectory_metadata_v3.csv; definitions in
            ml/events.py and the README ("What the event metrics cover").
          </SourceNote>
        </GlassPanel>
      </Reveal>

      <Reveal delay={0.15}>
        <div className="mt-5 rounded-2xl border border-(--color-line-strong) bg-white/[0.02] p-6 sm:p-7">
          <div className="flex items-center gap-2.5">
            <NotIcon />
            <span className="font-mono-tab text-[11px] font-medium uppercase tracking-[0.2em] text-(--color-ink)">
              What this does not establish
            </span>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {NOT_ESTABLISHED.map((n) => (
              <span
                key={n}
                className="rounded-full border border-(--color-line) bg-white/[0.03] px-3 py-1.5 font-mono-tab text-[11px] text-(--color-ink-soft)"
              >
                {n}
              </span>
            ))}
          </div>
          <p className="mt-4 text-sm leading-relaxed text-(--color-ink-soft)">
            Every number above is simulation-internal, measured on a simplified 2D longitudinal
            model that is explicitly not a validated model of any real aircraft. Full scope and
            threats to validity are in <a href="#limitations" className="text-(--color-signal) underline decoration-(--color-signal)/40 underline-offset-2 hover:decoration-(--color-signal)">Scientific Scope</a>.
          </p>
        </div>
      </Reveal>
    </Section>
  );
}

const NOT_ESTABLISHED = [
  "Universal stall prediction",
  "Real-aircraft safety",
  "Real-flight performance",
  "Zero-shot generalization to arbitrary regimes",
];

function NotIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" className="shrink-0 text-(--color-ink-faint)">
      <circle cx="8" cy="8" r="6.3" stroke="currentColor" strokeWidth="1.4" />
      <path d="M3.6 3.6l8.8 8.8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

function ArrowRight() {
  return (
    <svg width="28" height="14" viewBox="0 0 28 14" fill="none" className="mb-3 text-(--color-ink-faint)">
      <path d="M0 7H26M26 7L20 1M26 7L20 13" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
