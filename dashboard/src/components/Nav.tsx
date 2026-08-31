import { useEffect, useState } from "react";

const LINKS = [
  { id: "problem", label: "Problem" },
  { id: "physics", label: "Physics" },
  { id: "pipeline", label: "Pipeline" },
  { id: "intervention", label: "Intervention" },
  { id: "results", label: "Results" },
  { id: "replay", label: "Replay" },
  { id: "simulator", label: "Simulator" },
  { id: "generalization", label: "Generalization" },
  { id: "limitations", label: "Scope" },
  { id: "timeline", label: "Timeline" },
];

export function Nav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={
        "fixed inset-x-0 top-0 z-50 transition-colors duration-300 " +
        (scrolled ? "glass border-b border-(--color-line)" : "border-b border-transparent")
      }
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4 sm:px-8">
        <a href="#top" className="flex items-center gap-2.5">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-(--color-signal) opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-(--color-signal)" />
          </span>
          <span className="font-mono-tab text-[13px] font-semibold tracking-[0.2em] text-(--color-ink)">
            AEROGUARD
          </span>
        </a>

        {/* Adding an "Intervention" link left no slack at 1280px, so the gap and
            letter-spacing tighten below xl rather than pushing the CTA off-screen. */}
        <nav className="mx-4 hidden items-center gap-4 lg:flex xl:mx-6 xl:gap-6">
          {LINKS.map((l) => (
            <a
              key={l.id}
              href={`#${l.id}`}
              className="font-mono-tab whitespace-nowrap text-[11px] uppercase tracking-[0.1em] text-(--color-ink-soft) transition-colors hover:text-(--color-ink) xl:tracking-[0.14em]"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <a
          href="#results"
          className="rounded-full border border-(--color-line-strong) bg-white/[0.04] px-4 py-1.5 font-mono-tab text-[11px] uppercase tracking-[0.14em] text-(--color-ink) transition-colors hover:border-(--color-signal)/50 hover:text-(--color-signal)"
        >
          Key Result
        </a>
      </div>
    </header>
  );
}
