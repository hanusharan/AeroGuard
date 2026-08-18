import { useEffect, useRef, useState } from "react";

export function useScrubber(length: number, stepMs = 60) {
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(true);
  const raf = useRef<number | null>(null);
  const last = useRef(0);

  useEffect(() => {
    if (!playing) return;
    const tick = (now: number) => {
      if (now - last.current >= stepMs) {
        last.current = now;
        setIndex((i) => (i >= length - 1 ? 0 : i + 1));
      }
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [playing, length, stepMs]);

  return {
    index,
    setIndex,
    playing,
    togglePlaying: () => setPlaying((p) => !p),
    play: () => setPlaying(true),
    pause: () => setPlaying(false),
  };
}
