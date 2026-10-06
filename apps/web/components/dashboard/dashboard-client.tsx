"use client";

import Link from "next/link";
import { useMemo } from "react";
import {
  ArrowRight,
  BriefcaseBusiness,
  CalendarDays,
  Loader2,
  Plus,
  Sparkles
} from "lucide-react";

import { CountUp } from "@/components/dashboard/count-up";
import { DarkPanel } from "@/components/dark-panel";
import { JobInputForm } from "@/components/job-input-form";
import { ScoreRing } from "@/components/score-ring";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { useApiResource } from "@/lib/api/use-api-resource";
import {
  clampScore,
  getFirstName,
  getInitials,
  type DashboardSummary
} from "@/lib/dashboard/summary";
import { useI18n } from "@/lib/i18n/provider";
import {
  getScoreColor,
  getScoreColorOnDark,
  getScoreLabel
} from "@/lib/utils/score-colors";

type DashboardViewProps = {
  summary: DashboardSummary | undefined;
  error: string | null;
  isLoading: boolean;
};

function StatCard({
  children,
  label
}: {
  children: React.ReactNode;
  label: string;
}) {
  return (
    <div className="rounded-card border border-brand-line bg-white px-5 py-5 text-center shadow-card">
      <div className="text-[clamp(2.5rem,5vw,3.5rem)] font-semibold italic leading-none tracking-[-0.04em] text-brand-green">
        {children}
      </div>
      <p className="mt-3 text-[13px] font-semibold text-neutral-600">{label}</p>
    </div>
  );
}

