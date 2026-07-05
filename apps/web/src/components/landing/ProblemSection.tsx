"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";

import { useI18n } from "@/lib/i18n/provider";

export function ProblemSection() {
  const { t } = useI18n();
  const ref = useRef<HTMLElement>(null);
  const isInView = useInView(ref, { amount: 0.2, once: true });

  return (
    <section className="bg-muted/30 px-5 py-20 sm:px-8" ref={ref}>
      <motion.div
        animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
        className="mx-auto max-w-3xl text-center"
        initial={{ opacity: 0, y: 20 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
      >
        <h2 className="text-3xl font-black tracking-tight text-black md:text-5xl">
          {t("landing.problemTitle")}
        </h2>
        <p className="mt-6 text-lg font-medium leading-8 text-black/65">
          {t("landing.problemSubtitle")}
        </p>
      </motion.div>
    </section>
  );
}
