import { Reveal } from "../ui/Reveal";
import { Section, SectionTitle, GlassPanel, SourceNote } from "../ui/Primitives";

// What the evidence on this page does not yet settle. Each item is a gap named
// in the repository's own reports, not a new claim.
const OPEN = [
  {
    title: "Independent replication",
    body: "Every result here was produced and checked by the same author and code base. No one else has re-implemented or re-run the study.",
  },
  {
    title: "Threshold-matched lead-time comparison",
    body: "Phase 4 compared lead time and recall at each model's own threshold, which confounds model with operating point. A comparison at matched false-warning rates, as done for v0.3 in Items 40–42, is still to be run on the aircraft family.",
  },
  {
    title: "Primary experimental reference data",
    body: "The simulator's lift curve has been compared only with a secondary stall-speed figure and with another simulator's model. Primary sources (wind-tunnel data, flight-manual values) have not been checked.",
  },
  {
    title: "Real flight data",
    body: "No real aircraft, flight recorder or wind-tunnel data was used at any stage. Whether any of this transfers to real flight is unknown.",
  },
  {
    title: "Expert and peer review",
    body: "The simulator assumptions and the stall-margin definition have not been reviewed by an aerodynamics specialist, and the paper has not been peer-reviewed.",
  },
];

export function FutureWork() {
  return (
    <Section id="future-work">
      <SectionTitle
        kicker="13 — Open Questions"
        title="What this work has not yet shown."
        lede="The questions below are where the evidence currently stops. They are stated so that nothing on this page is read as settling them."
      />
      <div className="grid gap-4 sm:grid-cols-2 [&>*]:min-w-0">
        {OPEN.map((o, i) => (
          <Reveal key={o.title} delay={i * 0.04}>
            <GlassPanel className="h-full p-6">
              <h3 className="text-[15px] font-semibold text-(--color-ink)">{o.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-(--color-ink-soft)">{o.body}</p>
            </GlassPanel>
          </Reveal>
        ))}
      </div>
      <SourceNote>
        outputs/phase4/run_20261015T152932Z/REPORT.md §9, §11; experiments/phase4/SIMULATOR_ASSUMPTIONS.md;
        REPRODUCIBILITY_REPORT.md (replication status).
      </SourceNote>
    </Section>
  );
}
