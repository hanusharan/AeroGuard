import type { ReactNode } from "react";
import clsx from "clsx";
import { Reveal } from "../ui/Reveal";
import { Section, SectionTitle, GlassPanel, SourceNote, Pill } from "../ui/Primitives";
import metrics from "../../data/metrics.json";
import type { Metrics } from "../../types";

const m = metrics as Metrics;

/**
 * The causal spine of the whole project, read top to bottom: a measured failure,
 * a hypothesis about its cause, one isolated intervention, and the measured
 * result. Every node is a number from the repo, not a narrative flourish.
 */
type Step = {
  kind: "measure" | "verdict" | "hypothesis" | "action";
  label: string;
  value?: string;
  detail: string;
};

const CHAIN: Step[] = [
  {
    kind: "measure",
    label: "v0.2 dataset",
    value: `${m.precursor.v02MedianS.toFixed(2)}s`,
    detail: "median physical precursor — the measured alpha 8°→16° transition in the data itself",
  },
  {
    kind: "verdict",
    label: "Diagnosis",
    detail:
      "Too short for any model to learn a genuine early warning from. Sub-second warnings are detection, not warning.",
  },
  {
    kind: "hypothesis",
    label: "Hypothesis",
    detail:
      "The bottleneck is control-input timing, not the flight dynamics. Fast elevator pulses aimed far past the boundary compress the approach into a fraction of a second.",
  },
  {
    kind: "action",
    label: "Intervention",
    detail:
      "Slow and re-aim the elevator profile. Change nothing else — not the physics, not the stall boundary, not the model, not the evaluation.",
  },
  {
    kind: "measure",
    label: "v0.3 dataset",
    value: `${m.precursor.v03MedianS.toFixed(2)}s`,
    detail: `median physical precursor — ${(m.precursor.v03Coverage[">=2s"] * 100).toFixed(0)}% of crossings ≥2s, ${(m.precursor.v03Coverage[">=3s"] * 100).toFixed(0)}% ≥3s`,
  },
  {
    kind: "action",
    label: "Temporal ML",
    detail:
      "The same model family, the same 23 features, the same event-level evaluation applied to v0.2 — retrained on the new dataset.",
  },
  {
    kind: "measure",
    label: "Model warning",
    value: `${m.v03.medianLeadTimeS.toFixed(2)}s`,
    // Derived from the counts rather than the stored rounded rate, so this
    // reads 96.1% like the source report and not 96.0%.
    detail: `median credited lead time, ${((m.v03.nWarned / m.v03.nEvents) * 100).toFixed(1)}% event recall (${m.v03.nWarned}/${m.v03.nEvents}) on held-out TEST`,
  },
];

const UNCHANGED = [
  "Physics engine",
  "Stall boundary (α ≈ 16.07°)",
  "Model family & hyperparameters",
  "Feature definitions",
  "Evaluation methodology",
];

const CHANGED = ["Control-input timing / elevator profile"];

