import { Reveal } from "../ui/Reveal";
import { Section, SectionTitle, GlassPanel, Pill } from "../ui/Primitives";

export function Problem() {
  return (
    <Section id="problem">
      <SectionTitle
        kicker="01 — The Problem"
        title="Detecting a stall is not the same problem as warning about one."
        lede="A system that only flags a stall once the aircraft has already crossed the aerodynamic boundary offers no time to react. AeroGuard's research question is about the seconds before that boundary — not the instant it is reached."
      />

      <div className="grid gap-5 sm:grid-cols-2">
        <Reveal>
          <GlassPanel className="h-full p-8">
            <Pill tone="critical">Stall Detection</Pill>
            <h3 className="mt-5 text-xl font-semibold text-(--color-ink)">Reactive</h3>
            <p className="mt-3 text-sm leading-relaxed text-(--color-ink-soft)">
              Identifies that the angle of attack has already exceeded the critical boundary.
              Correct, but too late to act — the aircraft is already in the stalled regime by
              the time this signal fires.
            </p>
            <div className="mt-6 flex items-center gap-2 font-mono-tab text-[11px] uppercase tracking-[0.16em] text-(--color-critical)">
              <TimelineIcon /> Warning at T + 0.0s
            </div>
          </GlassPanel>
        </Reveal>

        <Reveal delay={0.1}>
          <GlassPanel raised className="h-full p-8 ring-1 ring-(--color-signal)/25">
            <Pill tone="signal">Stall Early Warning</Pill>
            <h3 className="mt-5 text-xl font-semibold text-(--color-ink)">Predictive</h3>
            <p className="mt-3 text-sm leading-relaxed text-(--color-ink-soft)">
              Recognizes a rising angle of attack and shrinking stall margin over a short causal
              window, seconds before the boundary is reached — while the flight state still
              carries a genuine physical precursor.
            </p>
            <div className="mt-6 flex items-center gap-2 font-mono-tab text-[11px] uppercase tracking-[0.16em] text-(--color-signal)">
              <TimelineIcon /> Warning at T − 4.72s (median, v0.3)
            </div>
          </GlassPanel>
        </Reveal>
      </div>

      <Reveal delay={0.2}>
        <p className="mt-8 max-w-2xl text-sm leading-relaxed text-(--color-ink-faint)">
          Early datasets in this project produced crossings with a physical precursor of only
          0.37–0.54 seconds — too short for any model to learn a genuine early warning from. A
          central finding of this research (see Timeline) is that this was a control-input
          timing artifact, not a limit of the underlying flight dynamics.
        </p>
      </Reveal>
    </Section>
  );
}

function TimelineIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.3" />
      <path d="M7 3.5V7L9.3 8.6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}
