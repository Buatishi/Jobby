"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { Check } from "lucide-react";

import { LanguageToggle } from "@/components/language-toggle";
import { MatchScoreCard } from "@/components/match-score-card";
import { useI18n } from "@/lib/i18n/provider";

type AuthLayoutProps = {
  children: ReactNode;
  headline: string;
};

const bulletKeys = ["auth.bulletMatch", "auth.bulletKit", "auth.bulletFree"];

export function AuthLayout({ children, headline }: AuthLayoutProps) {
  const { t } = useI18n();

  return (
    <main className="grid min-h-screen bg-white md:grid-cols-[58%_42%]">
      <section className="relative overflow-hidden bg-[#0F6E56] px-6 py-8 text-white md:min-h-screen md:px-12 md:py-16 lg:px-16">
        {/* Fondo decorativo fuera del flujo: usa z-0 y no contiene texto ni controles. */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(circle_at_20%_10%,rgba(255,255,255,0.18),transparent_30%),linear-gradient(135deg,#0F6E56_0%,#064536_100%)]"
        />
        <div className="relative z-10 flex min-h-[140px] flex-col md:min-h-[calc(100vh-8rem)] md:justify-center">
          <div className="max-w-xl md:pt-20">
            <h1 className="max-w-lg text-3xl font-black leading-tight tracking-tight md:text-5xl">
              {headline}
            </h1>
            <p className="mt-5 max-w-md text-sm font-medium leading-6 text-white/75 md:text-base">
              {t("auth.layoutSubtitle")}
            </p>
            <div className="mt-8 hidden space-y-4 md:block">
              {bulletKeys.map((bulletKey) => (
                <div className="flex items-center gap-3" key={bulletKey}>
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white/12 text-white">
                    <Check className="h-4 w-4" />
                  </span>
                  <span className="text-sm font-semibold text-white/88">
                    {t(bulletKey)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-12 hidden w-full max-w-md rotate-[-2deg] md:block">
            <MatchScoreCard compact />
          </div>
        </div>
      </section>

      <section className="flex min-h-[calc(100vh-140px)] flex-col bg-[#fbfcfb] px-6 py-8 md:min-h-screen md:px-10 lg:px-14">
        <div className="mb-10 flex items-center justify-between gap-4">
          <Link
            className="inline-flex w-fit text-xl font-black tracking-tight text-foreground transition-colors duration-200 hover:text-[#0F6E56] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0F6E56]"
            href="/"
          >
            Jobby
          </Link>
          <LanguageToggle compact />
        </div>
        <div className="flex flex-1 items-center">
          <div className="mx-auto w-full max-w-md rounded-3xl border border-black/5 bg-white p-6 shadow-[0_24px_80px_rgba(15,23,42,0.08)] sm:p-8">
            {children}
          </div>
        </div>
      </section>
    </main>
  );
}
