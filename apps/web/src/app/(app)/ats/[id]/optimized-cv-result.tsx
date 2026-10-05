import { Badge } from "@/components/ui/badge";
import { getScoreColor } from "@/lib/utils/score-colors";

export type ATSOptimizeResponse = {
  job_id: string;
  sections: Array<{
    section_name: string;
    original_excerpt: string;
    rewritten_text: string;
    added_keywords: string[];
    rationale: string;
    unverified_keywords?: string[];
  }>;
  ats_score_before?: number | null;
  ats_score_after?: number | null;
};

export function OptimizedCVResult({
  optimized
}: {
  optimized: ATSOptimizeResponse;
}) {
  return (
    <div className="mt-5 space-y-4">
      {typeof optimized.ats_score_before === "number" &&
      typeof optimized.ats_score_after === "number" ? (
        <div className="rounded-md border border-border p-4">
          <p className="text-sm text-muted-foreground">
            Puntaje ATS con las secciones nuevas
          </p>
          <p className="mt-1 text-2xl font-semibold">
            <span
              style={{ color: getScoreColor(optimized.ats_score_before) }}
            >
              {optimized.ats_score_before}
            </span>
            {" → "}
            <span
              style={{ color: getScoreColor(optimized.ats_score_after) }}
            >
              {optimized.ats_score_after}
            </span>
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Solo cuenta lo que tu CV respalda.
          </p>
        </div>
      ) : null}
      {optimized.sections.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No detectamos secciones con baja cobertura para reescribir.
        </p>
      ) : (
        optimized.sections.map((section) => (
          <div
            className="rounded-md border border-border p-4"
            key={section.section_name}
          >
            <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
              <div>
                <h3 className="font-medium">{section.section_name}</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {section.rationale}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {section.added_keywords.map((keyword) => (
                  <Badge key={keyword} variant="outline">
                    {keyword}
                  </Badge>
                ))}
              </div>
            </div>
            {section.unverified_keywords &&
            section.unverified_keywords.length > 0 ? (
              <div
                className="mt-4 rounded-md border p-3 text-sm"
                style={{ borderColor: getScoreColor(40) }}
              >
                <p className="font-medium">
                  Sin respaldo en tu CV:{" "}
                  {section.unverified_keywords.join(", ")}
                </p>
                <p className="mt-1 text-muted-foreground">
                  Usalas solo si de verdad tenés esa experiencia.
                </p>
              </div>
            ) : null}
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <div className="rounded-md bg-muted/40 p-3 text-sm leading-6 text-muted-foreground">
                {section.original_excerpt}
              </div>
              <div className="rounded-md border border-[#1D9E75] p-3 text-sm leading-6">
                {section.rewritten_text}
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
