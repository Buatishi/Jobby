"use client";

import { useI18n } from "@/lib/i18n/provider";

type ScoreRowProps = {
  label: string;
  value: number;
  hint: string;
};

function ScoreRow({ label, value, hint }: ScoreRowProps) {
  return (
    <div>
      <div className="flex justify-between">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <p className="mt-0.5 text-xs leading-5 text-muted-foreground">{hint}</p>
    </div>
  );
}

type SecondaryScoresProps = {
  potential: number | null;
  representation: number | null;
};

// Potential y Representation no son el Match Score: cada uno lleva una línea que dice qué mide.
export function SecondaryScores({ potential, representation }: SecondaryScoresProps) {
  const { t } = useI18n();

  return (
    <div className="mt-6 grid gap-3 text-sm">
      <ScoreRow
        hint={t("app.potentialScoreHint")}
        label="Potential Score"
        value={potential ?? 0}
      />
      <ScoreRow
        hint={t("app.representationScoreHint")}
        label="Representation Score"
        value={representation ?? 0}
      />
    </div>
  );
}
