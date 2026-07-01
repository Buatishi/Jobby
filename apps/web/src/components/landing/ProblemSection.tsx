"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";

export function ProblemSection() {
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
          Postulás a 50 puestos. Te responden 3.
        </h2>
        <p className="mt-6 text-lg font-medium leading-8 text-black/65">
          La mayoría de los rechazos no son por falta de skills — son por gaps
          invisibles: cómo lee tu CV el ATS, si tu seniority matchea, o si tu
          perfil está bien representado.
        </p>
      </motion.div>
    </section>
  );
}
