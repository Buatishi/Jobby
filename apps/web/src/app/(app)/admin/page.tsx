"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ActivityChart } from "@/components/admin/activity-chart";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { type AdminMetrics, formatDay } from "@/lib/admin/metrics";
import { ApiForbiddenError, apiClient } from "@/lib/api/client";
import { useI18n } from "@/lib/i18n/provider";

type LoadState =
  | { status: "loading" }
  | { status: "forbidden" }
  | { status: "error"; message: string }
  | { status: "ready"; metrics: AdminMetrics };

function StatTile({
  label,
  value,
  details
}: {
  label: string;
  value: number | string;
  details: string[];
}) {
  return (
    <div className="rounded-2xl border border-neutral-100 bg-white p-4 shadow-[0_8px_30px_rgb(0,0,0,0.02)]">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-1 text-3xl font-black tracking-tight text-black">{value}</p>
      <ul className="mt-2 space-y-0.5 text-xs text-muted-foreground">
        {details.map((detail) => (
          <li key={detail}>{detail}</li>
        ))}
      </ul>
    </div>
  );
}

export default function AdminPage() {
  const { language, t } = useI18n();
  const locale = language === "es" ? "es-AR" : "en-US";
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    async function load() {
      try {
        const metrics = await apiClient<AdminMetrics>("/api/v1/admin/metrics");
        setState({ status: "ready", metrics });
      } catch (error) {
        if (error instanceof ApiForbiddenError) {
          setState({ status: "forbidden" });
          return;
        }
        setState({
          status: "error",
          message: error instanceof Error ? error.message : t("admin.error")
        });
      }
    }

    void load();
  }, [t]);

  if (state.status === "loading") {
    return (
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <p className="text-sm text-muted-foreground">{t("admin.loading")}</p>
      </main>
    );
  }

  if (state.status === "forbidden" || state.status === "error") {
    return (
      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
        <Card>
          <CardContent className="space-y-4 pt-6">
            <p className="text-sm text-black">
              {state.status === "forbidden" ? t("admin.forbidden") : state.message}
            </p>
            <Button asChild variant="outline">
              <Link href="/dashboard">{t("admin.backToDashboard")}</Link>
            </Button>
          </CardContent>
        </Card>
      </main>
    );
  }

  const { metrics } = state;
  const days = metrics.daily_activity;

  return (
    <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-black tracking-tight text-black">
          {t("admin.title")}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("admin.subtitle")}</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {t("admin.updated", {
            time: new Intl.DateTimeFormat(locale, {
              dateStyle: "medium",
              timeStyle: "short"
            }).format(new Date(metrics.generated_at))
          })}
        </p>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <StatTile
          details={[
            t("admin.plans", {
              free: metrics.users.free,
              premium: metrics.users.premium
            }),
            t("admin.newThisWeek", { count: metrics.users.new_last_7_days })
          ]}
          label={t("admin.people")}
          value={metrics.users.total}
        />
        <StatTile
          details={[
            t("admin.cvsDone", { count: metrics.cvs.done }),
            t("admin.failed", { count: metrics.cvs.failed }),
            t("admin.inProgress", { count: metrics.cvs.in_progress })
          ]}
          label={t("admin.cvs")}
          value={metrics.cvs.total}
        />
        <StatTile
          details={[t("admin.newThisWeek", { count: metrics.jobs.last_7_days })]}
          label={t("admin.jobs")}
          value={metrics.jobs.total}
        />
        <StatTile
          details={[
            metrics.matches.average_score === null
              ? t("admin.noScore")
              : t("admin.averageScore", { score: metrics.matches.average_score }),
            metrics.matches.average_rating === null
              ? t("admin.noRatings")
              : t("admin.averageRating", {
                  rating: metrics.matches.average_rating,
                  count: metrics.matches.rated
                })
          ]}
          label={t("admin.matches")}
          value={metrics.matches.total}
        />
        <StatTile
          details={[
            t("admin.kitsDone", { count: metrics.interview_kits.done }),
            t("admin.failed", { count: metrics.interview_kits.failed })
          ]}
          label={t("admin.kits")}
          value={metrics.interview_kits.total}
        />
      </section>

      <section className="mt-8">
        <h2 className="text-base font-bold text-black">{t("admin.activity")}</h2>
        <p className="mt-1 text-xs text-muted-foreground">{t("admin.activityNote")}</p>
        <div className="mt-4 grid gap-3 lg:grid-cols-3">
          <ActivityChart
            days={days}
            locale={locale}
            series="cvs"
            title={t("admin.cvsPerDay")}
            unit={t("admin.unitCvs")}
          />
          <ActivityChart
            days={days}
            locale={locale}
            series="jobs"
            title={t("admin.jobsPerDay")}
            unit={t("admin.unitJobs")}
          />
          <ActivityChart
            days={days}
            locale={locale}
            series="matches"
            title={t("admin.matchesPerDay")}
            unit={t("admin.unitMatches")}
          />
        </div>

        <details className="mt-4 rounded-2xl border border-neutral-100 bg-white p-4 text-sm">
          <summary className="cursor-pointer font-semibold text-black">
            {t("admin.showTable")}
          </summary>
          <table className="mt-3 w-full text-left text-xs">
            <thead className="text-muted-foreground">
              <tr>
                <th className="py-1 font-medium">{t("admin.day")}</th>
                <th className="py-1 text-right font-medium">{t("admin.unitCvs")}</th>
                <th className="py-1 text-right font-medium">{t("admin.unitJobs")}</th>
                <th className="py-1 text-right font-medium">{t("admin.unitMatches")}</th>
              </tr>
            </thead>
            <tbody className="text-black">
              {days.map((day) => (
                <tr className="border-t border-neutral-100" key={day.day}>
                  <td className="py-1">{formatDay(day.day, locale)}</td>
                  <td className="py-1 text-right tabular-nums">{day.cvs}</td>
                  <td className="py-1 text-right tabular-nums">{day.jobs}</td>
                  <td className="py-1 text-right tabular-nums">{day.matches}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      </section>
    </main>
  );
}
