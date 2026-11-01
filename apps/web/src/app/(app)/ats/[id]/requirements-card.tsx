import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusPill } from "@/src/components/landing/shared";

export type ATSRequirement = {
  key: string;
  label: string;
  required: string;
  actual: string;
  status: "met" | "partial" | "unmet";
  ratio: number;
  note: string | null;
  /** El requisito se dedujo del nivel del puesto («Senior»), no lo dice el aviso. */
  estimated: boolean;
  /** Qué se tuvo en cuenta, para poder comprobarlo. */
  detail: string[];
};

const TONE = { met: "ok", partial: "mid", unmet: "bad" } as const;
const STATUS_LABEL = {
  met: "Cumple",
  partial: "Cumple en parte",
  unmet: "No cumple"
} as const;

/** Años, formación e idiomas que pide el puesto contra lo que muestra la persona. */
export function RequirementsCard({
  requirements
}: {
  requirements: ATSRequirement[] | undefined;
}) {
  // Una API que todavía no manda el campo, o un aviso que no pide nada de esto.
  if (!requirements || requirements.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Requisitos del puesto</CardTitle>
        <CardDescription>
          Años de experiencia, formación e idiomas que pide el aviso. Si los
          superás, cuenta como cumplido y se aclara aparte: no suma ni resta
          puntos.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {requirements.map((requirement) => (
          <div
            className="rounded-2xl border border-border p-4"
            key={requirement.key}
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="font-medium">{requirement.label}</p>
              <StatusPill tone={TONE[requirement.status]}>
                {STATUS_LABEL[requirement.status]}
              </StatusPill>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Pide: {requirement.required || "sin detalle"} · Tenés:{" "}
              {requirement.actual || "sin datos"}
            </p>
            {requirement.note ? (
              <p className="mt-1 text-xs text-muted-foreground">
                {requirement.note}
              </p>
            ) : null}
            {requirement.detail.length > 0 ? (
              <details className="mt-2 text-xs text-muted-foreground">
                <summary className="cursor-pointer">Qué se tuvo en cuenta</summary>
                <ul className="mt-1 list-disc space-y-0.5 pl-5">
                  {requirement.detail.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </details>
            ) : null}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
