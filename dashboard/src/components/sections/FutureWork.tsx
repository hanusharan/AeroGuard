import { Reveal } from "../ui/Reveal";
import { Section, SectionTitle, GlassPanel, SourceNote } from "../ui/Primitives";

const FACTORS = ["mass","wing area","aerodynamic coefficients","air density","initial airspeed","initial altitude"];

export function FutureWork() {
  return (
    <Section id="future-work">
      <SectionTitle
        kicker="10 — Next Research Stage"
        title="v0.4: can the warning survive a different aircraft?"
        lede="The v1.0 research result is frozen. The next scientifically meaningful question is whether the learned precursor generalizes when the simulated aircraft parameters change."
      />
      <Reveal>
        <GlassPanel raised className="p-6 sm:p-8">
          <div className="grid gap-8 md:grid-cols-[1.15fr_0.85fr]">
            <div>
              <div className="font-mono-tab text-[11px] uppercase tracking-[0.18em] text-(--color-signal)">Proposed experiment</div>
              <h3 className="mt-3 text-xl font-semibold text-(--color-ink)">Aircraft family A → Aircraft family B</h3>
              <p className="mt-4 text-sm leading-relaxed text-(--color-ink-soft)">
                Freeze the existing training pipeline and evaluate transfer under controlled changes to the simulated aircraft, without changing the published v1.0 result.
              </p>
              <div className="mt-6 rounded-xl border border-(--color-line) bg-white/[0.02] p-5">
                <div className="font-mono-tab text-[10px] uppercase tracking-[0.16em] text-(--color-ink-faint)">Evaluation principle</div>
                <p className="mt-2 text-sm font-medium leading-relaxed text-(--color-ink)">
                  Train on one parameterized aircraft family, freeze the model, then test on a meaningfully different family without refitting.
                </p>
              </div>
            </div>
            <div>
              <div className="font-mono-tab text-[11px] uppercase tracking-[0.18em] text-(--color-ink-faint)">Candidate variables</div>
              <div className="mt-4 grid grid-cols-2 gap-3">
                {FACTORS.map((factor) => (
                  <div key={factor} className="rounded-xl border border-(--color-line) bg-white/[0.02] px-4 py-3 text-sm text-(--color-ink-soft)">{factor}</div>
                ))}
              </div>
            </div>
          </div>
        </GlassPanel>
      </Reveal>
      <SourceNote>Future work only. No v0.4 measurements or performance claims are included in the frozen v1.0 research record.</SourceNote>
    </Section>
  );
}
