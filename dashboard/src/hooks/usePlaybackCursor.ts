import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "framer-motion";

/**
 * Loops an index from 0..length-1 on an interval, pausing at the end briefly before restarting.
 * With "reduce motion" set, it does not animate and returns the final index (the full trace).
 */
export function usePlaybackCursor(length: number, stepMs = 45, holdMs = 900) {
  const reduceMotion = useReducedMotion();
  const [index, setIndex] = useState(0);
  const holding = useRef(false);

  useEffect(() => {
    if (length <= 1 || reduceMotion) return;
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
  }, [length, stepMs, holdMs, reduceMotion]);

  useEffect(() => {
    if (index >= length - 1 && length > 1 && !reduceMotion) {
      const t = setTimeout(() => setIndex(0), holdMs);
      return () => clearTimeout(t);
    }
  }, [index, length, holdMs, reduceMotion]);

  return reduceMotion ? Math.max(length - 1, 0) : index;
}
