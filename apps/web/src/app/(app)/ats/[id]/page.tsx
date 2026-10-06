"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Check, Loader2, Lock, Wand2, X } from "lucide-react";

import { PageBanner } from "@/components/page-banner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { DownloadCVPanel } from "@/components/cv/download-cv-panel";
import { apiClient } from "@/lib/api/client";
import { getScoreColor, getScoreLabel } from "@/lib/utils/score-colors";

import {
  OptimizedCVResult,
  type ATSOptimizeResponse
} from "./optimized-cv-result";

type KeywordStatus = "literal" | "semantic" | "missing";

type ATSReport = {
  job_id: string;
  ats_score: number;
  keyword_matches: Array<{
    keyword: string;
    status: KeywordStatus;
    matched_text: string | null;
  }>;
  format_issues: Array<{
    code: string;
    message: string;
    penalty: number;
  }>;
};

function statusLabel(status: KeywordStatus) {
  if (status === "literal") {
    return "✓";
  }
  if (status === "semantic") {
    return "~";
  }
  return "✗";
}

export default function ATSReportPage() {
  const params = useParams<{ id: string }>();
  const [report, setReport] = useState<ATSReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [optimized, setOptimized] = useState<ATSOptimizeResponse | null>(null);
  const [optimizerError, setOptimizerError] = useState<string | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);

  useEffect(() => {
    async function loadReport() {
      try {
        setReport(await apiClient<ATSReport>(`/api/v1/ats/${params.id}`));
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "No se pudo cargar el reporte ATS."
        );
      }
    }

    void loadReport();
  }, [params.id]);

  const scoreColor = getScoreColor(report?.ats_score ?? 0);
  const scoreLabel = getScoreLabel(report?.ats_score ?? 0);
  const missingCount = useMemo(
    () =>
      report?.keyword_matches.filter((match) => match.status === "missing")
        .length ?? 0,
    [report?.keyword_matches]
  );

  async function handleOptimize() {
    setIsOptimizing(true);
    setOptimizerError(null);
    try {
      setOptimized(
        await apiClient<ATSOptimizeResponse>("/api/v1/ats/optimize", {
          method: "POST",
          body: JSON.stringify({ job_id: params.id })
        })
      );
    } catch (requestError) {
      setOptimizerError(
        requestError instanceof Error
          ? requestError.message
          : "No se pudo optimizar el CV."
      );
    } finally {
      setIsOptimizing(false);
    }
  }

  if (error) {
    return (
      <main className="min-h-screen bg-white p-4 pb-14">
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
      <main className="min-h-screen bg-white p-4 pb-14">
        <Card>
          <CardContent className="pt-6 text-sm text-muted-foreground">
            Cargando ATS report...
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-white p-4 pb-14">
      <PageBanner
        actions={
          <Badge className="border-white/30 text-white" variant="outline">
            {missingCount} keywords faltantes
          </Badge>
        }
        className="mb-5"
        eyebrow="ATS Report"
        title="Compatibilidad con filtros ATS"
      />

      <section className="grid gap-4 lg:grid-cols-[0.75fr_1.25fr]">
        <Card>
          <CardHeader>
            <CardTitle>ATS Score</CardTitle>
            <CardDescription>
              Keywords literales, semánticas y penalizaciones de formato.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-3">
              <span
                className="text-8xl font-semibold italic leading-none tracking-[-0.04em]"
                style={{ color: scoreColor }}
              >
                {report.ats_score}
              </span>
              <div className="pb-3">
                <p className="text-sm text-muted-foreground">/100</p>
                <p className="font-medium" style={{ color: scoreColor }}>
                  {scoreLabel}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Keyword map</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto rounded-2xl border border-border">
              <table className="w-full min-w-[560px] text-sm">
                <thead className="bg-muted/50 text-left">
                  <tr>
                    <th className="px-4 py-3 font-medium">Keyword del job</th>
                    <th className="px-4 py-3 font-medium">Presente en CV?</th>
                    <th className="px-4 py-3 font-medium">Match</th>
                  </tr>
                </thead>
                <tbody>
                  {report.keyword_matches.map((match) => (
                    <tr className="border-t border-border" key={match.keyword}>
                      <td className="px-4 py-3 font-medium">{match.keyword}</td>
                      <td className="px-4 py-3">
                        <span
                          className="text-lg font-semibold"
                          style={{
                            color:
                              match.status === "missing"
                                ? getScoreColor(20)
                                : match.status === "semantic"
                                  ? getScoreColor(60)
                                  : getScoreColor(90)
                          }}
                        >
                          {statusLabel(match.status)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {match.matched_text ?? "Sin evidencia"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="mt-4">
        <Card>
          <CardHeader>
            <CardTitle>Issues de formato</CardTitle>
          </CardHeader>
          <CardContent>
            {report.format_issues.length > 0 ? (
              <div className="space-y-3">
                {report.format_issues.map((issue) => (
                  <div
                    className="flex items-center justify-between rounded-2xl border border-border p-4"
                    key={issue.code}
                  >
                    <div className="flex items-center gap-3">
                      <X className="h-5 w-5 text-destructive" />
                      <p className="font-medium">{issue.message}</p>
                    </div>
                    <Badge variant="outline">-{issue.penalty}</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-3 rounded-2xl border border-border p-4">
                <Check className="h-5 w-5 text-secondary" />
                <p className="font-medium">No detectamos problemas de formato.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="mt-4">
        <details className="rounded-card border border-border bg-background">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 p-6">
            <div>
              <h2 className="text-lg font-semibold">CV Optimizado</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Secciones reescritas para cubrir keywords faltantes sin inventar
                experiencia.
              </p>
            </div>
            <Badge variant="outline">3 por mes gratis · 30 en Premium</Badge>
          </summary>
          <div className="border-t border-border p-6">
            <Button
              disabled={isOptimizing}
              onClick={() => void handleOptimize()}
              type="button"
            >
              {isOptimizing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Optimizando...
                </>
              ) : (
                <>
                  <Wand2 className="mr-2 h-4 w-4" />
                  Optimizar secciones del CV
                </>
              )}
            </Button>

            {optimizerError ? (
              <div className="mt-4 flex items-start gap-3 rounded-2xl border border-border p-4 text-sm text-muted-foreground">
                <Lock className="mt-0.5 h-4 w-4" />
                <p>{optimizerError}</p>
              </div>
            ) : null}

            {optimized ? <OptimizedCVResult optimized={optimized} /> : null}
            {optimized && optimized.sections.length > 0 ? (
              <div className="mt-5">
                <DownloadCVPanel sections={optimized.sections} />
              </div>
            ) : null}
          </div>
        </details>
      </section>
    </main>
  );
}
