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
  name?: string | null;
  employability_score?: number | null;
  global_score?: number | null;
  completeness_pct?: number | null;
  completeness?: number | null;
  missing_tip?: string | null;
  most_valuable_missing_field?: string | null;
  pending_analyses_count?: number | null;
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

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "";
  }

  return new Intl.DateTimeFormat("es-AR", {
    day: "2-digit",
    month: "short"
  }).format(new Date(value));
}

function getGreeting() {
  const hour = new Date().getHours();

  if (hour < 12) {
    return "Buenos días";
  }

  if (hour < 20) {
    return "Buenas tardes";
  }

  return "Buenas noches";
}

export function DashboardClient() {
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
              : "No se pudo cargar el resumen."
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
  }, []);

  const today = useMemo(
    () =>
      new Intl.DateTimeFormat("es-AR", {
        weekday: "long",
        day: "numeric",
        month: "long"
      }).format(new Date()),
    []
  );

  const userName = summary?.user_name ?? summary?.name ?? "";
  const employabilityScore = clampScore(
    summary?.employability_score ?? summary?.global_score
  );
  const completenessPct = clampScore(
    summary?.completeness_pct ?? summary?.completeness
  );
  const matches = (summary?.latest_matches ?? summary?.matches ?? []).slice(0, 5);
  const missingTip =
    summary?.missing_tip ?? summary?.most_valuable_missing_field ?? null;
  const scoreColor = getScoreColor(employabilityScore);
  const scoreLabel = getScoreLabel(employabilityScore);
  const completenessRadius = 48;
  const completenessStroke = 2 * Math.PI * completenessRadius;
  const completenessOffset =
    completenessStroke - (completenessPct / 100) * completenessStroke;
  const scoreNeedleAngle = -90 + (employabilityScore / 100) * 180;
  const contextualSuggestions = [
    missingTip
      ? `Próxima brecha a resolver: ${missingTip}.`
      : completenessPct < 80
        ? "Completá tu perfil para que Jobby detecte brechas críticas con más precisión."
        : `Tu perfil está en estado ${scoreLabel}. Analizá un puesto para convertirlo en recomendaciones concretas.`
  ];

  return (
    <main className="min-h-screen bg-[#f9fafb] p-6 sm:p-8 lg:p-10">
      <div className="mx-auto max-w-6xl">
        <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-sm font-medium text-neutral-500">
              <CalendarDays className="h-4 w-4 text-[#007a5e]" />
              <span className="capitalize">{today}</span>
            </div>
            <div className="mt-3 flex min-w-0 items-center gap-3">
              <h1 className="min-w-0 text-3xl font-black leading-tight tracking-tight text-black md:text-4xl">
                {getGreeting()}
                {userName ? `, ${userName}` : ""}
              </h1>
              <div className="hidden h-10 w-10 flex-none items-center justify-center rounded-full border border-neutral-100 bg-[#e6f2ed] text-[#007a5e] shadow-sm sm:flex">
                <CircleUserRound className="h-5 w-5" />
              </div>
            </div>
          </div>
          {isLoading ? (
            <Badge variant="outline" className="gap-2 rounded-full border-neutral-100 bg-white">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Cargando resumen
            </Badge>
          ) : null}
        </div>

        {error ? (
          <Card className="mb-6 rounded-2xl border border-destructive/20 bg-destructive/5 shadow-[0_8px_30px_rgb(0,0,0,0.02)]">
            <CardContent className="p-4 text-sm text-destructive">
              {error}
            </CardContent>
          </Card>
        ) : null}

        <section className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <Card className={dashboardCardClass}>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg font-semibold">
                Completeness del perfil
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col items-center pb-8">
              <div className="relative h-48 w-48">
                <svg
                  aria-label={`Completitud del perfil ${completenessPct}%`}
                  className="h-full w-full -rotate-90"
                  role="img"
                  viewBox="0 0 120 120"
                >
                  <circle
                    cx="60"
                    cy="60"
                    fill="none"
                    r={completenessRadius}
                    stroke="#e5e7eb"
                    strokeLinecap="round"
                    strokeWidth="8"
                  >
                    <animate
                      attributeName="stroke-dashoffset"
                      dur="900ms"
                      fill="freeze"
                      from={completenessStroke}
                      to={completenessOffset}
                    />
                  </circle>
                  <circle
                    cx="60"
                    cy="60"
                    fill="none"
                    r={completenessRadius}
                    stroke="#007a5e"
                    strokeDasharray={completenessStroke}
                    strokeDashoffset={completenessOffset}
                    strokeLinecap="round"
                    strokeWidth="8"
                    className="transition-all duration-700"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                  <p className="text-3xl font-bold leading-none text-black">
                    <CountUp value={completenessPct} />%
                  </p>
                  <p className="mt-1 text-xs font-semibold text-neutral-500">
                    Meta: 100%
                  </p>
                </div>
              </div>

              {completenessPct < 80 ? (
                <Button
                  asChild
                  className="mt-4 rounded-xl bg-[#e6f2ed] px-5 font-semibold text-[#007a5e] shadow-none hover:bg-[#d8ebe4]"
                >
                  <Link href="/profile">Conecta tu LinkedIn</Link>
                </Button>
              ) : null}
            </CardContent>
          </Card>

          <Card className={dashboardCardClass}>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg font-semibold">Score global</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col items-center pb-8">
              <div className="relative h-48 w-64">
                <svg
                  aria-label={`Score global ${employabilityScore} de 100`}
                  className="h-full w-full"
                  role="img"
                  viewBox="0 0 240 165"
                >
                  <defs>
                    <linearGradient
                      id="scoreGaugeGradient"
                      x1="0%"
                      x2="100%"
                      y1="0%"
                      y2="0%"
                    >
                      <stop offset="0%" stopColor="#E24B4A" />
                      <stop offset="50%" stopColor="#F0A500" />
                      <stop offset="100%" stopColor="#007a5e" />
                    </linearGradient>
                  </defs>
                  <path
                    d="M38 126 A82 82 0 0 1 202 126"
                    fill="none"
                    stroke="#e5e7eb"
                    strokeLinecap="round"
                    strokeWidth="20"
                  >
                    <animate
                      attributeName="stroke-dasharray"
                      dur="900ms"
                      fill="freeze"
                      from="0 100"
                      to={`${employabilityScore} 100`}
                    />
                  </path>
                  <path
                    d="M38 126 A82 82 0 0 1 202 126"
                    fill="none"
                    pathLength="100"
                    stroke="url(#scoreGaugeGradient)"
                    strokeDasharray={`${employabilityScore} 100`}
                    strokeLinecap="round"
                    strokeWidth="20"
                    className="transition-all duration-700"
                  />
                  <g
                    className="transition-transform duration-700"
                    style={{
                      transform: `rotate(${scoreNeedleAngle}deg)`,
                      transformBox: "fill-box",
                      transformOrigin: "120px 126px"
                    }}
                  >
                    <line
                      stroke="#111827"
                      strokeLinecap="round"
                      strokeWidth="4"
                      x1="120"
                      x2="120"
                      y1="126"
                      y2="68"
                    />
                    <circle cx="120" cy="126" fill="#111827" r="6" />
                  </g>
                  <text
                    fill="#111827"
                    fontSize="44"
                    fontWeight="900"
                    textAnchor="middle"
                    x="120"
                    y="111"
                  >
                    {employabilityScore}
                  </text>
                  <text
                    fill={scoreColor}
                    fontSize="14"
                    fontWeight="700"
                    textAnchor="middle"
                    x="120"
                    y="134"
                  >
                    {scoreLabel}
                  </text>
                  <text fill="#737373" fontSize="10" fontWeight="600" x="31" y="153">
                    0
                  </text>
                  <text
                    fill="#737373"
                    fontSize="10"
                    fontWeight="600"
                    textAnchor="end"
                    x="209"
                    y="153"
                  >
                    100
                  </text>
                </svg>
              </div>
              <p className="mt-1 text-center text-xs font-semibold text-neutral-600">
                Estado general:{" "}
                <span style={{ color: scoreColor }}>{scoreLabel}</span> para
                competir.
              </p>
            </CardContent>
          </Card>
        </section>

        <section className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <Card className={dashboardCardClass}>
            <CardHeader>
              <div className="flex items-center gap-2 text-sm font-medium text-[#007a5e]">
                <Sparkles className="h-4 w-4" />
                Hero de análisis
              </div>
              <CardTitle className="text-2xl font-semibold">
                Analizá un nuevo puesto
              </CardTitle>
              <CardDescription className="font-normal text-neutral-500">
                Pegá una URL o el texto completo del aviso para iniciar el análisis.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <JobInputForm />
            </CardContent>
          </Card>

          <Card className="rounded-2xl border border-neutral-100 bg-[#e6f2ed] shadow-sm">
            <CardHeader className="pb-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-[#007a5e] shadow-sm">
                <Sparkles className="h-5 w-5" />
              </div>
              <CardTitle className="text-base font-semibold leading-snug">
                Sugerencias de Jobby
              </CardTitle>
              <CardDescription className="text-neutral-700">
                Usamos tu perfil actual para anticipar qué mirar antes de aplicar.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {contextualSuggestions.map((suggestion) => (
                <div
                  className="rounded-2xl border border-white/70 bg-white/75 p-4 text-sm font-semibold leading-6 text-black"
                  key={suggestion}
                >
                  {suggestion}
                </div>
              ))}
              <p className="text-xs leading-5 text-neutral-600">
                Al analizar un puesto, estas alertas se vuelven específicas para
                ese rol y priorizan skills, ATS y brechas reales.
              </p>
            </CardContent>
          </Card>
        </section>

        <section className="mt-6">
          <Card className={dashboardCardClass}>
            <CardHeader>
              <CardTitle className="font-semibold">Últimos 5 matches</CardTitle>
              <CardDescription className="font-normal text-neutral-500">
                Tus análisis recientes aparecen ordenados por actividad.
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
                    const date = formatDate(match.created_at ?? match.analyzed_at);

                    return (
                      <div
                        className="flex flex-col gap-4 rounded-2xl border border-neutral-100 bg-white p-4 transition hover:shadow-[0_8px_30px_rgb(0,0,0,0.04)] md:flex-row md:items-center md:justify-between"
                        key={match.id}
                      >
                        <div className="min-w-0">
                          <p className="truncate font-semibold">
                            {company || "Empresa sin nombre"}
                          </p>
                          <p className="truncate text-sm text-muted-foreground">
                            {title || "Rol sin título"}
                          </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-3">
                          {date ? (
                            <span className="text-sm text-muted-foreground">
                              {date}
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
                              Ver reporte
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
                    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#e6f2ed] text-[#007a5e]">
                      <BriefcaseBusiness className="h-8 w-8" />
                    </div>
                    <div className="absolute -right-2 -top-2 h-5 w-5 rounded-full bg-brand-accent" />
                  </div>
                  <p className="mt-5 font-semibold">Todavía no hay matches</p>
                  <p className="mt-1 max-w-sm text-sm leading-6 text-muted-foreground">
                    Analizá tu primer puesto para ver empresa, rol, score y reporte.
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
