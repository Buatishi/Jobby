"use client";

import { useI18n } from "@/lib/i18n/provider";

const placeholderCards = [0, 1, 2];

/** Se muestra al instante al cambiar de sección, mientras llega la página nueva. */
export default function SectionLoading() {
  const { t } = useI18n();

  return (
    <main aria-busy="true" className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:py-8">
      <p className="sr-only" role="status">
        {t("status.loadingSection")}
      </p>
      <div aria-hidden="true" className="motion-safe:animate-pulse">
        <div className="h-4 w-28 rounded bg-muted" />
        <div className="mt-3 h-8 w-72 max-w-full rounded bg-muted" />
        <div className="mt-3 h-4 w-96 max-w-full rounded bg-muted/70" />
        <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {placeholderCards.map((card) => (
            <div className="rounded-lg border border-border bg-background p-6" key={card}>
              <div className="h-5 w-2/3 rounded bg-muted" />
              <div className="mt-3 h-4 w-1/2 rounded bg-muted/70" />
              <div className="mt-8 h-9 w-full rounded bg-muted/70" />
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
