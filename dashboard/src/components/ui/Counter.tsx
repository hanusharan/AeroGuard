import { useEffect, useRef, useState } from "react";
import { useInView } from "framer-motion";

export function Counter({
  to,
  duration = 1.4,
  decimals = 0,
  prefix = "",
  suffix = "",
}: {
  to: number;
  duration?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const observerInView = useInView(ref, { once: true, margin: "-60px" });
  const [manualInView, setManualInView] = useState(false);
  const [value, setValue] = useState(0);

  // IntersectionObserver-driven reveal (observerInView) is the primary
  // mechanism. A manual scroll-position fallback covers environments where
  // IntersectionObserver callbacks are deferred (e.g. a backgrounded/hidden
  // document) so the count-up still resolves instead of sticking at 0. A
  // reported viewport height of 0 is never valid in a real browser tab --
  // treat it as "unknown, don't gate on it" rather than "nothing is visible."
  useEffect(() => {
    if (manualInView) return;
    const check = () => {
      const el = ref.current;
      if (!el) return;
      const viewportH = window.innerHeight || document.documentElement.clientHeight;
      if (!viewportH) {
        setManualInView(true);
        return;
      }
      const rect = el.getBoundingClientRect();
      if (rect.top < viewportH && rect.bottom > 0) {
        setManualInView(true);
      }
    };
    check();
    window.addEventListener("scroll", check, { passive: true });
    window.addEventListener("resize", check);
    const poll = setInterval(check, 400);
    return () => {
      window.removeEventListener("scroll", check);
      window.removeEventListener("resize", check);
      clearInterval(poll);
    };
  }, [manualInView]);

  const inView = observerInView || manualInView;

  useEffect(() => {
    if (!inView) return;

    // Animating a count-up nobody can currently see is pointless, and a
    // backgrounded/hidden document throttles requestAnimationFrame anyway --
    // just show the final value immediately in that case.
    if (document.hidden) {
      setValue(to);
      return;
    }

    let raf: number;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / (duration * 1000));
      const eased = 1 - Math.pow(1 - p, 3);
      setValue(to * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    // Safety net: if the tab is backgrounded partway through (rAF throttled
    // to near-zero), don't leave the counter stuck mid-animation forever.
    const settle = setTimeout(() => setValue(to), duration * 1000 + 800);

    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(settle);
    };
  }, [inView, to, duration]);

  return (
    <span ref={ref} className="font-mono-tab tabular-nums">
      {prefix}
      {value.toLocaleString("en-US", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}
      {suffix}
    </span>
  );
}
