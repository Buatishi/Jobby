"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { GUIDE_LINKS } from "@/lib/guides/links";
import { useI18n } from "@/lib/i18n/provider";
import { SectionHead } from "@/src/components/landing/shared";

// Las guías también están en el pie. Acá van en el cuerpo de la home, para que cada una tenga
// un enlace visible desde la página principal y no solo uno entre los del pie.
export function GuidesSection() {
  const { t } = useI18n();

  return (
    <section className="mx-auto max-w-6xl px-5 pt-28 sm:px-8" id="guias">
      <SectionHead
        eyebrow={t("landing.guides")}
        subtitle={t("landing.guidesSubtitle")}
        title={t("landing.guidesTitle")}
      />
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {GUIDE_LINKS.map((guide) => (
          <li key={guide.slug}>
            <Link
              className="group flex h-full items-center justify-between gap-3 rounded-card border border-brand-line bg-white p-5 text-sm font-semibold tracking-tight shadow-card transition-colors hover:bg-brand-green-light"
              href={`/guias/${guide.slug}`}
            >
              {guide.label}
              <ArrowRight
                aria-hidden="true"
                className="h-4 w-4 flex-none text-brand-green transition-transform group-hover:translate-x-0.5 motion-reduce:transition-none"
              />
            </Link>
          </li>
        ))}
      </ul>
      <p className="mt-8 text-center">
        <Link className="text-sm font-semibold text-brand-green hover:underline" href="/guias">
          {t("landing.guidesAll")}
        </Link>
      </p>
    </section>
  );
}
