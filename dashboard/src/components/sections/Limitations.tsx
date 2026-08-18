import { Reveal } from "../ui/Reveal";
import { Section, SectionTitle, GlassPanel } from "../ui/Primitives";

const LIMITATIONS = [
  {
    title: "Simplified physics model",
    body: "2D longitudinal dynamics only — no roll, yaw, or sideslip. Constant air density, a linear pitch-response surrogate, and plausible-not-measured aerodynamic coefficients.",
  },
  {
    title: "Simulation-generated datasets",
    body: "All 5.34M+ observations come from this simulator, not from real flight recorders or wind-tunnel instrumentation.",
  },
  {
    title: "No real-flight or CFD validation",
    body: "No claim of correspondence to any real aircraft type's behavior is established or attempted.",
  },
  {
    title: "Not universal zero-shot generalization",
    body: "Cross-mechanism transfer was demonstrated within one broad slow-approach phenomenon class — not across arbitrary unseen flight regimes.",
  },
  {
    title: "Performance depends on phenomenon-class exposure",
    body: "A zero-exposure exclusion check shows the model cannot invent multi-second precursor detection without prior training exposure to the broader phenomenon class.",
  },
];

export function Limitations() {
  return (
    <Section id="limitations">
      <SectionTitle
        kicker="07 — Scientific Scope"
        title="What this research does and does not establish."
        lede="Stated as scope, not apology — every claim on this page is precisely bounded by what was actually measured."
      />

      <div className="grid gap-4 sm:grid-cols-2">
        {LIMITATIONS.map((l, i) => (
          <Reveal key={l.title} delay={i * 0.05}>
            <GlassPanel className="h-full p-6">
              <div className="flex items-start gap-3">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-(--color-ink-faint)" />
                <div>
                  <h3 className="text-[15px] font-semibold text-(--color-ink)">{l.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-(--color-ink-soft)">{l.body}</p>
                </div>
              </div>
            </GlassPanel>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}
