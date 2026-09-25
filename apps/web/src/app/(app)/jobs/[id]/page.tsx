"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Info, Star } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { planOf } from "@/lib/auth/permissions";
import { useCurrentUser } from "@/lib/auth/use-current-user";
import { getScoreColor, getScoreLabel } from "@/lib/utils/score-colors";
import { cn } from "@/lib/utils";

import { InterviewPrepLink } from "./interview-prep-link";

type MatchReport = {
  id: string;
  job_id: string;
  match_score: number | null;
  potential_score: number | null;
  representation_score: number | null;
  gap_origin: string | null;
  score_breakdown: {
    sub_scores?: Record<string, number>;
    reasoning?: string;
  } | null;
  recommendations:
    | Array<{
        title?: string;
        description?: string;
        priority?: "low" | "medium" | "high";
      }>
    | null;
  user_rating: number | null;
  job: {
    job_title?: string | null;
    company_name?: string | null;
  } | null;
};

const scoreComponents = [
  { key: "skills", label: "Skills", weight: "35%" },
  { key: "seniority", label: "Seniority", weight: "25%" },
  { key: "company", label: "Company", weight: "15%" },
  { key: "education", label: "Education", weight: "10%" },
  { key: "languages", label: "Languages", weight: "10%" },
  { key: "soft", label: "Soft", weight: "5%" }
];

export default function MatchReportPage() {
  const params = useParams<{ id: string }>();
  const [report, setReport] = useState<MatchReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rating, setRating] = useState<number | null>(null);
  const [profileConfidence, setProfileConfidence] = useState<
    "high" | "medium" | null
  >(null);
  const plan = planOf(useCurrentUser());

  useEffect(() => {
    async function loadReport() {
      try {
        const matchReport = await apiClient<MatchReport>(
          `/api/v1/matches/${params.id}`
        );
        setReport(matchReport);
        setRating(matchReport.user_rating);
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "No se pudo cargar el reporte."
        );
      }
    }

    void loadReport();
  }, [params.id]);

  useEffect(() => {
    const storedConfidence = window.localStorage.getItem(
      `jobmatch_profile_confidence:${params.id}`
    );
    setProfileConfidence(
      storedConfidence === "medium" || storedConfidence === "high"
        ? storedConfidence
        : null
    );
  }, [params.id]);

  const matchScore = report?.match_score ?? 0;
  const scoreLabel = getScoreLabel(matchScore);
  const scoreColor = getScoreColor(matchScore);
  const subScores = useMemo(
    () => report?.score_breakdown?.sub_scores ?? {},
    [report?.score_breakdown]
  );

  async function submitRating(nextRating: number) {
    if (!report) {
      return;
    }

    const updated = await apiClient<MatchReport>(
      `/api/v1/matches/${report.id}/rating`,
      {
        method: "PATCH",
        body: JSON.stringify({ rating: nextRating })
      }
    );
    setReport(updated);
    setRating(updated.user_rating);
  }

  if (error) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
        <Card>
          <CardContent className="pt-6 text-sm text-destructive">
            {error}
          </CardContent>
        </Card>
      </main>
    );
  }

  if (!report) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
        <Card>
          <CardContent className="pt-6 text-sm text-muted-foreground">
            Cargando reporte...
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:py-8">
      <div className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="text-sm font-medium text-muted-foreground">
            Match Report
          </p>
          <h1 className="mt-1 text-3xl font-semibold tracking-normal">
            {report.job?.job_title ?? "Puesto analizado"}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {report.job?.company_name ?? "Empresa sin identificar"}
          </p>
        </div>
        <Badge variant="outline">Gap: {report.gap_origin ?? "none"}</Badge>
      </div>

      {profileConfidence === "medium" ? (
        <div className="mb-4 flex items-start gap-3 rounded-2xl border border-[#0F6E56]/20 bg-[#0F6E56]/5 p-4 text-sm text-[#0F6E56]">
          <Info className="mt-0.5 h-4 w-4 flex-none" />
          <p>
            Tu análisis puede mejorar completando tu perfil.{" "}
            <Link className="font-semibold underline" href="/dashboard">
              Volver al dashboard
            </Link>
          </p>
        </div>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <Card>
          <CardHeader>
            <CardTitle>Match Score</CardTitle>
            <CardDescription>
              Compatibilidad multidimensional entre tu perfil y el puesto.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-3">
              <span
                className="text-8xl font-semibold leading-none"
                style={{ color: scoreColor }}
              >
                {matchScore}
              </span>
              <div className="pb-3">
                <p className="text-sm text-muted-foreground">/100</p>
                <p className="font-medium" style={{ color: scoreColor }}>
                  {scoreLabel}
                </p>
              </div>
            </div>
            <div className="mt-6 grid gap-2 text-sm">
              <div className="flex justify-between">
                <span>Potential Score</span>
                <strong>{report.potential_score ?? 0}</strong>
              </div>
              <div className="flex justify-between">
                <span>Representation Score</span>
                <strong>{report.representation_score ?? 0}</strong>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Componentes</CardTitle>
            <CardDescription>
              Cada barra muestra el sub-score y su peso en la fórmula.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {scoreComponents.map((component) => {
              const score = Math.round((subScores[component.key] ?? 0) * 100);
              return (
                <div key={component.key}>
                  <div className="mb-2 flex items-center justify-between text-sm">
                    <span className="font-medium">
                      {component.label} {component.weight}
                    </span>
                    <span>{score}</span>
                  </div>
                  <div className="h-3 rounded-md bg-muted">
                    <div
                      className="h-3 rounded-md"
                      style={{
                        width: `${score}%`,
                        backgroundColor: getScoreColor(score)
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </section>

      <section className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle>Recomendaciones priorizadas</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {(report.recommendations ?? []).map((recommendation, index) => (
                <div
                  className="rounded-md border border-border p-4"
                  key={`${recommendation.title}-${index}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium">
                      {recommendation.title ?? recommendation.description}
                    </p>
                    <Badge
                      className={cn(
                        recommendation.priority === "high" && "border-primary"
                      )}
                      variant="outline"
                    >
                      {recommendation.priority ?? "medium"}
                    </Badge>
                  </div>
                  {recommendation.description ? (
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      {recommendation.description}
                    </p>
                  ) : null}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Feedback</CardTitle>
            <CardDescription>Qué tan útil fue este análisis?</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5].map((value) => (
                <button
                  aria-label={`Rating ${value}`}
                  className="rounded-md p-1 hover:bg-muted"
                  key={value}
                  onClick={() => void submitRating(value)}
                  type="button"
                >
                  <Star
                    className={cn(
                      "h-7 w-7",
                      rating && value <= rating
                        ? "fill-secondary text-secondary"
                        : "text-muted-foreground"
                    )}
                  />
                </button>
              ))}
            </div>
            {rating ? (
              <p className="mt-3 text-sm text-muted-foreground">
                Gracias por tu feedback.
              </p>
            ) : null}

            <InterviewPrepLink plan={plan} />
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
