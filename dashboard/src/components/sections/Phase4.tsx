import { Reveal } from "../ui/Reveal";
import { Section, SectionTitle, GlassPanel, SourceNote, Pill } from "../ui/Primitives";
import data from "../../data/phase4.json";

// Every value comes from dashboard/src/data/phase4.json, exported verbatim from
// outputs/phase4/run_20261015T152932Z by data_export/export_phase4.py and
// checked by parity/check_metrics.mjs. Rounding happens only here.
const f3 = (x: number) => x.toFixed(3);
const f2 = (x: number) => x.toFixed(2);
const ci3 = ([lo, hi]: number[]) => `[${f3(lo)}, ${f3(hi)}]`;
const signed3 = (x: number) => `${x >= 0 ? "+" : "−"}${f3(Math.abs(x))}`;
const ciSigned3 = ([lo, hi]: number[]) => `[${signed3(lo)}, ${signed3(hi)}]`;

type Group = (typeof data.groups)["SEEN"];

const CARDS: { label: string; sub: string; g: Group }[] = [
  { label: "Training aircraft", sub: "12 configurations, held-out test flights", g: data.groups.SEEN },
  { label: "New aircraft, inside the range", sub: "4 configurations never trained on", g: data.groups.IDH },
  { label: "Unfamiliar aircraft", sub: "6 configurations outside the range", g: data.groups.OOD },
  { label: "Different simulator", sub: "JSBSim c172p, trained on AeroGuard only", g: data.jsbsim.cross },
];

const r = data.robustness;

const FINDINGS: { title: string; verdict: string; tone: "safe" | "caution" | "critical"; body: string }[] = [
  {
    title: "New aircraft inside the training range",
    verdict: "No loss detected",
    tone: "safe",
    body: `PR-AUC difference versus training aircraft ${signed3(data.item44.delta)} ${ciSigned3(data.item44.ci)}. The interval is wide: a loss of about 0.02 cannot be excluded.`,
  },
  {
    title: "Unfamiliar aircraft",
    verdict: "Modest loss",
    tone: "caution",
    body: `PR-AUC ${f3(data.groups.OOD.prAuc)} and a shorter median lead (${f2(data.groups.OOD.medianLeadS)} s). The loss did not grow detectably with distance from the training range (Spearman ρ = ${f2(data.item45.rho)}, p = ${f2(data.item45.p)}).`,
  },
  {
    title: "How the stall is entered matters most",
    verdict: "Large regime gap",
    tone: "caution",
    body: `Median lead ${f2(data.regimes.gradual.medianLeadS)} s on gradual approaches (${data.regimes.gradual.nEvents} events) but ${f2(data.regimes.abrupt.medianLeadS)} s on abrupt entries (${data.regimes.abrupt.nEvents} events). Multi-second warning exists only for gradual approaches.`,
  },
  {
    title: "Transfer to an independent simulator",
    verdict: "Partial skill",
    tone: "caution",
    body: `Trained only on AeroGuard, the model warned all ${data.jsbsim.cross.nEvents} JSBSim test stalls, but PR-AUC fell to ${f3(data.jsbsim.cross.prAuc)} (${f3(data.jsbsim.native.prAuc)} when trained on JSBSim itself) and median lead to ${f2(data.jsbsim.cross.medianLeadS)} s (${f2(data.jsbsim.native.medianLeadS)} s natively). Only ${data.jsbsim.cross.nEvents} test events, so event metrics are coarse.`,
  },
  {
    title: "Temporal vs. instantaneous model",
    verdict: "Ranking advantage persists",
    tone: "safe",
    body: `Higher PR-AUC in ${r["K1|IDH"].signHolds}/${r["K1|IDH"].nRuns} runs on new aircraft (${signed3(r["K1|IDH"].diff)} ${ciSigned3(r["K1|IDH"].ci)}) and ${r["K1|OOD"].signHolds}/${r["K1|OOD"].nRuns} on unfamiliar ones (${signed3(r["K1|OOD"].diff)} ${ciSigned3(r["K1|OOD"].ci)}).`,
  },
  {
    title: "Longer lead or higher recall?",
    verdict: "Not supported",
    tone: "critical",
    body: `A longer median lead than the instantaneous model held in only ${r["K2|IDH"].signHolds}/${r["K2|IDH"].nRuns} runs, and recall at least matching the angle-of-attack rule in ${r["K3|OOD"].signHolds}/${r["K3|OOD"].nRuns} on unfamiliar aircraft. Each model ran at its own threshold, so these compare operating points; a threshold-matched comparison was not part of this study.`,
  },
];

