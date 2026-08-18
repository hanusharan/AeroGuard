import { motion } from "framer-motion";

/**
 * Decorative hero visualization: a climbing flight-path vector approaching
 * the stall boundary, with a probability readout rising ahead of the
 * crossing. Illustrative motion graphic, not a data-bound chart -- the real,
 * data-bound version of this idea is the Flight Replay section below.
 */
export function HeroTrajectory() {
  const width = 640;
  const height = 380;
  const boundaryY = 108;

  // A climbing, two-stage "staircase" path loosely evoking the real
  // gradual_approach_v3 alpha trace shape (see Physics Engine section).
  const pathD =
    "M 10 320 C 90 316, 140 300, 190 270 C 230 246, 250 236, 270 236 " +
    "C 300 236, 320 250, 340 220 C 365 182, 380 150, 420 128 " +
    "C 450 112, 470 108, 500 96 C 540 80, 570 60, 610 34";

  return (
    <div className="relative mx-auto w-full max-w-3xl select-none">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full overflow-visible"
        role="img"
        aria-label="Animated flight-path vector climbing toward the stall boundary, with an AI warning marker appearing before the crossing"
      >
        <defs>
          <linearGradient id="pathGrad" x1="0" y1="1" x2="1" y2="0">
            <stop offset="0%" stopColor="#4fd6ff" stopOpacity="0.35" />
            <stop offset="65%" stopColor="#4fd6ff" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#ff5f56" stopOpacity="0.95" />
          </linearGradient>
          <radialGradient id="glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#4fd6ff" stopOpacity="0.55" />
            <stop offset="100%" stopColor="#4fd6ff" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* horizon grid */}
        {Array.from({ length: 7 }).map((_, i) => (
          <line
            key={`h${i}`}
            x1={0}
            x2={width}
            y1={40 + i * 48}
            y2={40 + i * 48}
            stroke="rgba(255,255,255,0.05)"
            strokeWidth={1}
          />
        ))}

        {/* stall boundary line */}
        <line
          x1={0}
          x2={width}
          y1={boundaryY}
          y2={boundaryY}
          stroke="#ff5f56"
          strokeOpacity={0.45}
          strokeWidth={1.5}
          strokeDasharray="3 7"
        />
        <text x={width - 4} y={boundaryY - 10} textAnchor="end" className="font-mono-tab" fontSize={11} fill="#ff8a82" opacity={0.85}>
          STALL BOUNDARY · 16.07°
        </text>

        {/* flight path, animated draw-on */}
        <motion.path
          d={pathD}
          fill="none"
          stroke="url(#pathGrad)"
          strokeWidth={2.5}
          strokeLinecap="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 3.2, ease: [0.16, 1, 0.3, 1], repeat: Infinity, repeatDelay: 1.4 }}
        />

        {/* AI warning marker, appears partway along the path -- well before the endpoint crosses the boundary line */}
        <motion.g
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 0, 1, 1, 0] }}
          transition={{ duration: 4.6, times: [0, 0.42, 0.5, 0.88, 1], repeat: Infinity, repeatDelay: 0 }}
        >
          <circle cx={352} cy={214} r="22" fill="url(#glow)" />
          <circle cx={352} cy={214} r="4.5" fill="#4fd6ff" />
          <text x={352} y={192} textAnchor="middle" className="font-mono-tab" fontSize={11} fontWeight={600} fill="#4fd6ff">
            WARNING
          </text>
        </motion.g>

        {/* aircraft glyph riding the leading edge of the path */}
        <motion.g
          initial={{ offsetDistance: "0%" }}
          animate={{ offsetDistance: "100%" }}
          transition={{ duration: 3.2, ease: [0.16, 1, 0.3, 1], repeat: Infinity, repeatDelay: 1.4 }}
          style={{ offsetPath: `path("${pathD}")`, offsetRotate: "auto" }}
        >
          <g transform="translate(-9,-9) rotate(90)">
            <path
              d="M9 0 L13 9 L9 7 L5 9 Z M9 7 L9 15 M4 12 L14 12"
              fill="#eef2f5"
              stroke="#eef2f5"
              strokeWidth={1.1}
              strokeLinejoin="round"
            />
          </g>
        </motion.g>
      </svg>
    </div>
  );
}
