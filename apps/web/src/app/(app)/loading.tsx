"use client";

import { useI18n } from "@/lib/i18n/provider";

const placeholderCards = [0, 1, 2];

/** Se muestra al instante al cambiar de sección, mientras llega la página nueva. */
export default function SectionLoading() {
  const { t } = useI18n();

  return (
    <main aria-busy="true" className="min-h-screen bg-white p-4">
      <p className="sr-only" role="status">
        {t("status.loadingSection")}
      </p>
      <div aria-hidden="true" className="motion-safe:animate-pulse">
        <div className="h-44 rounded-panel bg-brand-ink/90" />
        <div className="mt-5 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {placeholderCards.map((card) => (
            <div className="rounded-card border border-border bg-background p-6" key={card}>
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
