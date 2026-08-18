import { Reveal } from "../ui/Reveal";
import { Pill } from "../ui/Primitives";

export function FinalCTA() {
  return (
    <section id="final" className="relative overflow-hidden border-t border-(--color-line) py-28 sm:py-36">
      <div className="grid-horizon pointer-events-none absolute inset-0 -z-10 opacity-60" />
      <div className="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[500px] w-[820px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-(--color-signal)/[0.06] blur-[130px]" />

      <div className="mx-auto max-w-3xl px-6 text-center sm:px-8">
        <Reveal>
          <Pill tone="neutral">Frozen Research · v1.0</Pill>
        </Reveal>
        <Reveal delay={0.08}>
          <h2 className="mt-6 font-mono-tab text-4xl font-bold tracking-tight text-(--color-ink) sm:text-5xl">
            AeroGuard
          </h2>
        </Reveal>
        <Reveal delay={0.14}>
          <p className="mt-3 text-lg text-(--color-ink-soft)">Physics + AI + Aerospace</p>
        </Reveal>

        <Reveal delay={0.22}>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <a
              href="/docs/AEROGUARD_FINAL_RESEARCH_REPORT.md"
              target="_blank"
              rel="noreferrer"
              className="rounded-full bg-(--color-signal) px-6 py-3 font-mono-tab text-[12px] font-semibold uppercase tracking-[0.14em] text-(--color-void) transition-transform hover:scale-[1.03]"
            >
              Read the Research Paper
            </a>
            <a
              href="/docs/PROVENANCE.md"
              target="_blank"
              rel="noreferrer"
              className="rounded-full border border-(--color-line-strong) bg-white/[0.03] px-6 py-3 font-mono-tab text-[12px] font-semibold uppercase tracking-[0.14em] text-(--color-ink) transition-colors hover:border-(--color-signal)/50 hover:text-(--color-signal)"
            >
              View Source
            </a>
            <a
              href="#results"
              className="rounded-full border border-(--color-line-strong) bg-white/[0.03] px-6 py-3 font-mono-tab text-[12px] font-semibold uppercase tracking-[0.14em] text-(--color-ink) transition-colors hover:border-(--color-signal)/50 hover:text-(--color-signal)"
            >
              Explore Results
            </a>
          </div>
        </Reveal>

        <Reveal delay={0.3}>
          <p className="mx-auto mt-14 max-w-xl font-mono-tab text-[11px] leading-relaxed text-(--color-ink-faint)">
            Not peer-reviewed. Not flight-tested. Not a certified aviation safety tool. Every
            number on this page is sourced from outputs/final/AEROGUARD_FINAL_RESEARCH_REPORT.md
            and the frozen metrics files it cites.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
