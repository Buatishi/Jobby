"use client";

import { FileSearch, Gauge, MessageSquareText, TriangleAlert, Wand2, type LucideIcon } from "lucide-react";

import { useI18n } from "@/lib/i18n/provider";
import { cn } from "@/lib/utils";
import { SectionHead } from "@/src/components/landing/shared";

type Feature = {
  id: "match" | "ats" | "gap" | "optimizer" | "kit";
  icon: LucideIcon;
  includes: number;
  premium?: boolean;
};

const features: Feature[] = [
  { id: "match", icon: Gauge, includes: 3 },
  { id: "ats", icon: FileSearch, includes: 3 },
  { id: "gap", icon: TriangleAlert, includes: 2 },
  { id: "optimizer", icon: Wand2, includes: 3 },
  { id: "kit", icon: MessageSquareText, includes: 4, premium: true }
];

const ordinals = ["One", "Two", "Three", "Four"];

export function Features() {
  const { t } = useI18n();

  return (
    <section className="mx-auto max-w-6xl px-5 pt-28 sm:px-8" id="funciones">
      <SectionHead eyebrow={t("landing.featuresEyebrow")} title={t("landing.featuresTitle")} />
      <div className="grid gap-5 md:grid-cols-2">
        {features.map((feature, index) => {
          const Icon = feature.icon;
          const isLast = index === features.length - 1;

          return (
            <article
              className={cn(
                "rounded-card border border-brand-line bg-white p-7 shadow-card",
                isLast && "md:col-span-2"
              )}
              key={feature.id}
            >
              <div className="flex items-center gap-3.5">
                <span className="flex h-11 w-11 flex-none items-center justify-center rounded-[14px] bg-brand-ink text-brand-bright">
                  <Icon aria-hidden="true" className="h-[22px] w-[22px]" />
                </span>
                <h3 className="text-[19px] font-semibold tracking-tight">
                  {t(`landing.features.${feature.id}Title`)}
                </h3>
                {feature.premium ? (
                  <span className="ml-auto rounded-full bg-brand-ink px-2.5 py-0.5 text-[11px] font-bold text-brand-bright">
                    {t("common.premium")}
                  </span>
                ) : null}
              </div>
              <p className="mt-3.5 max-w-[56ch] text-sm font-medium text-neutral-600">
                {t(`landing.features.${feature.id}Description`)}
              </p>
              <p className="mt-4 text-xs font-semibold text-neutral-500">{t("landing.includes")}</p>
              <ul className="mt-2 flex flex-wrap gap-2">
                {Array.from({ length: feature.includes }, (_, i) => (
                  <li
                    className="rounded-full bg-brand-green-light px-3 py-1 text-xs font-semibold text-brand-green"
                    key={i}
                  >
                    {t(`landing.features.${feature.id}${ordinals[i]}`)}
                  </li>
                ))}
              </ul>
            </article>
          );
        })}
      </div>
    </section>
  );
}
