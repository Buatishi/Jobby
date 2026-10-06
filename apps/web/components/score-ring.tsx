"use client";

import { useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

type ScoreRingProps = {
  value: number;
  color: string;
  trackColor: string;
  label: string;
  strokeWidth?: number;
  className?: string;
  children?: React.ReactNode;
};

export function clampRingValue(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }

  return Math.max(0, Math.min(100, value));
}

// Anillo de match: se dibuja una vez al aparecer y respeta "reducir movimiento".
export function ScoreRing({
  value,
  color,
  trackColor,
  label,
  strokeWidth = 9,
  className,
  children
}: ScoreRingProps) {
  const reduceMotion = useReducedMotion();
  const [isDrawn, setIsDrawn] = useState(false);

  useEffect(() => {
    if (reduceMotion) {
      setIsDrawn(true);
      return;
    }

    const frame = requestAnimationFrame(() => setIsDrawn(true));

    return () => cancelAnimationFrame(frame);
  }, [reduceMotion]);

  const radius = 50 - strokeWidth / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = isDrawn
    ? circumference * (1 - clampRingValue(value) / 100)
    : circumference;

  return (
    <div className={cn("relative flex-none", className)}>
      <svg
        aria-label={label}
        className="h-full w-full -rotate-90"
        role="img"
        viewBox="0 0 100 100"
      >
        <circle
          cx="50"
          cy="50"
          fill="none"
          r={radius}
          stroke={trackColor}
          strokeWidth={strokeWidth}
        />
        <circle
          cx="50"
          cy="50"
          fill="none"
          r={radius}
          stroke={color}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          strokeWidth={strokeWidth}
          style={{
            transition: reduceMotion
              ? "none"
              : "stroke-dashoffset 1.1s cubic-bezier(0.2, 0.7, 0.2, 1)"
          }}
        />
      </svg>
      {children ? (
        <div className="absolute inset-0 flex items-center justify-center">
          {children}
        </div>
      ) : null}
    </div>
  );
}
