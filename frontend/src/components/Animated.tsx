"use client";

import { useEffect, useState } from "react";

/** Läuft beim Einblenden von 0 auf `to` (easeOutCubic). */
function useProgress(duration = 900, delay = 150) {
  const [t, setT] = useState(0);
  useEffect(() => {
    // Weniger Bewegung gewünscht: sofort im ersten Frame am Ziel
    const instant = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let frame = 0;
    const start = performance.now() + delay;
    const step = (now: number) => {
      const p = instant ? 1 : Math.min(1, Math.max(0, (now - start) / duration));
      setT(1 - (1 - p) ** 3);
      if (p < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [duration, delay]);
  return t;
}

/** Zahl, die beim Laden hochzählt. */
export function CountUp({ to, className }: { to: number; className?: string }) {
  const t = useProgress();
  return <span className={`tabular-nums ${className ?? ""}`}>{Math.round(to * t)}</span>;
}

/** Fortschrittsring, der sich beim Laden füllt. `value` von 0 bis 1. */
export function ProgressRing({
  value,
  size = 84,
  stroke = 7,
  children,
}: {
  value: number;
  size?: number;
  stroke?: number;
  children?: React.ReactNode;
}) {
  const t = useProgress(1100, 200);
  const r = (size - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const shown = Math.min(1, Math.max(0, value)) * t;
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--surface-2)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="url(#ring-gradient)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - shown)}
        />
        <defs>
          <linearGradient id="ring-gradient" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#bef264" />
            <stop offset="100%" stopColor="#65a30d" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">{children}</div>
    </div>
  );
}
