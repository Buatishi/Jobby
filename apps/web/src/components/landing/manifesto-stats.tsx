"use client";

import { CountUp } from "@/components/dashboard/count-up";
import { DarkPanel } from "@/components/dark-panel";
import { ScoreRing } from "@/components/score-ring";
import { useI18n } from "@/lib/i18n/provider";
import { getScoreColorOnDark } from "@/lib/utils/score-colors";
import { Eyebrow } from "@/src/components/landing/shared";

const stats = [
  { value: 3, labelKey: "landing.statOptimizations" },
  { value: 10, labelKey: "landing.statAnalyses" },
  { value: 100, labelKey: "landing.statPoints" }
];

export function ManifestoStats() {
  const { t } = useI18n();

  return (
    <section className="mx-auto max-w-6xl px-5 pt-28 sm:px-8">
      <div className="mb-8 flex justify-center">
        <Eyebrow>{t("landing.manifestoEyebrow")}</Eyebrow>
      </div>

      <div className="grid items-center gap-6 rounded-panel border border-brand-line bg-white p-6 shadow-card md:grid-cols-[auto_1fr] md:gap-10 md:px-11 md:py-9">
        <DarkPanel className="h-[170px] w-full md:h-[200px] md:w-[200px]">
          <div className="flex h-[170px] items-center justify-center md:h-[200px]">
            <ScoreRing
              className="h-[130px] w-[130px]"
              color={getScoreColorOnDark(78)}
              label="78/100"
              trackColor="#3A3A37"
              value={78}
            >
              <span className="text-[40px] font-semibold">78</span>
            </ScoreRing>
          </div>
        </DarkPanel>
        <blockquote>
          <p className="text-[clamp(1.25rem,2.4vw,1.625rem)] font-semibold leading-snug tracking-tight">
            {t("landing.manifestoQuote")}
          </p>
          <footer className="mt-4 text-[13px] font-semibold text-neutral-600">
            <strong className="block text-brand-ink">{t("landing.manifestoAuthor")}</strong>
            {t("landing.manifestoNote")}
          </footer>
        </blockquote>
      </div>

      <div className="mt-5 grid gap-5 md:grid-cols-3">
        {stats.map((stat) => (
          <div
            className="rounded-card border border-brand-line bg-white px-5 py-7 text-center shadow-card"
            key={stat.labelKey}
          >
            <div className="text-[clamp(3.25rem,7vw,5.25rem)] font-semibold italic leading-none tracking-[-0.04em] text-brand-green">
              <CountUp durationMs={1200} value={stat.value} />
            </div>
            <p className="mt-3 text-[13px] font-semibold text-neutral-600">{t(stat.labelKey)}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
