import type { ReactNode } from "react";
import clsx from "clsx";

export function Section({
  id,
  children,
  className,
  bordered = true,
}: {
  id?: string;
  children: ReactNode;
  className?: string;
  bordered?: boolean;
}) {
  return (
    <section
      id={id}
      className={clsx(
        "relative mx-auto w-full max-w-6xl px-6 py-24 sm:px-8 md:py-32",
        bordered && "border-t border-(--color-line)",
        className,
      )}
    >
      {children}
    </section>
  );
}

export function Kicker({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-center gap-2.5 text-(--color-signal)">
      <span className="h-[6px] w-[6px] rounded-full bg-(--color-signal) shadow-[0_0_10px_var(--color-signal)]" />
      <span className="font-mono-tab text-[11px] font-medium uppercase tracking-[0.28em]">
        {children}
      </span>
    </div>
  );
}

export function SectionTitle({
  kicker,
  title,
  lede,
}: {
  kicker: string;
  title: ReactNode;
  lede?: ReactNode;
}) {
  return (
    <div className="mb-14 max-w-3xl">
      <Kicker>{kicker}</Kicker>
      <h2 className="mt-4 text-3xl font-semibold tracking-tight text-(--color-ink) sm:text-4xl">
        {title}
      </h2>
      {lede && <p className="mt-5 text-lg leading-relaxed text-(--color-ink-soft)">{lede}</p>}
    </div>
  );
}

export function GlassPanel({
  children,
  className,
  raised = false,
}: {
  children: ReactNode;
  className?: string;
  raised?: boolean;
}) {
  return (
    <div className={clsx("rounded-2xl", raised ? "glass-raised" : "glass", className)}>
      {children}
    </div>
  );
}

export function StatValue({
  value,
  unit,
  className,
}: {
  value: ReactNode;
  unit?: string;
  className?: string;
}) {
  return (
    <div className={clsx("font-mono-tab font-semibold tracking-tight text-(--color-ink)", className)}>
      {value}
      {unit && <span className="ml-1 text-[0.5em] font-medium text-(--color-ink-soft)">{unit}</span>}
    </div>
  );
}

export function Pill({
  children,
  tone = "signal",
}: {
  children: ReactNode;
  tone?: "signal" | "caution" | "critical" | "safe" | "neutral";
}) {
  const tones: Record<string, string> = {
    signal: "text-(--color-signal) border-(--color-signal)/30 bg-(--color-signal)/10",
    caution: "text-(--color-caution) border-(--color-caution)/30 bg-(--color-caution)/10",
    critical: "text-(--color-critical) border-(--color-critical)/30 bg-(--color-critical)/10",
    safe: "text-(--color-safe) border-(--color-safe)/30 bg-(--color-safe)/10",
    neutral: "text-(--color-ink-soft) border-(--color-line-strong) bg-white/5",
  };
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border px-3 py-1 font-mono-tab text-[11px] font-medium uppercase tracking-[0.18em]",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}

export function SourceNote({ children }: { children: ReactNode }) {
  return (
    // Source paths are long unbreakable tokens; without break-words their
    // min-content width stretches whatever grid or panel contains them.
    <p className="mt-3 break-words font-mono-tab text-[11px] leading-relaxed text-(--color-ink-faint)">
      {children}
    </p>
  );
}
