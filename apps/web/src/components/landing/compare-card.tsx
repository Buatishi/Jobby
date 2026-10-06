"use client";

import { useI18n } from "@/lib/i18n/provider";
import { PillRow, StatusPill } from "@/src/components/landing/shared";

export function CompareCard() {
  const { t } = useI18n();
  const rows = [
    { skill: "Python", note: t("landing.comparePythonNote"), tone: "ok", status: t("landing.met") },
    { skill: "SQL", note: t("landing.compareSqlNote"), tone: "mid", status: t("landing.partial") },
    { skill: "Docker", note: t("landing.compareDockerNote"), tone: "bad", status: t("landing.missing") }
  ] as const;

  return (
    <section className="mx-auto max-w-6xl px-5 sm:px-8">
      <div className="grid items-center gap-12 rounded-panel border border-brand-line bg-white p-7 shadow-card md:p-14 lg:grid-cols-2">
        <div>
          <h2 className="text-[clamp(1.75rem,3.4vw,2.5rem)] font-semibold leading-[1.12] tracking-[-0.02em]">
            {t("landing.resultTitle")}
          </h2>
          <p className="mt-3.5 max-w-[44ch] text-[15px] font-medium text-neutral-600">
            {t("landing.resultSubtitle")}
          </p>
          <div className="mt-7 grid gap-3">
            <PillRow strong={t("landing.pillMatchStrong")}>{t("landing.pillMatchRest")}</PillRow>
            <PillRow strong={t("landing.pillAtsStrong")}>{t("landing.pillAtsRest")}</PillRow>
            <PillRow strong={t("landing.pillGapsStrong")}>{t("landing.pillGapsRest")}</PillRow>
          </div>
        </div>

        <div aria-label={t("landing.sampleData")} className="rounded-card bg-brand-green-light p-5">
          <h3 className="mb-3 text-sm font-semibold text-brand-green">{t("landing.compareTitle")}</h3>
          <ul className="grid gap-2">
            {rows.map((row) => (
              <li
                className="flex items-center justify-between gap-3 rounded-[14px] bg-white px-4 py-3 text-sm font-medium"
                key={row.skill}
              >
                <div>
                  {row.skill}
                  <small className="block text-xs font-medium text-neutral-500">{row.note}</small>
                </div>
                <StatusPill tone={row.tone}>{row.status}</StatusPill>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
