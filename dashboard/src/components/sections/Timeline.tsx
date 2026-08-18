import { Reveal } from "../ui/Reveal";
import { Section, SectionTitle } from "../ui/Primitives";

const STAGES = [
  { label: "Physics Model", detail: "5-state RK4 longitudinal simulator, emergent stall" },
  { label: "v0.1", detail: "1,000 trajectories, first dataset generation" },
  { label: "v0.2", detail: "Ground-contact fix, near_boundary recalibration" },
  { label: "Temporal ML", detail: "Median lead 0.53s — an imminent-event detector" },
  { label: "Precursor Diagnosis", detail: "Root cause: control-input timing, not physics" },
  { label: "v0.3", detail: "3,150 trajectories, engineered multi-second precursor" },
  { label: "Generalization", detail: "Cross-mechanism transfer, CASE A" },
  { label: "Final Research", detail: "190/190 tests, frozen, packaged" },
];

export function Timeline() {
  return (
    <Section id="timeline">
      <SectionTitle
        kicker="08 — Research Timeline"
        title="Eight stages, one continuous line of evidence."
      />

      <div className="relative">
        <div className="absolute left-[15px] top-2 bottom-2 w-px bg-(--color-line-strong) sm:left-1/2 sm:w-px" />
        <ol className="space-y-8">
          {STAGES.map((s, i) => (
            <Reveal key={s.label} delay={i * 0.04}>
              <li
                className={
                  "relative flex items-start gap-5 sm:w-1/2 " +
                  (i % 2 === 0 ? "sm:pr-10" : "sm:ml-auto sm:flex-row-reverse sm:pl-10 sm:text-right")
                }
              >
                <span className="relative z-10 mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-(--color-signal)/40 bg-(--color-hull) font-mono-tab text-[11px] text-(--color-signal) sm:absolute sm:left-1/2 sm:-translate-x-1/2">
                  {i + 1}
                </span>
                <div className="ml-1 sm:ml-0">
                  <h3 className="text-[15px] font-semibold text-(--color-ink)">{s.label}</h3>
                  <p className="mt-1 text-sm text-(--color-ink-soft)">{s.detail}</p>
                </div>
              </li>
            </Reveal>
          ))}
        </ol>
      </div>
    </Section>
  );
}
