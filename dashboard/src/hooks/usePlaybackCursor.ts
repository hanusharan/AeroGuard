import { useEffect, useRef, useState } from "react";

/** Loops an index from 0..length-1 on an interval, pausing at the end briefly before restarting. */
export function usePlaybackCursor(length: number, stepMs = 45, holdMs = 900) {
  const [index, setIndex] = useState(0);
  const holding = useRef(false);

  useEffect(() => {
    if (length <= 1) return;
    const id = setInterval(() => {
      setIndex((prev) => {
        if (holding.current) return prev;
        if (prev >= length - 1) {
          holding.current = true;
          setTimeout(() => {
            holding.current = false;
          }, holdMs);
          return prev;
        }
        return prev + 1;
      });
    }, stepMs);
    return () => clearInterval(id);
  }, [length, stepMs, holdMs]);

  useEffect(() => {
    if (index >= length - 1 && length > 1) {
      const t = setTimeout(() => setIndex(0), holdMs);
      return () => clearTimeout(t);
    }
  }, [index, length, holdMs]);

  return index;
}
