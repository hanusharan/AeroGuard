import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid, Cell } from "recharts";
import { Reveal } from "../ui/Reveal";
import { Section, SectionTitle, GlassPanel, SourceNote, Pill } from "../ui/Primitives";
import metrics from "../../data/metrics.json";
import type { Metrics } from "../../types";

const m = metrics as Metrics;

const prAucComparison = [
  { label: "In-distribution", value: m.v03.prAuc * 100, tone: "#4fd6ff" },
  { label: "Zero-exposure exclusion", value: m.generalization.zeroExposureExclusion.prAuc * 100, tone: "#ff5f56" },
  { label: "Forward: novel mechanism", value: m.generalization.forward.prAuc * 100, tone: "#3ddc97" },
  { label: "Reverse: novel → gradual", value: m.generalization.reverse.prAuc * 100, tone: "#3ddc97" },
];

export function Generalization() {
  return (
    <Section id="generalization">
      <SectionTitle
        kicker="06 — Generalization"
        title="Does the warning signal transfer to a mechanism the model never trained on?"
        lede="Candidate D's two-pulse control profile produced v0.3's training data. A structurally distinct single-pulse mechanism — reaching the same physical stall boundary by a genuinely different temporal path — tests whether the model learned a transferable pattern or memorized one shape."
      />

      <div className="grid gap-5 lg:grid-cols-2">
        <Reveal>
          <GlassPanel raised className="p-8">
            <div className="flex items-center justify-between">
              <Pill tone="signal">Forward</Pill>
              <span className="font-mono-tab text-[11px] text-(--color-ink-faint)">frozen v0.3 → novel mechanism</span>
            </div>
            <div className="mt-5 grid grid-cols-3 gap-4">
              <Stat label="PR-AUC" value={m.generalization.forward.prAuc.toFixed(3)} />
              <Stat label="Event recall" value={`${(m.generalization.forward.eventRecall * 100).toFixed(0)}%`} />
              <Stat label="Median lead" value={`${m.generalization.forward.medianLeadTimeS.toFixed(2)}s`} />
            </div>
            <p className="mt-5 text-sm leading-relaxed text-(--color-ink-soft)">
              The frozen primary model — never refit — evaluated on {m.generalization.forwardPopulation.n_events}{" "}
              held-out events from a control-input mechanism it never saw in training.
            </p>
          </GlassPanel>
        </Reveal>

        <Reveal delay={0.1}>
          <GlassPanel raised className="p-8">
            <div className="flex items-center justify-between">
              <Pill tone="signal">Reverse</Pill>
              <span className="font-mono-tab text-[11px] text-(--color-ink-faint)">mechanism-only model → v0.3 gradual</span>
            </div>
            <div className="mt-5 grid grid-cols-3 gap-4">
              <Stat label="PR-AUC" value={m.generalization.reverse.prAuc.toFixed(3)} />
              <Stat label="Event recall" value={`${(m.generalization.reverse.eventRecall * 100).toFixed(0)}%`} />
              <Stat label="Median lead" value={`${m.generalization.reverse.medianLeadTimeS.toFixed(2)}s`} />
            </div>
            <p className="mt-5 text-sm leading-relaxed text-(--color-ink-soft)">
              A fresh model trained only on the novel mechanism — never seeing a single Candidate D
              trajectory — evaluated on v0.3's own held-out gradual-approach events.
            </p>
          </GlassPanel>
        </Reveal>
      </div>

      <Reveal delay={0.15}>
        <GlassPanel className="mt-5 p-6 sm:p-8">
          <span className="font-mono-tab text-[11px] uppercase tracking-[0.18em] text-(--color-ink-faint)">
            PR-AUC across four checks
          </span>
          <div className="mt-5 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={prAucComparison} layout="vertical" margin={{ left: 24, right: 24 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.06)" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tick={{ fill: "#5b6672", fontSize: 10 }} tickFormatter={(v) => `${v}%`} stroke="rgba(255,255,255,0.12)" />
                <YAxis type="category" dataKey="label" tick={{ fill: "#9aa7b5", fontSize: 11 }} width={170} stroke="rgba(255,255,255,0.12)" />
                <Tooltip
                  contentStyle={{ background: "#0a0e15", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, fontSize: 11, fontFamily: "var(--font-mono)" }}
                  formatter={(v) => `${Number(v).toFixed(1)}%`}
                />
                <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                  {prAucComparison.map((d) => (
                    <Cell key={d.label} fill={d.tone} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <SourceNote>
            outputs/ml_v03/metrics/generalization_check.json,
            outputs/ml_v03_generalization/metrics/{"{forward_check_frozen_model_on_alt_mechanism,reverse_check_alt_model_on_v03_gradual}"}.json
          </SourceNote>
        </GlassPanel>
      </Reveal>

      <Reveal delay={0.2}>
        <div className="mt-6 flex items-start gap-3 rounded-2xl border border-(--color-caution)/25 bg-(--color-caution)/[0.06] p-5">
          <WarnIcon />
          <p className="text-sm leading-relaxed text-(--color-ink-soft)">
            <span className="font-semibold text-(--color-ink)">Decision: CASE A.</span> The evidence
            supports transfer across structurally distinct control-input mechanisms producing the
            same underlying physical phenomenon. It does <span className="font-semibold text-(--color-ink)">not</span>{" "}
            establish universal zero-shot stall prediction — the zero-exposure exclusion check
            (PR-AUC {(m.generalization.zeroExposureExclusion.prAuc * 100).toFixed(1)}%, median lead{" "}
            {m.generalization.zeroExposureExclusion.medianLeadTimeS.toFixed(2)}s) shows the model
            cannot invent multi-second precursor detection with zero training exposure to the
            phenomenon class. This is a family-level generalization, not a universal one.
          </p>
        </div>
      </Reveal>
    </Section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="font-mono-tab text-2xl font-bold text-(--color-ink)">{value}</div>
      <div className="mt-1 font-mono-tab text-[10px] uppercase tracking-[0.12em] text-(--color-ink-faint)">{label}</div>
    </div>
  );
}

function WarnIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="mt-0.5 shrink-0 text-(--color-caution)">
      <path d="M10 2L18.5 17H1.5L10 2Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
      <path d="M10 8V11.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="10" cy="14.2" r="0.9" fill="currentColor" />
    </svg>
  );
}
