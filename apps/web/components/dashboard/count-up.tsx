"use client";

import { useEffect, useRef, useState } from "react";

type CountUpProps = {
  value: number;
  durationMs?: number;
};

export function CountUp({ value, durationMs = 800 }: CountUpProps) {
  const elementRef = useRef<HTMLSpanElement | null>(null);
  const [displayValue, setDisplayValue] = useState(0);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const element = elementRef.current;

    if (!element) {
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.35 }
    );

    observer.observe(element);

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!isVisible) {
      return;
    }

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
  }, [durationMs, isVisible, value]);

  return <span ref={elementRef}>{displayValue}</span>;
}
