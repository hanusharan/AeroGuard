import { motion } from "framer-motion";
import { Reveal } from "../ui/Reveal";
import { Section, SectionTitle, GlassPanel, Pill } from "../ui/Primitives";

const STAGES = [
  { label: "Flight Dynamics", desc: "5-state RK4 physics simulation" },
  { label: "Temporal Flight Data", desc: "Per-timestep trajectory telemetry" },
  { label: "Causal Temporal Features", desc: "State + derivatives + 1s causal window" },
  { label: "Random Forest", desc: "23 features, 200 trees, frozen" },
  { label: "Stall Risk", desc: "Warning probability, 0–1" },
  { label: "Early Warning", desc: "Thresholded, multi-second lead" },
];

export function AIPipeline() {
  return (
    <Section id="pipeline">
      <SectionTitle
        kicker="03 — AI Pipeline"
        title="A causal pipeline from raw dynamics to an early warning."
        lede="Every feature the model sees is computed from the current timestep and a fixed window of the past — never from the future. This is what makes the resulting probability a genuine early-warning signal rather than hindsight."
      />

      <Reveal>
        <GlassPanel className="overflow-x-auto p-6 sm:p-10">
          <div className="flex min-w-[860px] items-center justify-between gap-1">
            {STAGES.map((s, i) => (
              <div key={s.label} className="flex flex-1 items-center">
                <div className="flex flex-1 flex-col items-center text-center">
                  <div
                    className={
                      "flex h-16 w-16 items-center justify-center rounded-2xl border font-mono-tab text-[10px] " +
                      (i === STAGES.length - 1
                        ? "border-(--color-signal)/50 bg-(--color-signal)/10 text-(--color-signal)"
                        : "border-(--color-line-strong) bg-white/[0.04] text-(--color-ink-soft)")
                    }
                  >
                    {String(i + 1).padStart(2, "0")}
                  </div>
                  <span className="mt-3 max-w-[110px] text-[13px] font-semibold text-(--color-ink)">
                    {s.label}
                  </span>
                  <span className="mt-1.5 max-w-[120px] text-[11px] leading-snug text-(--color-ink-faint)">
                    {s.desc}
                  </span>
                </div>

                {i < STAGES.length - 1 && (
                  <div className="relative mx-1 h-px w-10 shrink-0 bg-(--color-line-strong) sm:w-14">
                    <motion.span
                      className="absolute -top-[3px] h-[7px] w-[7px] rounded-full bg-(--color-signal) shadow-[0_0_8px_var(--color-signal)]"
                      animate={{ left: ["0%", "100%"] }}
                      transition={{
                        duration: 1.4,
                        repeat: Infinity,
                        ease: "linear",
                        delay: i * 0.22,
                      }}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </GlassPanel>
      </Reveal>

      <Reveal delay={0.15}>
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Pill tone="signal">Causal only</Pill>
          <p className="max-w-2xl text-sm leading-relaxed text-(--color-ink-soft)">
            The temporal feature window (0.5–2s tested; 1s used in the primary model) is built
            strictly backward-looking — <code className="font-mono-tab text-(--color-ink)">t − W</code> to{" "}
            <code className="font-mono-tab text-(--color-ink)">t</code> — and every leakage guard in the
            test suite verifies no label-derived or future-timestep information reaches the feature
            set.
          </p>
        </div>
      </Reveal>
    </Section>
  );
}
