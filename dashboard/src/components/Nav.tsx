import { useEffect, useRef, useState } from "react";

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

// The desktop bar has no room for these, but the mobile menu does.
const MOBILE_ONLY_AFTER: Record<string, { id: string; label: string }> = {
  results: { id: "evaluation", label: "Evaluation" },
  generalization: { id: "phase4", label: "Phase 4" },
  timeline: { id: "future-work", label: "Open Questions" },
};

const MOBILE_LINKS = LINKS.flatMap((l) => (MOBILE_ONLY_AFTER[l.id] ? [l, MOBILE_ONLY_AFTER[l.id]] : [l]));

export function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      // Focus would otherwise fall to <body> when the focused menu link unmounts.
      if (document.getElementById("mobile-nav")?.contains(document.activeElement)) toggleRef.current?.focus();
      setMenuOpen(false);
    };
    // The menu is only rendered below xl; close it if the viewport grows past that.
    const mq = window.matchMedia("(min-width: 1280px)");
    const onMq = () => mq.matches && setMenuOpen(false);
    window.addEventListener("keydown", onKey);
    mq.addEventListener("change", onMq);
    return () => {
      window.removeEventListener("keydown", onKey);
      mq.removeEventListener("change", onMq);
    };
  }, [menuOpen]);

  return (
    <header
      className={
        "fixed inset-x-0 top-0 z-50 transition-colors duration-300 " +
        (scrolled || menuOpen ? "glass border-b border-(--color-line)" : "border-b border-transparent")
      }
    >
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-[60] focus:rounded-full focus:bg-(--color-signal) focus:px-4 focus:py-2 focus:font-mono-tab focus:text-[11px] focus:uppercase focus:tracking-[0.14em] focus:text-(--color-void)"
      >
        Skip to content
      </a>
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4 sm:px-8">
        <a href="#top" className="flex items-center gap-2.5" onClick={() => setMenuOpen(false)}>
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-(--color-signal) opacity-60 motion-reduce:hidden" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-(--color-signal)" />
          </span>
          <span className="font-mono-tab text-[13px] font-semibold tracking-[0.2em] text-(--color-ink)">
            AEROGUARD
          </span>
        </a>

        {/* The full link bar needs about 1,260px, so it appears from xl (1280px);
            narrower screens use the menu button. */}
        <nav aria-label="Sections" className="mx-4 hidden items-center gap-4 xl:flex xl:mx-6 xl:gap-6">
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

        <div className="flex items-center gap-2">
          <a
            href="#results"
            className="hidden whitespace-nowrap rounded-full border border-(--color-line-strong) bg-white/[0.04] px-4 py-1.5 font-mono-tab text-[11px] uppercase tracking-[0.14em] text-(--color-ink) transition-colors hover:border-(--color-signal)/50 hover:text-(--color-signal) min-[360px]:inline-block"
            onClick={() => setMenuOpen(false)}
          >
            Key Result
          </a>
          <button
            ref={toggleRef}
            type="button"
            className="flex h-9 w-9 items-center justify-center rounded-full border border-(--color-line-strong) bg-white/[0.04] text-(--color-ink) transition-colors hover:border-(--color-signal)/50 hover:text-(--color-signal) xl:hidden"
            aria-expanded={menuOpen}
            aria-controls="mobile-nav"
            aria-label={menuOpen ? "Close section menu" : "Open section menu"}
            onClick={() => setMenuOpen((o) => !o)}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              {menuOpen ? (
                <path d="M3.5 3.5l9 9M12.5 3.5l-9 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              ) : (
                <path d="M2.5 4.5h11M2.5 8h11M2.5 11.5h11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {menuOpen && (
        <nav
          id="mobile-nav"
          aria-label="Sections"
          className="max-h-[calc(100dvh-4.5rem)] overflow-y-auto border-t border-(--color-line) bg-(--color-void) xl:hidden"
        >
          <ul className="mx-auto grid max-w-6xl grid-cols-2 gap-1 px-4 py-3 sm:grid-cols-3 sm:px-6">
            {MOBILE_LINKS.map((l) => (
              <li key={l.id}>
                <a
                  href={`#${l.id}`}
                  onClick={() => setMenuOpen(false)}
                  className="block rounded-lg px-3 py-3 font-mono-tab text-[12px] uppercase tracking-[0.12em] text-(--color-ink-soft) transition-colors hover:bg-white/[0.04] hover:text-(--color-ink)"
                >
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </header>
  );
}
