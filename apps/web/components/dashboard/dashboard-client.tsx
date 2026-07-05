"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  BriefcaseBusiness,
  CalendarDays,
  CircleUserRound,
  Loader2,
  Sparkles
} from "lucide-react";

import { CountUp } from "@/components/dashboard/count-up";
import { JobInputForm } from "@/components/job-input-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { useI18n } from "@/lib/i18n/provider";
import { getScoreColor, getScoreLabel } from "@/lib/utils/score-colors";

type DashboardMatch = {
  id: string;
  company?: string | null;
  company_name?: string | null;
  role?: string | null;
  title?: string | null;
  job_title?: string | null;
  score?: number | null;
  match_score?: number | null;
  created_at?: string | null;
  analyzed_at?: string | null;
};

type DashboardSummary = {
  user_name?: string | null;
  full_name?: string | null;
  email?: string | null;
  user_email?: string | null;
  name?: string | null;
  employability_score?: number | null;
  global_score?: number | null;
  completeness_pct?: number | null;
  completeness?: number | null;
  missing_tip?: string | null;
  most_valuable_missing_field?: string | null;
  latest_matches?: DashboardMatch[] | null;
  matches?: DashboardMatch[] | null;
};

const dashboardCardClass =
  "rounded-2xl border border-neutral-100 bg-white shadow-sm";

function clampScore(value: number | null | undefined) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return 0;
  }

  return Math.max(0, Math.min(100, Math.round(value)));
}

function getFirstName(summary: DashboardSummary | null) {
  const fullName = summary?.full_name?.trim();
  if (fullName) {
    return fullName.split(/\s+/)[0] ?? "";
  }

  const rawName =
    summary?.email ?? summary?.user_email ?? summary?.user_name ?? summary?.name ?? "";
  const cleanName = rawName.includes("@") ? rawName.split("@")[0] : rawName;

  return cleanName.trim().split(/\s+/)[0] ?? "";
}

type ScoreCardProps = {
  title: string;
  value: number;
  description?: string;
  variant?: "linear" | "circular";
  action?: React.ReactNode;
};

