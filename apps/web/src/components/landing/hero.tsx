"use client";

import Link from "next/link";

import { CountUp } from "@/components/dashboard/count-up";
import { DarkPanel } from "@/components/dark-panel";
import { ScoreRing } from "@/components/score-ring";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n/provider";
import { getScoreColorOnDark } from "@/lib/utils/score-colors";
import { StatusPill } from "@/src/components/landing/shared";

const SAMPLE_SCORE = 78;

export function Hero() {
  const { t } = useI18n();

  return (
    <DarkPanel className="mx-4" floor id="top">
      <div className="mx-auto grid max-w-6xl gap-12 px-5 py-16 sm:px-8 md:py-20 lg:grid-cols-[1.15fr_1fr] lg:items-center">
        <div>
          <h1 className="max-w-[11ch] text-[clamp(2.5rem,6vw,4.5rem)] font-semibold leading-[1.02] tracking-[-0.025em]">
            {t("landing.heroTitle")}
          </h1>
          <p className="mt-6 max-w-[42ch] text-[17px] font-medium leading-relaxed text-neutral-300">
            {t("landing.heroSubtitle")}
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button asChild size="lg">
              <Link href="/register">{t("landing.heroCta")}</Link>
            </Button>
            <Button
              asChild
              className="border-white/40 text-white hover:border-white"
              size="lg"
              variant="outline"
            >
              <a href="#cuando">{t("landing.heroSecondary")}</a>
            </Button>
          </div>
        </div>

        <div className="rounded-card border border-white/10 bg-[#272725]/90 p-6 backdrop-blur">
          <div className="flex items-center justify-between gap-3 text-[13px] font-medium text-neutral-400">
            <span>{t("landing.sampleResult")}</span>
            <StatusPill surface="dark" tone="ok">
              {t("landing.analysisReady")}
            </StatusPill>
          </div>
          <div className="my-5 flex items-center gap-5">
            <ScoreRing
              className="h-[104px] w-[104px]"
              color={getScoreColorOnDark(SAMPLE_SCORE)}
              label={`${t("landing.sampleRole")}: ${SAMPLE_SCORE}/100`}
              trackColor="#3A3A37"
              value={SAMPLE_SCORE}
            >
              <span className="text-3xl font-semibold tracking-tight">
                <CountUp value={SAMPLE_SCORE} />
              </span>
            </ScoreRing>
            <div>
              <h2 className="text-lg font-semibold leading-tight">{t("landing.sampleRole")}</h2>
              <p className="mt-1 text-[13px] text-neutral-400">{t("landing.sampleCompany")}</p>
            </div>
          </div>
          <ul className="grid gap-2">
            {(
              [
                ["Python", "ok", "landing.met"],
                ["SQL", "mid", "landing.partial"],
                ["Docker", "bad", "landing.missing"]
              ] as const
            ).map(([skill, tone, statusKey]) => (
              <li
                className="flex items-center justify-between rounded-xl bg-[#1F1F1D] px-3.5 py-2.5 text-sm font-medium"
                key={skill}
              >
                {skill}
                <StatusPill surface="dark" tone={tone}>
                  {t(statusKey)}
                </StatusPill>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </DarkPanel>
  );
}