export function Intervention() {
  return (
    <Section id="intervention">
      <SectionTitle
        kicker="04 — The Intervention"
        title="One change to the dataset turned a 0.54s detector into a 4.72s warning."
        lede="This is the central result of the research, and it is a causal claim rather than a correlational one: everything that could explain the improvement was held fixed except a single, deliberate change to how control inputs were generated."
      />

      {/* min-w-0 so a long source path inside a column can't widen the track. */}
      <div className="grid gap-5 lg:grid-cols-[1.15fr_1fr] lg:items-start [&>*]:min-w-0">
        <Reveal>
          <GlassPanel raised className="p-6 sm:p-8">
            <span className="font-mono-tab text-[11px] uppercase tracking-[0.18em] text-(--color-ink-faint)">
              v0.2 → v0.3, step by step
            </span>
            <ol className="mt-6">
              {CHAIN.map((s, i) => (
                <li key={s.label} className="relative pb-7 pl-8 last:pb-0">
                  {i < CHAIN.length - 1 && (
                    <span
                      aria-hidden
                      className="absolute left-[7px] top-4 h-full w-px bg-gradient-to-b from-(--color-line-strong) to-(--color-line)"
                    />
                  )}
                  <span
                    aria-hidden
                    className={clsx(
                      "absolute left-0 top-[5px] h-[15px] w-[15px] rounded-full border-2",
                      s.kind === "measure" && i === 0 && "border-(--color-critical) bg-(--color-critical)/20",
                      s.kind === "measure" && i > 0 && "border-(--color-signal) bg-(--color-signal)/25",
                      s.kind === "verdict" && "border-(--color-critical) bg-(--color-void)",
                      s.kind === "hypothesis" && "border-(--color-caution) bg-(--color-void)",
                      s.kind === "action" && "border-(--color-line-strong) bg-(--color-void)",
                    )}
                  />
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <span className="font-mono-tab text-[11px] uppercase tracking-[0.16em] text-(--color-ink-faint)">
                      {s.label}
                    </span>
                    {s.value && (
                      <span
                        className={clsx(
                          "font-mono-tab text-2xl font-bold tabular-nums",
                          i === 0 ? "text-(--color-ink-faint)" : "text-(--color-signal)",
                        )}
                      >
                        {s.value}
                      </span>
                    )}
                  </div>
                  <p className="mt-1.5 text-sm leading-relaxed text-(--color-ink-soft)">{s.detail}</p>
                </li>
              ))}
            </ol>
            <SourceNote>
              outputs/dataset_audit_v3/v03_generation_report.md (precursor),
              outputs/ml_v03/metrics/primary_model_metrics.json (lead time, recall)
            </SourceNote>
          </GlassPanel>
        </Reveal>

        <div className="grid gap-5">
          <Reveal delay={0.1}>
            <GlassPanel className="p-6 sm:p-8">
              <div className="flex items-center justify-between gap-3">
                <span className="font-mono-tab text-[11px] uppercase tracking-[0.18em] text-(--color-ink-faint)">
                  What changed between v0.2 and v0.3?
                </span>
              </div>

              <div className="mt-6">
                <Pill tone="neutral">Not changed</Pill>
                <ul className="mt-4 space-y-2.5">
                  {UNCHANGED.map((u) => (
                    <li key={u} className="flex items-start gap-2.5 text-sm text-(--color-ink-soft)">
                      <LockIcon />
                      <span>{u}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="mt-7 border-t border-(--color-line) pt-6">
                <Pill tone="signal">Changed</Pill>
                <ul className="mt-4 space-y-2.5">
                  {CHANGED.map((c) => (
                    <li key={c} className="flex items-start gap-2.5 text-sm font-medium text-(--color-ink)">
                      <SwapIcon />
                      <span>{c}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <p className="mt-7 border-t border-(--color-line) pt-6 text-sm leading-relaxed text-(--color-ink-soft)">
                Holding all five of those fixed is what isolates the dataset intervention as the
                explanation for the longer physical precursor — and, downstream of it, the longer
                warning. The physics engine has been unmodified since Stage 1.
              </p>
              <SourceNote>PROVENANCE.md, aeroguard/ (unchanged since Stage 1)</SourceNote>
            </GlassPanel>
          </Reveal>

          <Reveal delay={0.16}>
            <GlassPanel className="p-6 sm:p-8">
              <span className="font-mono-tab text-[11px] uppercase tracking-[0.18em] text-(--color-ink-faint)">
                Precursor coverage in the data
              </span>
              <div className="mt-5 space-y-4">
                <CoverageBar
                  label="≥2s precursor"
                  v02={m.precursor.v02Coverage[">=2s"]}
                  v03={m.precursor.v03Coverage[">=2s"]}
                  approxV02
                />
                <CoverageBar
                  label="≥3s precursor"
                  v02={m.precursor.v02Coverage[">=3s"]}
                  v03={m.precursor.v03Coverage[">=3s"]}
                  approxV02
                />
              </div>
              <SourceNote>
                outputs/dataset_audit_v3/v03_generation_report.md — dip-aware, direction-aligned
                precursor metric, identical definition across versions. v0.2 figures are reported
                as approximate in the source.
              </SourceNote>
            </GlassPanel>
          </Reveal>
        </div>
      </div>
    </Section>
  );
}

function CoverageBar({
  label,
  v02,
  v03,
  approxV02,
}: {
  label: string;
  v02: number;
  v03: number;
  approxV02?: boolean;
}) {
  const fmt = (v: number) => `${approxV02 ? "~" : ""}${(v * 100).toFixed(0)}%`;
  return (
    <div>
      <div className="flex items-baseline justify-between font-mono-tab text-[11px] uppercase tracking-[0.14em] text-(--color-ink-faint)">
        <span>{label}</span>
      </div>
      <div className="mt-2.5 space-y-1.5">
        <Track value={v02} tone="dim" caption={`v0.2 · ${fmt(v02)}`} />
        <Track value={v03} tone="signal" caption={`v0.3 · ${(v03 * 100).toFixed(1)}%`} />
      </div>
    </div>
  );
}

function Track({ value, tone, caption }: { value: number; tone: "dim" | "signal"; caption: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/[0.06]">
        <div
          className={clsx(
            "h-full rounded-full",
            tone === "signal" ? "bg-(--color-signal)" : "bg-(--color-ink-faint)",
          )}
          style={{ width: `${Math.max(value * 100, 1)}%` }}
        />
      </div>
      <span
        className={clsx(
          "w-[92px] shrink-0 font-mono-tab text-[11px] tabular-nums",
          tone === "signal" ? "text-(--color-signal)" : "text-(--color-ink-faint)",
        )}
      >
        {caption}
      </span>
    </div>
  );
}

function LockIcon(): ReactNode {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="mt-[3px] shrink-0 text-(--color-ink-faint)">
      <rect x="2.6" y="6" width="8.8" height="6.4" rx="1.4" stroke="currentColor" strokeWidth="1.3" />
      <path d="M4.8 6V4.4a2.2 2.2 0 0 1 4.4 0V6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

function SwapIcon(): ReactNode {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="mt-[3px] shrink-0 text-(--color-signal)">
      <path d="M1.8 4.4h8.1M7.6 2.1l2.3 2.3-2.3 2.3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M12.2 9.6H4.1M6.4 11.9 4.1 9.6l2.3-2.3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