export function Phase4() {
  return (
    <Section id="phase4">
      <SectionTitle
        kicker="10 — Generalisation Study (Phase 4)"
        title="Does the warning survive a different aircraft — or a different simulator?"
        lede={`${data.nConfigurations} simulated aircraft configurations varying 15 parameters (including mass, wing area, lift curve, drag, thrust, pitch response and air density), plus the independent JSBSim Cessna 172 model. The protocol and its pass/fail rules were committed before any of this data existed.`}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 [&>*]:min-w-0">
        {CARDS.map((c, i) => (
          <Reveal key={c.label} delay={i * 0.05}>
            <GlassPanel raised className="h-full p-5">
              <div className="text-[13px] font-semibold text-(--color-ink)">{c.label}</div>
              <div className="mt-1 text-xs text-(--color-ink-faint)">{c.sub}</div>
              <div className="mt-4 font-mono-tab text-3xl font-semibold text-(--color-ink)">{f3(c.g.prAuc)}</div>
              <div className="mt-1 font-mono-tab text-[11px] text-(--color-ink-faint)">PR-AUC {ci3(c.g.prAucCi)}</div>
              <dl className="mt-4 grid grid-cols-2 gap-2 border-t border-(--color-line) pt-3 text-xs">
                <div>
                  <dt className="text-(--color-ink-faint)">Stalls warned</dt>
                  <dd className="font-mono-tab text-(--color-ink)">{c.g.nWarned}/{c.g.nEvents}</dd>
                </div>
                <div>
                  <dt className="text-(--color-ink-faint)">Median lead</dt>
                  <dd className="font-mono-tab text-(--color-ink)">{f2(c.g.medianLeadS)} s</dd>
                </div>
              </dl>
            </GlassPanel>
          </Reveal>
        ))}
      </div>
      <p className="mt-3 text-xs text-(--color-ink-faint)">
        Family-trained temporal model, primary seed, at its validation-selected threshold; 95% trajectory-bootstrap intervals.
        Lead times are over warned stalls only. For comparison, the v0.3 model on its own aircraft: PR-AUC 0.890.
      </p>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 [&>*]:min-w-0">
        {FINDINGS.map((x, i) => (
          <Reveal key={x.title} delay={i * 0.04}>
            <GlassPanel className="h-full p-6">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-[15px] font-semibold text-(--color-ink)">{x.title}</h3>
                <Pill tone={x.tone}>{x.verdict}</Pill>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-(--color-ink-soft)">{x.body}</p>
            </GlassPanel>
          </Reveal>
        ))}
      </div>

      <Reveal>
        <div className="mt-6 rounded-2xl border border-(--color-line-strong) bg-white/[0.02] p-6 text-sm leading-relaxed text-(--color-ink-soft)">
          <span className="font-semibold text-(--color-ink)">An unexpected result.</span> The original v0.3 model, trained on
          one aircraft and never refitted, ranked stalls on the unfamiliar aircraft about as well as the family-trained model
          (PR-AUC {f3(data.frozenZeroShotOOD.prAuc)} vs {f3(data.groups.OOD.prAuc)}) and was better calibrated, while warning
          later and less often. Retraining on many aircraft did not improve ranking on unfamiliar ones in this simulator.
        </div>
      </Reveal>

      <p className="mt-6 text-sm text-(--color-ink-soft)">
        Simulation only, by the same author and code base, so this is not independent replication. JSBSim&apos;s c172p is
        itself an approximation: transfer between two simulators is model-to-model, not validation against flight data.
      </p>

      <SourceNote>
        {data.source}/REPORT.md §2–4, 7–8, 11 (primary.json, jsbsim.json, robustness.json); protocol {data.protocol},
        deviations P4-D1 to P4-D5 in experiments/phase4/DEVIATIONS.md; reasoning in RESEARCH_LOG.md RL-008.
      </SourceNote>
    </Section>
  );
}
