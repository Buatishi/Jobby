"use client";

import { Check, Info, X } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useI18n } from "@/lib/i18n/provider";

export type FormatIssue = {
  code: string;
  message: string;
  penalty: number;
};

type FormatIssuesCardProps = {
  issues: FormatIssue[];
  /** false: el CV se leyó antes de que existiera el chequeo de formato, no se miró. */
  evaluated: boolean;
  /** Los puntos de formato (0 a 10) que entran en el puntaje; una API anterior no los manda. */
  points?: number | null;
};

/** Los puntos máximos de formato; los fija `FORMAT_POINTS` en `scoring.py`. */
const FORMAT_POINTS = 10;

/** Una API que todavía no manda el campo se trata como antes: el formato se evaluó. */
export function formatWasEvaluated(report: {
  format_evaluated?: boolean;
}): boolean {
  return report.format_evaluated !== false;
}

export function FormatIssuesCard({
  issues,
  evaluated,
  points
}: FormatIssuesCardProps) {
  const { t } = useI18n();

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("app.atsFormatTitle")}</CardTitle>
      </CardHeader>
      <CardContent>
        {!evaluated ? (
          <div
            className="flex items-start gap-3 rounded-2xl border border-border p-4"
            role="status"
          >
            <Info className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
            <div>
              <p className="font-medium">
                {t("app.atsFormatNotEvaluatedTitle")}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                {t("app.atsFormatNotEvaluatedHint")}
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {typeof points === "number" ? (
              <p className="text-sm">
                <span className="text-muted-foreground">
                  {t("app.atsFormatPointsLabel")}:{" "}
                </span>
                <span className="font-semibold">
                  {points} / {FORMAT_POINTS}
                </span>
              </p>
            ) : null}
            {issues.length > 0 ? (
              issues.map((issue) => (
                <div
                  className="flex items-center justify-between rounded-2xl border border-border p-4"
                  key={issue.code}
                >
                  <div className="flex items-center gap-3">
                    <X className="h-5 w-5 text-destructive" />
                    <p className="font-medium">{issue.message}</p>
                  </div>
                  {issue.penalty > 0 ? (
                    <span className="text-sm font-medium text-muted-foreground">
                      −{issue.penalty}
                    </span>
                  ) : null}
                </div>
              ))
            ) : (
              <div className="flex items-center gap-3 rounded-2xl border border-border p-4">
                <Check className="h-5 w-5 text-secondary" />
                <p className="font-medium">{t("app.atsFormatClean")}</p>
              </div>
            )}
            <p className="text-sm text-muted-foreground">
              {t("app.atsFormatEstimate")}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
