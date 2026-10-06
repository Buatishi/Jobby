"use client";

import { CircleCheck, Download, Gauge, Gift, Lock, Star, Wand2, type LucideIcon } from "lucide-react";

import { useI18n } from "@/lib/i18n/provider";
import { SectionHead } from "@/src/components/landing/shared";

type PromiseCard = { id: string; icon: LucideIcon };

// Columnas de dos tarjetas: la del medio sube y las laterales bajan, como en la referencia.
const columns: PromiseCard[][] = [
  [
    { id: "one", icon: Wand2 },
    { id: "two", icon: Gauge }
  ],
  [
    { id: "three", icon: Lock },
    { id: "four", icon: Download }
  ],
  [
    { id: "five", icon: Gift },
    { id: "six", icon: Star }
  ]
];

export function Promises() {
  const { t } = useI18n();

  return (
    <section className="mx-auto max-w-6xl px-5 pt-28 sm:px-8" id="promesas">
      <SectionHead eyebrow={t("landing.promisesEyebrow")} title={t("landing.promisesTitle")} />
      <div className="grid items-start gap-5 md:grid-cols-3">
        {columns.map((column, columnIndex) => (
          <div className={`grid gap-5 ${columnIndex % 2 === 0 ? "md:mt-10" : ""}`} key={columnIndex}>
            {column.map(({ id, icon: Icon }) => (
              <article
                className="grid gap-3.5 rounded-card border border-brand-line bg-white p-6 shadow-card"
                key={id}
              >
                <CircleCheck aria-hidden="true" className="h-5 w-5 text-brand-green" />
                <h3 className="text-base font-semibold tracking-tight">{t(`landing.promises.${id}Title`)}</h3>
                <p className="text-sm font-medium italic leading-relaxed text-neutral-600">
                  {t(`landing.promises.${id}Text`)}
                </p>
                <footer className="flex items-center gap-2.5 text-xs font-semibold text-neutral-600">
                  <span className="flex h-[30px] w-[30px] items-center justify-center rounded-full bg-brand-green-light text-brand-green">
                    <Icon aria-hidden="true" className="h-4 w-4" />
                  </span>
                  {t(`landing.promises.${id}Tag`)}
                </footer>
              </article>
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}
