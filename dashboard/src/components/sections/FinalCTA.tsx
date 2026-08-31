import { Reveal } from "../ui/Reveal";
import { Pill } from "../ui/Primitives";
import { PAPER_HTML, PAPER_PDF, FULL_REPORT, PROVENANCE } from "../../lib/links";

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

        <Reveal delay={0.2}>
          <div className="mx-auto mt-12 max-w-xl rounded-2xl border border-(--color-signal)/25 bg-(--color-signal)/[0.05] p-6 sm:p-7">
            <span className="font-mono-tab text-[11px] font-medium uppercase tracking-[0.24em] text-(--color-signal)">
              The paper
            </span>
            <h3 className="mt-3 text-[17px] font-semibold leading-snug text-(--color-ink)">
              A Physics-Informed Machine Learning Approach to Multi-Second Aircraft Stall Early
              Warning and Cross-Mechanism Generalization
            </h3>
            <p className="mt-3 text-sm leading-relaxed text-(--color-ink-soft)">
              The full write-up of everything on this page — methods, the precursor diagnosis, the
              control-profile intervention, and the two-direction transfer test — with figures and
              references.
            </p>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              <a
                href={PAPER_HTML}
                target="_blank"
                rel="noreferrer"
                className="rounded-full bg-(--color-signal) px-6 py-3 font-mono-tab text-[12px] font-semibold uppercase tracking-[0.14em] text-(--color-void) transition-transform hover:scale-[1.03]"
              >
                Read the Research Paper
              </a>
              <a
                href={PAPER_PDF}
                target="_blank"
                rel="noreferrer"
                className="rounded-full border border-(--color-signal)/40 px-6 py-3 font-mono-tab text-[12px] font-semibold uppercase tracking-[0.14em] text-(--color-signal) transition-colors hover:bg-(--color-signal)/10"
              >
                PDF
              </a>
            </div>
          </div>
        </Reveal>

        <Reveal delay={0.28}>
          <div className="mt-7 flex flex-wrap items-center justify-center gap-4">
            <a
              href={FULL_REPORT}
              target="_blank"
              rel="noreferrer"
              className="rounded-full border border-(--color-line-strong) bg-white/[0.03] px-6 py-3 font-mono-tab text-[12px] font-semibold uppercase tracking-[0.14em] text-(--color-ink) transition-colors hover:border-(--color-signal)/50 hover:text-(--color-signal)"
            >
              Full Research Report
            </a>
            <a
              href={PROVENANCE}
              target="_blank"
              rel="noreferrer"
              className="rounded-full border border-(--color-line-strong) bg-white/[0.03] px-6 py-3 font-mono-tab text-[12px] font-semibold uppercase tracking-[0.14em] text-(--color-ink) transition-colors hover:border-(--color-signal)/50 hover:text-(--color-signal)"
            >
              Provenance
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
