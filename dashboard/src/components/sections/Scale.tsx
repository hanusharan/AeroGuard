import { Reveal } from "../ui/Reveal";
import { Section, GlassPanel, SourceNote } from "../ui/Primitives";
import { Counter } from "../ui/Counter";
import metrics from "../../data/metrics.json";
import type { Metrics } from "../../types";

const m = metrics as Metrics;

export function Scale() {
  return (
    <Section id="scale" bordered={false} className="py-16 sm:py-20">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Reveal>
          <GlassPanel className="p-6">
            <div className="text-4xl font-semibold text-(--color-ink)">
              <Counter to={m.dataset.trajectories} />
            </div>
            <div className="mt-2 font-mono-tab text-[11px] uppercase tracking-[0.16em] text-(--color-ink-faint)">
              v0.3 trajectories
            </div>
          </GlassPanel>
        </Reveal>
        <Reveal delay={0.06}>
          <GlassPanel className="p-6">
            <div className="text-4xl font-semibold text-(--color-ink)">
              <Counter to={5.34} decimals={2} suffix="M+" />
            </div>
            <div className="mt-2 font-mono-tab text-[11px] uppercase tracking-[0.16em] text-(--color-ink-faint)">
              observations ({m.dataset.rows.toLocaleString()} rows)
            </div>
          </GlassPanel>
        </Reveal>
        <Reveal delay={0.12}>
          <GlassPanel className="p-6">
            <div className="text-4xl font-semibold text-(--color-ink)">
              <Counter to={m.dataset.trainTrajectories} />
              <span className="text-(--color-ink-faint)">/</span>
              <Counter to={m.dataset.valTrajectories} />
              <span className="text-(--color-ink-faint)">/</span>
              <Counter to={m.dataset.testTrajectories} />
            </div>
            <div className="mt-2 font-mono-tab text-[11px] uppercase tracking-[0.16em] text-(--color-ink-faint)">
              train / val / test split
            </div>
          </GlassPanel>
        </Reveal>
        <Reveal delay={0.18}>
          <GlassPanel className="p-6">
            <div className="text-4xl font-semibold text-(--color-safe)">
              <Counter to={m.dataset.splitOverlap} />
            </div>
            <div className="mt-2 font-mono-tab text-[11px] uppercase tracking-[0.16em] text-(--color-ink-faint)">
              trajectory-ID split overlap
            </div>
          </GlassPanel>
        </Reveal>
      </div>
      <SourceNote>
        data/metadata/trajectory_metadata_v3.csv, data/splits/split_manifest_v3.csv — verified
        directly against the frozen dataset files during final packaging.
      </SourceNote>
    </Section>
  );
}
