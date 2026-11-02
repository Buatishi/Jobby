"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Loader2, Lock, Wand2 } from "lucide-react";

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
  DeclareKeywords,
  optimizeRequestBody,
  type MissingKeyword
} from "./declare-keywords";
import {
  FormatIssuesCard,
  formatWasEvaluated,
  type FormatIssue
} from "./format-issues-card";
import {
  OptimizedCVResult,
  type ATSOptimizeResponse
} from "./optimized-cv-result";
import { KeywordName } from "./keyword-name";
import { RequirementsCard, type ATSRequirement } from "./requirements-card";

type KeywordStatus = "literal" | "semantic" | "missing";

type ATSReport = {
  job_id: string;
  ats_score: number;
  keyword_matches: Array<{
    keyword: string;
    status: KeywordStatus;
    matched_text: string | null;
    /** «nice»: el aviso la presenta como deseable y vale la mitad; una API anterior no lo manda. */
    priority?: "required" | "nice";
  }>;
  format_issues: FormatIssue[];
  /** Años, formación e idiomas que pide el puesto; una API anterior no lo manda. */
  requirements?: ATSRequirement[];
  /** false: el CV se leyó antes del chequeo de formato; `format_issues` vacío no es «sin problemas». */
  format_evaluated?: boolean;
  /** Puntos de formato (0 a 10) que entran en el puntaje; null si el formato no se evaluó. */
  format_points?: number | null;
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
  // Las palabras que la persona marcó como «sí las sé» aunque su CV no las muestre.
  const [declared, setDeclared] = useState<string[]>([]);

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
  const missingKeywords = useMemo<MissingKeyword[]>(
    () =>
      (report?.keyword_matches ?? [])
        .filter((match) => match.status === "missing")
        .map(({ keyword, priority }) => ({ keyword, priority })),
    [report?.keyword_matches]
  );
  const missingCount = missingKeywords.length;

  function toggleDeclared(keyword: string) {
    setDeclared((current) =>
      current.includes(keyword)
        ? current.filter((item) => item !== keyword)
        : [...current, keyword]
    );
  }

  async function handleOptimize() {
    setIsOptimizing(true);
    setOptimizerError(null);
    try {
      setOptimized(
        await apiClient<ATSOptimizeResponse>("/api/v1/ats/optimize", {
          method: "POST",
          body: JSON.stringify(
            optimizeRequestBody(params.id, declared, missingKeywords)
          )
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
              Palabras clave, años, formación, idiomas y formato (10 de los
              100 puntos, una estimación propia del riesgo de lectura).
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
                      <td className="px-4 py-3 font-medium">
                        <KeywordName
                          keyword={match.keyword}
                          priority={match.priority}
                        />
                      </td>
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
        <RequirementsCard requirements={report.requirements} />
      </section>

      <section className="mt-4">
        <FormatIssuesCard
          evaluated={formatWasEvaluated(report)}
          issues={report.format_issues}
          points={report.format_points}
        />
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
            <DeclareKeywords
              disabled={isOptimizing}
              missing={missingKeywords}
              onToggle={toggleDeclared}
              selected={declared}
            />
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

            {optimized ? (
              <OptimizedCVResult
                formatPointsBefore={report.format_points}
                optimized={optimized}
              />
            ) : null}
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