// Vista del dashboard: recibe los datos ya resueltos para poder probarla sin la API.
export function DashboardView({ summary, error, isLoading }: DashboardViewProps) {
  const { language, t } = useI18n();

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
    <main className="min-h-screen bg-white p-4 pb-14">
      <DarkPanel floor>
        <div className="grid gap-8 px-6 pb-14 pt-8 sm:px-10 sm:pt-10 md:grid-cols-[1fr_auto] md:items-center">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-3 text-sm font-medium text-neutral-300">
              <span className="inline-flex items-center gap-2">
                <CalendarDays className="h-4 w-4 text-brand-bright" />
                <span className="inline-block first-letter:uppercase">{today}</span>
              </span>
              {isLoading ? (
                <Badge className="gap-2 border-white/20 bg-white/10 text-white" variant="outline">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  {t("app.loadingSummary")}
                </Badge>
              ) : null}
            </div>
            <h1 className="mt-3 text-[clamp(1.875rem,4vw,2.875rem)] font-semibold leading-[1.05] tracking-[-0.025em]">
              {greeting}
              {displayName ? `, ${displayName}` : ""}
            </h1>
            <p className="mt-3 max-w-[48ch] text-[15px] font-medium text-neutral-300">
              {profileActionMessage}
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Button asChild>
                <a href="#analizar">
                  <Plus className="h-4 w-4" />
                  {t("app.analyzeNewJob")}
                </a>
              </Button>
              {completenessPct < 80 ? (
                <Button
                  asChild
                  className="border-white/40 text-white hover:border-white"
                  variant="outline"
                >
                  <Link href="/wizard/step-1">{t("app.completeProfile")}</Link>
                </Button>
              ) : null}
            </div>
          </div>

          <div className="grid justify-items-center gap-2 text-[13px] font-medium text-neutral-400">
            <ScoreRing
              className="h-[148px] w-[148px]"
              color={getScoreColorOnDark(employabilityScore)}
              label={`${t("app.globalScore")}: ${employabilityScore}/100`}
              trackColor="#3A3A37"
              value={employabilityScore}
            >
              <span className="text-[42px] font-semibold text-white">
                <CountUp value={employabilityScore} />
              </span>
            </ScoreRing>
            <span>{t("app.globalScore")}</span>
          </div>
        </div>
      </DarkPanel>

      {error ? (
        <Card className="mt-5 border-destructive/20 bg-destructive/5 shadow-none">
          <CardContent className="p-4 pt-4 text-sm text-destructive">{error}</CardContent>
        </Card>
      ) : null}

      <section className="mt-5 grid gap-5 md:grid-cols-3">
        <StatCard label={t("app.completeness")}>
          <CountUp value={completenessPct} />%
        </StatCard>
        <StatCard label={t("app.globalScore")}>
          <CountUp value={employabilityScore} />
        </StatCard>
        <StatCard label={t("app.latestMatches")}>
          <CountUp value={matches.length} />
        </StatCard>
      </section>

      <section className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <Card id="analizar">
          <CardHeader>
            <div className="flex items-center gap-2 text-sm font-semibold text-brand-green">
              <Sparkles className="h-4 w-4" />
              {t("app.analysisHero")}
            </div>
            <CardTitle className="text-2xl font-semibold">{t("app.analyzeNewJob")}</CardTitle>
            <CardDescription className="font-normal text-neutral-500">
              {t("app.analyzeDescription")}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <JobInputForm />
          </CardContent>
        </Card>

        <Card className="self-start">
          <CardHeader className="pb-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-[14px] bg-brand-ink text-brand-bright">
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
            <div className="flex items-start gap-3.5 rounded-[22px] bg-brand-green-light py-3 pl-3 pr-5 text-sm font-semibold leading-6">
              <span
                aria-hidden="true"
                className="mt-0.5 flex h-[30px] w-[30px] flex-none items-center justify-center rounded-full bg-brand-ink text-white"
              >
                <ArrowRight className="h-[15px] w-[15px]" />
              </span>
              {profileActionMessage}
            </div>
            <p className="text-xs leading-5 text-neutral-600">{t("app.suggestionsFooter")}</p>
          </CardContent>
        </Card>
      </section>

      <section className="mt-5">
        <Card>
          <CardHeader>
            <CardTitle className="font-semibold">{t("app.latestMatches")}</CardTitle>
            <CardDescription className="font-normal text-neutral-500">
              {t("app.latestMatchesDescription")}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {matches.length > 0 ? (
              <ul>
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
                    <li
                      className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3.5 border-t border-brand-line py-3.5 first:border-t-0 first:pt-0 sm:gap-4"
                      key={match.id}
                    >
                      <span
                        aria-hidden="true"
                        className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-green-light text-sm font-bold text-brand-green"
                      >
                        {getInitials(company, title)}
                      </span>
                      <div className="min-w-0">
                        <p className="truncate text-[15px] font-semibold">
                          {title || t("app.untitledRole")}
                        </p>
                        <p className="truncate text-[13px] font-medium text-neutral-500">
                          {company || t("app.unnamedCompany")}
                          {formattedDate ? `, ${formattedDate}` : ""}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <ScoreRing
                          className="h-[52px] w-[52px]"
                          color={color}
                          label={`${score}/100`}
                          strokeWidth={10}
                          trackColor="#CBEADD"
                          value={score}
                        >
                          <span className="text-sm font-bold">{score}</span>
                        </ScoreRing>
                        <Button asChild size="sm" variant="ghost">
                          <Link href={`/jobs/${match.id}`}>
                            {t("app.viewReport")}
                            <ArrowRight className="h-4 w-4" />
                          </Link>
                        </Button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <div className="flex min-h-52 flex-col items-center justify-center rounded-card border border-dashed border-brand-mint bg-brand-green-light/40 p-6 text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-green-light text-brand-green">
                  <BriefcaseBusiness className="h-8 w-8" />
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
    </main>
  );
}

export function DashboardClient() {
  const { t } = useI18n();
  const {
    data: summary,
    error,
    loading: isLoading
  } = useApiResource<DashboardSummary>("/api/v1/dashboard/summary", t("app.summaryError"));

  return <DashboardView error={error} isLoading={isLoading} summary={summary} />;
}
