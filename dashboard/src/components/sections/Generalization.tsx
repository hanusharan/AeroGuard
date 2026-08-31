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
        kicker="08 — Generalization"
        title="Does the warning signal transfer to a mechanism the model never trained on?"
        lede="Candidate D's two-pulse control profile produced v0.3's training data. A structurally distinct single-pulse mechanism — reaching the same physical stall boundary by a genuinely different temporal path — tests whether the model learned a transferable pattern or memorized one shape."
      />

      <Reveal>
        <GlassPanel raised className="mb-5 p-6 sm:p-8">
          <span className="font-mono-tab text-[11px] uppercase tracking-[0.18em] text-(--color-ink-faint)">
            The forward transfer test
          </span>

          <div className="mt-7 flex flex-col items-stretch gap-0 md:flex-row md:items-center md:gap-0">
            <FlowNode
              caption="Train"
              title="Mechanism A"
              sub="Candidate D — two-pulse elevator profile, v0.3 training data"
            />
            <FlowArrow />
            <FlowNode caption="Model" title="Temporal ML" sub="23 features, 1s causal window" />
            <FlowArrow />
            <FlowNode caption="Freeze" title="No refit" sub="inference only — weights untouched" />
            <FlowArrow />
            <FlowNode
              caption="Evaluate"
              title="Mechanism B"
              sub="single-pulse precursor — never seen in training"
              tone="novel"
            />
          </div>

          <div className="mt-7 grid grid-cols-3 gap-4 border-t border-(--color-line) pt-6">
            <BigStat label="PR-AUC" value={m.generalization.forward.prAuc.toFixed(3)} />
            <BigStat
              label={`event recall (${m.generalization.forward.nWarned}/${m.generalization.forward.nEvents})`}
              value={`${(m.generalization.forward.eventRecall * 100).toFixed(0)}%`}
              highlight
            />
            <BigStat label="median lead" value={`${m.generalization.forward.medianLeadTimeS.toFixed(2)}s`} />
          </div>
          <p className="mt-4 text-sm leading-relaxed text-(--color-ink-soft)">
            The frozen model retained{" "}
            <span className="font-medium text-(--color-ink)">
              {((m.generalization.forward.prAuc / m.v03.prAuc) * 100).toFixed(0)}%
            </span>{" "}
            of its in-distribution PR-AUC ({m.v03.prAuc.toFixed(3)}) on a control-input mechanism
            that reaches the same physical stall boundary by a structurally different temporal path.
          </p>
        </GlassPanel>
      </Reveal>

      <Reveal delay={0.08}>
        <div className="mb-5 rounded-2xl border border-(--color-critical)/25 bg-(--color-critical)/[0.05] p-6 sm:p-8">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="text-lg font-semibold text-(--color-ink)">But is it zero-shot?</span>
            <span className="font-mono-tab text-lg font-bold uppercase tracking-[0.14em] text-(--color-critical)">
              No.
            </span>
          </div>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-(--color-ink-soft)">
            Remove the entire slow-approach family from training — leaving the model with{" "}
            <span className="font-medium text-(--color-ink)">zero</span> exposure to any
            multi-second approach — and the same architecture, features, and evaluation collapse:
          </p>
          <div className="mt-6 grid grid-cols-3 gap-4">
            <BigStat
              label="PR-AUC"
              value={m.generalization.zeroExposureExclusion.prAuc.toFixed(3)}
              tone="critical"
            />
            <BigStat
              label="event recall"
              value={`${(m.generalization.zeroExposureExclusion.eventRecall * 100).toFixed(1)}%`}
              tone="critical"
            />
            <BigStat
              label="median lead"
              value={`${m.generalization.zeroExposureExclusion.medianLeadTimeS.toFixed(2)}s`}
              tone="critical"
            />
          </div>
          <p className="mt-5 border-t border-(--color-critical)/20 pt-5 text-sm leading-relaxed text-(--color-ink-soft)">
            A{" "}
            <span className="font-semibold text-(--color-ink)">
              {(m.v03.medianLeadTimeS / m.generalization.zeroExposureExclusion.medianLeadTimeS).toFixed(0)}x
            </span>{" "}
            drop in median lead time, back to the sub-second regime v0.3 was built to escape.
            The conclusion this forces:{" "}
            <span className="font-semibold text-(--color-ink)">
              family-level transfer, not universal zero-shot prediction.
            </span>
          </p>
        </div>
      </Reveal>

      <Reveal delay={0.1}>
        <GlassPanel raised className="p-8">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Pill tone="signal">Reverse check</Pill>
            <span className="font-mono-tab text-[11px] text-(--color-ink-faint)">
              mechanism-only model → v0.3 gradual
            </span>
          </div>
          <div className="mt-5 grid grid-cols-3 gap-4">
            <Stat label="PR-AUC" value={m.generalization.reverse.prAuc.toFixed(3)} />
            <Stat
              label={`Event recall (${m.generalization.reverse.nWarned}/${m.generalization.reverse.nEvents})`}
              value={`${(m.generalization.reverse.eventRecall * 100).toFixed(0)}%`}
            />
            <Stat label="Median lead" value={`${m.generalization.reverse.medianLeadTimeS.toFixed(2)}s`} />
          </div>
          <p className="mt-5 text-sm leading-relaxed text-(--color-ink-soft)">
            Transfer runs both ways. A fresh model trained <em>only</em> on the novel mechanism —
            never seeing a single Candidate D trajectory — still warns on v0.3's own held-out
            gradual-approach events, at the 5s horizon cap.
          </p>
        </GlassPanel>
      </Reveal>

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
            <span className="font-semibold text-(--color-ink)">Decision: CASE A.</span> Taking the
            forward, reverse, and zero-exposure checks together, the evidence supports transfer
            across structurally distinct control-input mechanisms producing the same underlying
            physical phenomenon — and does{" "}
            <span className="font-semibold text-(--color-ink)">not</span> establish universal
            zero-shot stall prediction across arbitrary unseen flight regimes. This is a
            family-level generalization, not a universal one.
          </p>
        </div>
      </Reveal>
    </Section>
  );
}

