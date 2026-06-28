"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Check, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { getScoreColor, getScoreLabel } from "@/lib/utils/score-colors";

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
            Cargando ATS report...
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:py-8">
      <div className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="text-sm font-medium text-muted-foreground">ATS Report</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-normal">
            Compatibilidad con filtros ATS
          </h1>
        </div>
        <Badge variant="outline">{missingCount} keywords faltantes</Badge>
      </div>

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
                className="text-8xl font-semibold leading-none"
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
            <div className="overflow-x-auto rounded-md border border-border">
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
                    className="flex items-center justify-between rounded-md border border-border p-4"
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
              <div className="flex items-center gap-3 rounded-md border border-border p-4">
                <Check className="h-5 w-5 text-secondary" />
                <p className="font-medium">No detectamos problemas de formato.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
