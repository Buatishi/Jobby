"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { Check } from "lucide-react";

import { CountUp } from "@/components/dashboard/count-up";
import { DarkPanel } from "@/components/dark-panel";
import { LanguageToggle } from "@/components/language-toggle";
import { ScoreRing } from "@/components/score-ring";
import { useI18n } from "@/lib/i18n/provider";
import { getScoreColorOnDark } from "@/lib/utils/score-colors";
import { StatusPill } from "@/src/components/landing/shared";

type AuthLayoutProps = {
  children: ReactNode;
  headline: string;
};

const bulletKeys = ["auth.bulletMatch", "auth.bulletKit", "auth.bulletFree"];
const SAMPLE_SCORE = 78;

export function AuthLayout({ children, headline }: AuthLayoutProps) {
  const { t } = useI18n();

  return (
    <main className="grid min-h-screen bg-white md:grid-cols-[58%_42%]">
      <div className="p-3 md:p-4">
        <DarkPanel className="h-full min-h-[140px]" floor>
          <div className="flex min-h-[140px] flex-col px-6 py-8 md:min-h-[calc(100vh-2rem)] md:justify-center md:px-12 md:py-16 lg:px-16">
            <div className="max-w-xl">
              <h1 className="max-w-lg text-3xl font-semibold leading-tight tracking-tight md:text-5xl">
                {headline}
              </h1>
              <p className="mt-5 max-w-md text-sm font-medium leading-6 text-neutral-300 md:text-base">
                {t("auth.layoutSubtitle")}
              </p>
              <div className="mt-8 hidden space-y-4 md:block">
                {bulletKeys.map((bulletKey) => (
                  <div className="flex items-center gap-3" key={bulletKey}>
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-bright/15 text-brand-bright">
                      <Check className="h-4 w-4" />
                    </span>
                    <span className="text-sm font-semibold text-white/90">{t(bulletKey)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-12 hidden w-full max-w-sm rounded-card border border-white/10 bg-[#272725]/90 p-5 backdrop-blur md:block">
              <div className="flex items-center gap-4">
                <ScoreRing
                  className="h-20 w-20"
                  color={getScoreColorOnDark(SAMPLE_SCORE)}
                  label={`${t("landing.sampleRole")}: ${SAMPLE_SCORE}/100`}
                  trackColor="#3A3A37"
                  value={SAMPLE_SCORE}
                >
                  <span className="text-2xl font-semibold">
                    <CountUp value={SAMPLE_SCORE} />
                  </span>
                </ScoreRing>
                <div>
                  <p className="text-sm font-semibold">{t("landing.sampleRole")}</p>
                  <p className="mt-0.5 text-xs text-neutral-400">{t("landing.sampleResult")}</p>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <StatusPill surface="dark" tone="ok">
                  Python: {t("landing.met")}
                </StatusPill>
                <StatusPill surface="dark" tone="mid">
                  SQL: {t("landing.partial")}
                </StatusPill>
                <StatusPill surface="dark" tone="bad">
                  Docker: {t("landing.missing")}
                </StatusPill>
              </div>
            </div>
          </div>
        </DarkPanel>
      </div>

      <section className="flex min-h-[calc(100vh-140px)] flex-col bg-white px-6 py-8 md:min-h-screen md:px-10 lg:px-14">
        <div className="mb-10 flex items-center justify-between gap-4">
          <Link
            className="inline-flex w-fit items-center gap-2 text-xl font-bold tracking-tight text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-green"
            href="/"
          >
            <span
              aria-hidden="true"
              className="flex h-[30px] w-[30px] items-center justify-center rounded-[10px] bg-brand-bright text-[17px]"
            >
              J
            </span>
            Jobby
          </Link>
          <LanguageToggle compact />
        </div>
        <div className="flex flex-1 items-center">
          <div className="mx-auto w-full max-w-md rounded-panel border border-brand-line bg-white p-6 shadow-card sm:p-8">
            {children}
          </div>
        </div>
      </section>
    </main>
  );
}