/**
 * One box in the train → freeze → evaluate chain. `tone="novel"` marks the
 * mechanism the model never trained on, which is the whole point of the figure.
 */
function FlowNode({
  caption,
  title,
  sub,
  tone = "default",
}: {
  caption: string;
  title: string;
  sub: string;
  tone?: "default" | "novel";
}) {
  return (
    <div
      className={
        "flex-1 rounded-xl border p-4 " +
        (tone === "novel"
          ? "border-(--color-safe)/40 bg-(--color-safe)/[0.07]"
          : "border-(--color-line) bg-white/[0.02]")
      }
    >
      <div
        className={
          "font-mono-tab text-[10px] uppercase tracking-[0.16em] " +
          (tone === "novel" ? "text-(--color-safe)" : "text-(--color-ink-faint)")
        }
      >
        {caption}
      </div>
      <div className="mt-1.5 text-[15px] font-semibold text-(--color-ink)">{title}</div>
      <div className="mt-1 text-[12px] leading-snug text-(--color-ink-soft)">{sub}</div>
    </div>
  );
}

function FlowArrow() {
  return (
    <div aria-hidden className="flex items-center justify-center px-2 py-2 text-(--color-ink-faint)">
      {/* Chain reads left-to-right on desktop and top-to-bottom once it wraps. */}
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="hidden md:block">
        <path d="M2 10h15M17 10l-5-4.5M17 10l-5 4.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="md:hidden">
        <path d="M10 2v15M10 17l-4.5-5M10 17l4.5-5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

function BigStat({
  label,
  value,
  highlight,
  tone = "default",
}: {
  label: string;
  value: string;
  highlight?: boolean;
  tone?: "default" | "critical";
}) {
  const color =
    tone === "critical"
      ? "text-(--color-critical)"
      : highlight
        ? "text-(--color-safe)"
        : "text-(--color-ink)";
  return (
    <div>
      <div className={`font-mono-tab text-3xl font-bold tabular-nums sm:text-4xl ${color}`}>{value}</div>
      <div className="mt-1.5 font-mono-tab text-[10px] uppercase tracking-[0.12em] text-(--color-ink-faint)">
        {label}
      </div>
    </div>
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