function ScoreCard({
  title,
  value,
  description,
  variant = "linear",
  action
}: ScoreCardProps) {
  const color = getScoreColor(value);
  const label = description ?? getScoreLabel(value);
  const radius = 48;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  return (
    <Card className={dashboardCardClass}>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg font-semibold">{title}</CardTitle>
      </CardHeader>
      <CardContent className="pb-8">
        {variant === "circular" ? (
          <div className="flex flex-col items-center">
            <div className="relative h-48 w-48">
              <svg
                aria-label={`${title} ${value}%`}
                className="h-full w-full -rotate-90"
                role="img"
                viewBox="0 0 120 120"
              >
                <circle
                  cx="60"
                  cy="60"
                  fill="none"
                  r={radius}
                  stroke="#e5e7eb"
                  strokeLinecap="round"
                  strokeWidth="8"
                />
                <circle
                  cx="60"
                  cy="60"
                  fill="none"
                  r={radius}
                  stroke={color}
                  strokeDasharray={circumference}
                  strokeDashoffset={offset}
                  strokeLinecap="round"
                  strokeWidth="8"
                  className="transition-all duration-700"
                >
                  <animate
                    attributeName="stroke-dashoffset"
                    dur="800ms"
                    fill="freeze"
                    from={circumference}
                    to={offset}
                  />
                </circle>
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                <p className="text-5xl font-bold leading-none text-black">
                  <CountUp value={value} />%
                </p>
                <p className="mt-2 text-sm font-medium text-neutral-500">
                  Meta: 100%
                </p>
              </div>
            </div>
            {action ? <div className="mt-4">{action}</div> : null}
          </div>
        ) : (
          <div>
            <div className="flex items-end gap-3">
              <p className="text-5xl font-bold leading-none text-black">
                <CountUp value={value} />
              </p>
              <span className="pb-1 text-sm font-medium text-neutral-500">/100</span>
            </div>
            <p className="mt-3 text-sm font-semibold" style={{ color }}>
              {label}
            </p>
            <div className="mt-6 h-3 overflow-hidden rounded-full bg-neutral-100">
              <div
                className="h-full rounded-full transition-[width] duration-700"
                style={{ backgroundColor: color, width: `${value}%` }}
              />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function DashboardClient() {
  const { language, t } = useI18n();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadSummary() {
      try {
        const response = await apiClient<DashboardSummary>(
          "/api/v1/dashboard/summary"
        );
        if (isMounted) {
          setSummary(response);
        }
      } catch (requestError) {
        if (isMounted) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : t("app.summaryError")
          );
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadSummary();

    return () => {
      isMounted = false;
    };
  }, [t]);

  const locale = language === "es" ? "es-AR" : "en-US";
  const today = useMemo(
    () =>
      new Intl.DateTimeFormat(locale, {
        weekday: "long",
        day: "numeric",
        month: "long"
      }).format(new Date()),
    [locale]
  );

  const hour = new Date().getHours();
  const greeting =
    hour < 12
      ? t("app.goodMorning")
      : hour < 20
        ? t("app.goodAfternoon")
        : t("app.goodNight");
  const displayName = getFirstName(summary);
  const employabilityScore = clampScore(
    summary?.employability_score ?? summary?.global_score
  );
  const completenessPct = clampScore(
    summary?.completeness_pct ?? summary?.completeness
  );
  const matches = (summary?.latest_matches ?? summary?.matches ?? []).slice(0, 5);
  const missingTip =
    summary?.missing_tip ?? summary?.most_valuable_missing_field ?? null;
  const profileActionMessage =
    completenessPct >= 85
      ? t("app.profileReady")
      : missingTip
        ? t("app.profileAt", { percent: completenessPct, tip: missingTip })
        : t("app.profileFallback", {
            percent: completenessPct,
            label: getScoreLabel(employabilityScore)
          });

  return (
    <main className="min-h-screen bg-[#f9fafb] p-6 sm:p-8 lg:p-10">
      <div className="mx-auto max-w-6xl">
        <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-sm font-medium text-neutral-500">
              <CalendarDays className="h-4 w-4 text-[#0F6E56]" />
              <span className="capitalize">{today}</span>
            </div>
            <div className="mt-3 flex min-w-0 items-center gap-3">
              <h1 className="min-w-0 text-3xl font-black leading-tight tracking-tight text-black md:text-4xl">
                {greeting}
                {displayName ? `, ${displayName}` : ""}
              </h1>
              <div className="hidden h-10 w-10 flex-none items-center justify-center rounded-full border border-neutral-100 bg-[#e6f2ed] text-[#0F6E56] shadow-sm sm:flex">
                <CircleUserRound className="h-5 w-5" />
              </div>
            </div>
          </div>
          {isLoading ? (
            <Badge variant="outline" className="gap-2 rounded-full border-neutral-100 bg-white">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              {t("app.loadingSummary")}
            </Badge>
          ) : null}
        </div>

        {error ? (
          <Card className="mb-6 rounded-2xl border border-destructive/20 bg-destructive/5 shadow-sm">
            <CardContent className="p-4 text-sm text-destructive">
              {error}
            </CardContent>
          </Card>
        ) : null}

        <section className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <ScoreCard
            action={
              completenessPct < 80 ? (
                <Button
                  asChild
                  className="rounded-xl bg-[#e6f2ed] px-5 font-semibold text-[#0F6E56] shadow-none hover:bg-[#d8ebe4]"
                >
                  <Link href="/wizard/step-1">{t("app.completeProfile")}</Link>
                </Button>
              ) : null
            }
            title={t("app.completeness")}
            value={completenessPct}
            variant="circular"
          />

          <ScoreCard
            description={profileActionMessage}
            title={t("app.globalScore")}
            value={employabilityScore}
          />
        </section>

        <section className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <Card className={dashboardCardClass}>
            <CardHeader>
              <div className="flex items-center gap-2 text-sm font-medium text-[#0F6E56]">
                <Sparkles className="h-4 w-4" />
                {t("app.analysisHero")}
              </div>
              <CardTitle className="text-2xl font-semibold">
                {t("app.analyzeNewJob")}
              </CardTitle>
              <CardDescription className="font-normal text-neutral-500">
                {t("app.analyzeDescription")}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <JobInputForm />
            </CardContent>
          </Card>

          <Card className="rounded-2xl border border-l-4 border-neutral-100 border-l-[#0F6E56] bg-white shadow-sm">
            <CardHeader className="pb-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#e6f2ed] text-[#0F6E56] shadow-sm">
                <Sparkles className="h-5 w-5" />
              </div>
              <CardTitle className="text-base font-semibold leading-snug">
                {t("app.suggestionsTitle")}
              </CardTitle>
              <CardDescription className="text-neutral-600">
                {t("app.suggestionsSubtitle")}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="rounded-2xl border border-neutral-100 bg-neutral-50/70 p-4 text-sm font-semibold leading-6 text-black">
                {profileActionMessage}
              </div>
              <p className="text-xs leading-5 text-neutral-600">
                {t("app.suggestionsFooter")}
              </p>
            </CardContent>
          </Card>
        </section>

        <section className="mt-6">
          <Card className={dashboardCardClass}>
            <CardHeader>
              <CardTitle className="font-semibold">{t("app.latestMatches")}</CardTitle>
              <CardDescription className="font-normal text-neutral-500">
                {t("app.latestMatchesDescription")}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {matches.length > 0 ? (
                <div className="space-y-3">
                  {matches.map((match) => {
                    const score = clampScore(match.score ?? match.match_score);
                    const color = getScoreColor(score);
                    const title = match.role ?? match.title ?? match.job_title ?? "";
                    const company = match.company ?? match.company_name ?? "";
                    const date = match.created_at ?? match.analyzed_at;
                    const formattedDate = date
                      ? new Intl.DateTimeFormat(locale, {
                          day: "2-digit",
                          month: "short"
                        }).format(new Date(date))
                      : "";

                    return (
                      <div
                        className="flex flex-col gap-4 rounded-2xl border border-neutral-100 bg-white p-4 transition hover:shadow-[0_8px_30px_rgb(0,0,0,0.04)] md:flex-row md:items-center md:justify-between"
                        key={match.id}
                      >
                        <div className="min-w-0">
                          <p className="truncate font-semibold">
                            {company || t("app.unnamedCompany")}
                          </p>
                          <p className="truncate text-sm text-muted-foreground">
                            {title || t("app.untitledRole")}
                          </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-3">
                          {formattedDate ? (
                            <span className="text-sm text-muted-foreground">
                              {formattedDate}
                            </span>
                          ) : null}
                          <Badge
                            className="rounded-full border-transparent text-white"
                            style={{ backgroundColor: color }}
                          >
                            {score}
                          </Badge>
                          <Button asChild variant="ghost">
                            <Link href={`/jobs/${match.id}`}>
                              {t("app.viewReport")}
                              <ArrowRight className="ml-2 h-4 w-4" />
                            </Link>
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="flex min-h-52 flex-col items-center justify-center rounded-2xl border border-dashed border-neutral-200 bg-neutral-50/70 p-6 text-center">
                  <div className="relative">
                    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#e6f2ed] text-[#0F6E56]">
                      <BriefcaseBusiness className="h-8 w-8" />
                    </div>
                    <div className="absolute -right-2 -top-2 h-5 w-5 rounded-full bg-brand-accent" />
                  </div>
                  <p className="mt-5 font-semibold">{t("app.noMatches")}</p>
                  <p className="mt-1 max-w-sm text-sm leading-6 text-muted-foreground">
                    {t("app.noMatchesDescription")}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  );
}
