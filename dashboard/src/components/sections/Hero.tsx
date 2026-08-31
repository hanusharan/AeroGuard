import { motion } from "framer-motion";
import { HeroTrajectory } from "../HeroTrajectory";
import { Pill } from "../ui/Primitives";
import { FULL_REPORT } from "../../lib/links";

export function Hero() {
  return (
    <section id="top" className="relative overflow-hidden pt-36 pb-20 sm:pt-44">
      <div className="grid-horizon pointer-events-none absolute inset-0 -z-10" />
      <div className="pointer-events-none absolute left-1/2 top-0 -z-10 h-[560px] w-[900px] -translate-x-1/2 rounded-full bg-(--color-signal)/[0.07] blur-[140px]" />

      <div className="mx-auto max-w-5xl px-6 text-center sm:px-8">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="flex justify-center"
        >
          <Pill tone="neutral">Frozen Research · v1.0</Pill>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.08, ease: [0.16, 1, 0.3, 1] }}
          className="mt-7 font-mono-tab text-[15vw] font-bold leading-none tracking-tight text-(--color-ink) sm:text-8xl"
        >
          AEROGUARD
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.18, ease: [0.16, 1, 0.3, 1] }}
          className="mx-auto mt-6 max-w-2xl text-xl font-medium text-(--color-ink) sm:text-2xl"
        >
          Physics-informed machine learning for early aircraft stall warning.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.26, ease: [0.16, 1, 0.3, 1] }}
          className="mx-auto mt-9 max-w-3xl"
        >
          <div className="glass rounded-2xl border-l-2 border-l-(--color-signal) px-6 py-7 text-left sm:px-9 sm:py-8">
            <span className="font-mono-tab text-[11px] font-medium uppercase tracking-[0.28em] text-(--color-signal)">
              Research question
            </span>
            <p className="mt-4 text-lg leading-relaxed font-medium text-(--color-ink) sm:text-xl">
              Can a temporal ML model detect a physically meaningful approach-to-stall precursor{" "}
              <em className="not-italic text-(--color-signal)">seconds</em> before the stall
              boundary — and transfer that warning to a structurally different control mechanism?
            </p>
            <p className="mt-4 text-sm leading-relaxed text-(--color-ink-soft)">
              Answered end to end inside this repository: a 2D longitudinal flight-dynamics
              simulator, three versioned trajectory datasets, and a temporal early-warning model
              evaluated once on a held-out, trajectory-level TEST split.
            </p>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.34, ease: [0.16, 1, 0.3, 1] }}
          className="mt-9 flex flex-wrap items-center justify-center gap-4"
        >
          <a
            href="#problem"
            className="rounded-full bg-(--color-signal) px-6 py-3 font-mono-tab text-[12px] font-semibold uppercase tracking-[0.14em] text-(--color-void) transition-transform hover:scale-[1.03]"
          >
            Explore the Research
          </a>
          <a
            href={FULL_REPORT}
            target="_blank"
            rel="noreferrer"
            className="rounded-full border border-(--color-line-strong) bg-white/[0.03] px-6 py-3 font-mono-tab text-[12px] font-semibold uppercase tracking-[0.14em] text-(--color-ink) transition-colors hover:border-(--color-signal)/50 hover:text-(--color-signal)"
          >
            Read the Full Research Report
          </a>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.9, delay: 0.42, ease: [0.16, 1, 0.3, 1] }}
        className="mx-auto mt-16 max-w-4xl px-4"
      >
        <div className="glass-raised rounded-3xl p-6 sm:p-10">
          <HeroTrajectory />
          <div className="mt-2 flex flex-wrap items-center justify-center gap-x-10 gap-y-2 font-mono-tab text-[11px] uppercase tracking-[0.16em] text-(--color-ink-faint)">
            <span>Simulated flight-path vector</span>
            <span>Illustrative — see Flight Replay for a real, model-scored trajectory</span>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
