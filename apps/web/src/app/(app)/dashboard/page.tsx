import { BriefcaseBusiness, Lightbulb } from "lucide-react";

import { JobInputForm } from "@/components/job-input-form";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { getScoreColor, getScoreLabel } from "@/lib/utils/score-colors";

const employabilityScore = 74;
const completenessPct = 68;
const missingTip = "Agrega al menos 3 skills confirmadas para sumar +10 pts.";
const latestMatches: Array<{
  id: string;
  title: string;
  company: string;
  score: number;
}> = [];

export default function DashboardPage() {
  const scoreColor = getScoreColor(employabilityScore);
  const scoreLabel = getScoreLabel(employabilityScore);

  return (
    <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:py-8">
      <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Dashboard</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-normal">
            Tu panel de compatibilidad laboral
          </h1>
        </div>
        <Badge variant="outline">Sprint 2</Badge>
      </div>

      <section className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Score global de empleabilidad</CardTitle>
            <CardDescription>
              Resume tu preparacion actual para aplicar con confianza.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-3">
              <span
                className="text-7xl font-semibold leading-none"
                style={{ color: scoreColor }}
              >
                {employabilityScore}
              </span>
              <div className="pb-2">
                <p className="text-sm text-muted-foreground">/100</p>
                <p className="font-medium" style={{ color: scoreColor }}>
                  {scoreLabel}
                </p>
              </div>
            </div>
            <div className="mt-6 grid grid-cols-4 gap-2">
              {[25, 50, 75, 100].map((value) => (
                <div
                  className="h-2 rounded-md"
                  key={value}
                  style={{
                    backgroundColor:
                      employabilityScore >= value
                        ? getScoreColor(value)
                        : "hsl(var(--muted))"
                  }}
                />
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Completeness del perfil</CardTitle>
            <CardDescription>
              Cada campo completo mejora la calidad del Match Score.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="mb-3 flex items-center justify-between text-sm">
              <span className="font-medium">{completenessPct}% completo</span>
              <span className="text-muted-foreground">Meta: 100%</span>
            </div>
            <div className="h-3 rounded-md bg-muted">
              <div
                className="h-3 rounded-md"
                style={{
                  width: `${completenessPct}%`,
                  backgroundColor: getScoreColor(completenessPct)
                }}
              />
            </div>
            <div className="mt-5 flex gap-3 rounded-lg border border-border p-4">
              <Lightbulb className="mt-0.5 h-5 w-5 text-primary" />
              <div>
                <p className="text-sm font-medium">Proximo campo mas valioso</p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  {missingTip}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="mt-4">
        <Card>
          <CardHeader>
            <CardTitle>Analiza un nuevo job</CardTitle>
            <CardDescription>
              Pega una URL o el texto completo de la busqueda laboral.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <JobInputForm />
          </CardContent>
        </Card>
      </section>

      <section className="mt-4">
        <Card>
          <CardHeader>
            <CardTitle>Ultimos 5 matches</CardTitle>
            <CardDescription>
              Los analisis recientes apareceran aca cuando este integrado Sprint 2.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {latestMatches.length > 0 ? (
              <div className="space-y-3">
                {latestMatches.map((match) => (
                  <div
                    className="flex items-center justify-between rounded-md border border-border p-4"
                    key={match.id}
                  >
                    <div>
                      <p className="font-medium">{match.title}</p>
                      <p className="text-sm text-muted-foreground">
                        {match.company}
                      </p>
                    </div>
                    <Badge>{match.score}</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex min-h-40 flex-col items-center justify-center rounded-lg border border-dashed border-border text-center">
                <BriefcaseBusiness className="h-8 w-8 text-muted-foreground" />
                <p className="mt-3 font-medium">Todavia no hay matches</p>
                <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                  Analiza tu primer job para ver scores, brechas y recomendaciones.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
