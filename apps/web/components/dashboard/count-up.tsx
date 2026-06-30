"use client";

import { useEffect, useState } from "react";

type CountUpProps = {
  value: number;
  durationMs?: number;
};

export function CountUp({ value, durationMs = 800 }: CountUpProps) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    let animationFrame = 0;
    const startedAt = performance.now();

    function tick(now: number) {
      const progress = Math.min((now - startedAt) / durationMs, 1);
      setDisplayValue(Math.round(value * progress));

      if (progress < 1) {
        animationFrame = requestAnimationFrame(tick);
      }
    }

    animationFrame = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(animationFrame);
  }, [durationMs, value]);

  return <>{displayValue}</>;
}
