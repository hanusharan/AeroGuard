import { Reveal } from "../ui/Reveal";
import { Section, GlassPanel, SourceNote } from "../ui/Primitives";
import { Counter } from "../ui/Counter";
import metrics from "../../data/metrics.json";
import type { Metrics } from "../../types";

const m = metrics as Metrics;

// The value row is a fixed 40px band so the four cards keep a shared baseline
// even though the split card's digits scale down to fit its own width.
const valueRow = "flex h-10 items-center text-4xl font-semibold leading-none";

export function Scale() {
  return (
    <Section id="scale" bordered={false} className="py-16 sm:py-20">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Reveal>
          <GlassPanel className="p-6">
            <div className={`${valueRow} text-(--color-ink)`}>
              <Counter to={m.dataset.trajectories} />
            </div>
            <div className="mt-2 font-mono-tab text-[11px] uppercase tracking-[0.16em] text-(--color-ink-faint)">
              v0.3 trajectories
            </div>
          </GlassPanel>
        </Reveal>
        <Reveal delay={0.06}>
          <GlassPanel className="p-6">
            <div className={`${valueRow} text-(--color-ink)`}>
              <Counter to={5.34} decimals={2} suffix="M+" />
            </div>
            <div className="mt-2 font-mono-tab text-[11px] uppercase tracking-[0.16em] text-(--color-ink-faint)">
              observations ({m.dataset.rows.toLocaleString()} rows)
            </div>
          </GlassPanel>
        </Reveal>
        <Reveal delay={0.12}>
          {/* Three numbers on one line overflow a quarter-width card at 4xl,
              so this one sizes off the panel width and caps at the row size. */}
          <GlassPanel className="@container p-6">
            <div
              className={`${valueRow} whitespace-nowrap text-(--color-ink)`}
              style={{ fontSize: "min(2.25rem, 12cqw)" }}
            >
              <Counter to={m.dataset.trainTrajectories} />
              <span className="mx-[0.15em] text-[0.7em] text-(--color-ink-faint)">/</span>
              <Counter to={m.dataset.valTrajectories} />
              <span className="mx-[0.15em] text-[0.7em] text-(--color-ink-faint)">/</span>
              <Counter to={m.dataset.testTrajectories} />
            </div>
            <div className="mt-2 font-mono-tab text-[11px] uppercase tracking-[0.16em] text-(--color-ink-faint)">
              train / val / test split
            </div>
          </GlassPanel>
        </Reveal>
        <Reveal delay={0.18}>
          <GlassPanel className="p-6">
            <div className={`${valueRow} text-(--color-safe)`}>
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
