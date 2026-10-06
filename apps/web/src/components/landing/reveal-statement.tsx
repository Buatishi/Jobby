"use client";

import { useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

import { useI18n } from "@/lib/i18n/provider";
import { litWords, revealProgress } from "@/lib/landing/reveal";
import { cn } from "@/lib/utils";

// Frase grande que se pinta de verde palabra por palabra mientras se scrollea.
export function RevealStatement() {
  const { t } = useI18n();
  const reduceMotion = useReducedMotion();
  const paragraphRef = useRef<HTMLParagraphElement>(null);
  const [lit, setLit] = useState(0);
  const words = t("landing.statement").split(/\s+/);

  useEffect(() => {
    if (reduceMotion) {
      setLit(words.length);
      return;
    }

    let frame = 0;

    function update() {
      const element = paragraphRef.current;

      if (!element) {
        return;
      }

      const rect = element.getBoundingClientRect();
      setLit(litWords(revealProgress(rect.top, rect.height, window.innerHeight), words.length));
    }

    function onScroll() {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(update);
    }

    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, [reduceMotion, words.length]);

  return (
    <section className="px-5 pb-[110px] pt-[130px] text-center sm:px-8 max-md:pb-[72px] max-md:pt-[88px]">
      <p
        className="mx-auto max-w-[26ch] text-[clamp(1.625rem,3.6vw,2.5rem)] font-semibold leading-[1.28] tracking-[-0.015em]"
        ref={paragraphRef}
      >
        {words.map((word, index) => (
          <span
            className={cn(
              "transition-colors duration-300",
              index < lit ? "text-brand-green" : "text-[#C9DDD5]"
            )}
            key={`${word}-${index}`}
          >
            {word}{" "}
          </span>
        ))}
      </p>
    </section>
  );
}
