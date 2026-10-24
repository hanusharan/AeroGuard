import { Reveal } from "../ui/Reveal";
import { Section, SectionTitle, GlassPanel, SourceNote } from "../ui/Primitives";

// Numbers copied from the committed, machine-generated reports listed in the SourceNote below.
const METHODS = [
  { name: "Temporal model (frozen)", prauc: "0.890 [0.854, 0.922]", fa: "18.8 [11.6, 26.8]", c2: "0.66", c4: "0.63" },
  { name: "Instantaneous model", prauc: "0.875 [0.835, 0.911]", fa: "29.5 [17.6, 43.8]", c2: "0.69", c4: "0.63" },
  { name: "Angle-of-attack threshold", prauc: "0.709 [0.667, 0.745]", fa: "23.4 [14.9, 33.4]", c2: "0.51", c4: "0.19" },
];

const FINDINGS = [
  {
    title: "Temporal vs. instantaneous model",
    body: "PR-AUC difference +0.015 [0.008, 0.023] (paired trajectory bootstrap). At validation-matched false-warning rates of 10 and 20 per simulated hour, the temporal model warned more events 4 s ahead (+0.12 and +0.09); at 40 per hour the interval includes 0.",
  },
  {
    title: "Temporal model vs. angle-of-attack rule",
    body: "PR-AUC difference +0.181 [0.150, 0.219]. At every matched false-warning rate the temporal model covered more events 4 s ahead (+0.34 to +0.45).",
  },
  {
    title: "Removing control inputs (Item 33)",
    body: "Retraining without elevator and throttle, or also without recent elevator change, gave PR-AUC differences whose intervals include 0 (5 seeds). No difference was demonstrated; this does not show the inputs are irrelevant.",
  },
  {
    title: "Checks on the conclusions (Item 42)",
    body: "No trajectory in two splits, no label-derived feature, best single feature far below the full model, thresholds reproducible from training and validation data, all stored metrics recomputed exactly, every headline statement re-derived independently.",
  },
];

export function Evaluation() {
  return (
    <Section id="evaluation">
      <SectionTitle
        kicker="06 — Evaluation (Items 33–42)"
        title="A fair comparison, with uncertainty and leakage checks."
        lede="Same test rows, same split, thresholds chosen on validation data only, and 95% intervals from resampling whole trajectories. Test set: 456 simulated flights, 76 stall events, about 1.49 simulated hours."
      />

      <Reveal>
        <GlassPanel className="p-6">
          <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Method comparison (scrolls sideways on narrow screens)">
          <table className="w-full min-w-[560px] text-left text-sm text-(--color-ink-soft)">
            <thead className="text-(--color-ink)">
              <tr>
                <th className="py-2 pr-4 font-semibold">Method</th>
                <th className="py-2 pr-4 font-semibold">PR-AUC [95% CI]</th>
                <th className="py-2 pr-4 font-semibold">False warnings / sim. hour</th>
                <th className="py-2 pr-4 font-semibold">Warned ≥ 2 s ahead</th>
                <th className="py-2 font-semibold">Warned ≥ 4 s ahead</th>
              </tr>
            </thead>
            <tbody>
              {METHODS.map((m) => (
                <tr key={m.name} className="border-t border-white/10">
                  <td className="py-2 pr-4 text-(--color-ink)">{m.name}</td>
                  <td className="py-2 pr-4">{m.prauc}</td>
                  <td className="py-2 pr-4">{m.fa}</td>
                  <td className="py-2 pr-4">{m.c2}</td>
                  <td className="py-2">{m.c4}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          <p className="mt-3 text-xs text-(--color-ink-faint)">
            Warning and coverage columns use each method's own validation-selected threshold, so they are shown side by side, not ranked.
          </p>
          <p className="mt-2 text-xs text-(--color-ink-faint)">
            Coverage here counts an event only if the evaluated rows include the full L seconds before its crossing (74 of 76
            events at 2 s, 67 at 4 s), so a warning that early could have been observed. Key Results divides the same warned
            events by all 76, which is why the temporal model shows 64.5% and 55.3% there.
          </p>
        </GlassPanel>
      </Reveal>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        {FINDINGS.map((f, i) => (
          <Reveal key={f.title} delay={i * 0.05}>
            <GlassPanel className="h-full p-6">
              <h3 className="text-[15px] font-semibold text-(--color-ink)">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-(--color-ink-soft)">{f.body}</p>
            </GlassPanel>
          </Reveal>
        ))}
      </div>

      <p className="mt-4 text-sm text-(--color-ink-soft)">
        Simulation only. The test split had been used in earlier analyses, so these are not blind or independent results, and
        the rates are per simulated hour, not operational rates. Nothing here is evidence about real aircraft.
      </p>

      <SourceNote>
        outputs/items33_42/items40_42/run_20261015T144358282823Z/REPORT.md (combined comparison report),
        coverage_item38.json (eligible-event denominators),
        outputs/items33_42/items37_39/…/REPORT.md, outputs/items33_42/item33/…/REPORT.md, outputs/phase3/…/REPORT.md
      </SourceNote>
    </Section>
  );
}
