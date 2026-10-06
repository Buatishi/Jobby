"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { PageBanner } from "@/components/page-banner";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { cn } from "@/lib/utils";

type InterviewKit = {
  id: string;
  title: string | null;
  status: string;
  error_msg: string | null;
  questions: Record<string, unknown> | null;
  prep_notes: Record<string, unknown> | null;
};

type TabKey =
  | "fit"
  | "strengths"
  | "risks"
  | "argument"
  | "answers"
  | "questions"
  | "plan";

const tabs: Array<{ key: TabKey; label: string }> = [
  { key: "fit", label: "Fit CV ↔ Empresa" },
  { key: "strengths", label: "Fortalezas" },
  { key: "risks", label: "Brechas y riesgos" },
  { key: "argument", label: "Argumentario" },
  { key: "answers", label: "Respuestas modelo" },
  { key: "questions", label: "Tus preguntas" },
  { key: "plan", label: "Plan de acción" }
];

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function asText(value: unknown, fallback = "") {
  return typeof value === "string" && value.trim().length > 0
    ? value
    : fallback;
}

function asScore(value: unknown) {
  return typeof value === "number" && Number.isFinite(value)
    ? Math.max(0, Math.min(100, Math.round(value)))
    : 0;
}

function compatibility(score: number) {
  if (score >= 81) {
    return { label: "Muy alto", color: "#0F6E56" };
  }
  if (score >= 66) {
    return { label: "Alto", color: "#1D9E75" };
  }
  if (score >= 51) {
    return { label: "Medio-Alto", color: "#F0A500" };
  }
  if (score >= 36) {
    return { label: "Medio", color: "#E07B00" };
  }
  return { label: "A demostrar", color: "#E24B4A" };
}

function severityClassName(severity: string) {
  return cn(
    severity === "low" && "border-[#1D9E75] text-[#1D9E75]",
    severity === "medium" && "border-[#F0A500] text-[#8A5F00]",
    severity === "high" && "border-[#E24B4A] text-[#E24B4A]"
  );
}

function normalizeItems(value: unknown) {
  return asArray(value).map((item, index) => {
    if (typeof item === "string") {
      return {
        title: item,
        body: "",
        evidence: "",
        talkingPoint: "",
        whenToUse: "",
        severity: "medium",
        question: item,
        answer: "",
        tips: "",
        justification: ""
      };
    }

    const record = asRecord(item);
    return {
      title: asText(record.title ?? record.name, `Ítem ${index + 1}`),
      body: asText(record.body ?? record.description ?? record.mitigation),
      evidence: asText(record.evidence),
      talkingPoint: asText(record.talking_point ?? record.talkingPoint),
      whenToUse: asText(record.when_to_use ?? record.whenToUse),
      severity: asText(record.severity, "medium"),
      question: asText(record.question ?? record.title, `Pregunta ${index + 1}`),
      answer: asText(record.answer ?? record.response),
      tips: asText(record.tips ?? record.evaluation_criteria),
      justification: asText(record.justification ?? record.why)
    };
  });
}

function normalizeCompatibility(value: unknown) {
  return asArray(value).map((item, index) => {
    const record = asRecord(item);
    return {
      name: asText(record.name ?? record.area, `Área ${index + 1}`),
      score: asScore(record.score),
      notes: asText(record.notes ?? record.description)
    };
  });
}

function normalizePlan(value: unknown) {
  const record = asRecord(value);
  if (record.before || record.during || record.after) {
    return {
      before: normalizeItems(record.before),
      during: normalizeItems(record.during),
      after: normalizeItems(record.after)
    };
  }

  const steps = normalizeItems(record.steps ?? value);
  return {
    before: steps.slice(0, Math.ceil(steps.length / 3)),
    during: steps.slice(Math.ceil(steps.length / 3), Math.ceil((steps.length * 2) / 3)),
    after: steps.slice(Math.ceil((steps.length * 2) / 3))
  };
}

export default function InterviewKitDetailPage() {
  const params = useParams<{ id: string }>();
  const [kit, setKit] = useState<InterviewKit | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("fit");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadKit() {
      try {
        const response = await apiClient<InterviewKit>(
          `/api/v1/interview-kits/${params.id}`
        );
        setKit(response);
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "No se pudo cargar el kit."
        );
      }
    }

    void loadKit();
  }, [params.id]);

  const notes = useMemo(() => asRecord(kit?.prep_notes), [kit?.prep_notes]);
  const questions = useMemo(() => asRecord(kit?.questions), [kit?.questions]);
  const compatibilityAreas = useMemo(
    () => normalizeCompatibility(notes.compatibility_areas),
    [notes.compatibility_areas]
  );
  const strengths = useMemo(() => normalizeItems(notes.strengths), [notes.strengths]);
  const risks = useMemo(() => normalizeItems(notes.risks), [notes.risks]);
  const argumentario = useMemo(
    () => normalizeItems(notes.argumentario),
    [notes.argumentario]
  );
  const modelAnswers = useMemo(
    () => normalizeItems(notes.model_answers ?? questions.model_answers),
    [notes.model_answers, questions.model_answers]
  );
  const candidateQuestions = useMemo(
    () =>
      normalizeItems(
        notes.candidate_questions ?? questions.candidate_questions
      ),
    [notes.candidate_questions, questions.candidate_questions]
  );
  const actionPlan = useMemo(
    () => normalizePlan(notes.action_plan),
    [notes.action_plan]
  );

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

  if (!kit) {
    return (
      <main className="min-h-screen bg-white p-4 pb-14">
        <Card>
          <CardContent className="pt-6 text-sm text-muted-foreground">
            Cargando kit...
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-white p-4 pb-14">
      <PageBanner
        className="mb-5"
        eyebrow="Interview Kit"
        note={kit.error_msg ?? undefined}
        title={kit.title ?? "Kit de entrevista"}
      />

      <div className="mb-5 flex gap-2 overflow-x-auto pb-2">
        {tabs.map((tab) => (
          <button
            className={cn(
              "h-10 shrink-0 rounded-full border border-border px-4 text-sm font-semibold transition-colors",
              activeTab === tab.key
                ? "border-transparent bg-brand-bright text-brand-ink"
                : "bg-background hover:bg-muted"
            )}
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "fit" ? (
        <section className="space-y-4">
          <div className="rounded-2xl border-l-4 border-brand-green bg-muted/30 p-5">
            <p className="leading-7">
              {asText(
                notes.overall_summary,
                "El resumen general va a aparecer cuando el kit termine de generarse."
              )}
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {compatibilityAreas.map((area) => {
              const meta = compatibility(area.score);
              return (
                <Card key={area.name}>
                  <CardHeader>
                    <div className="flex items-center justify-between gap-3">
                      <CardTitle>{area.name}</CardTitle>
                      <Badge style={{ borderColor: meta.color, color: meta.color }} variant="outline">
                        {meta.label}
                      </Badge>
                    </div>
                    {area.notes ? (
                      <CardDescription>{area.notes}</CardDescription>
                    ) : null}
                  </CardHeader>
                  <CardContent>
                    <div className="mb-2 flex justify-between text-sm">
                      <span>Compatibilidad</span>
                      <strong>{area.score}</strong>
                    </div>
                    <div className="h-3 rounded-full bg-muted">
                      <div
                        className="h-3 rounded-full"
                        style={{
                          width: `${area.score}%`,
                          backgroundColor: meta.color
                        }}
                      />
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </section>
      ) : null}

      {activeTab === "strengths" ? (
        <section className="grid gap-4 md:grid-cols-2">
          {strengths.map((strength, index) => (
            <Card key={`${strength.title}-${index}`}>
              <CardHeader>
                <CardTitle>{strength.title}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm leading-6">
                <p>{strength.evidence || strength.body}</p>
                <p className="rounded-2xl bg-muted p-3">
                  {strength.talkingPoint || "Conectalo con una experiencia concreta del CV."}
                </p>
              </CardContent>
            </Card>
          ))}
        </section>
      ) : null}

      {activeTab === "risks" ? (
        <section className="grid gap-4 md:grid-cols-2">
          {risks.map((risk, index) => (
            <Card key={`${risk.title}-${index}`}>
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <CardTitle>{risk.title}</CardTitle>
                  <Badge
                    className={severityClassName(risk.severity)}
                    variant="outline"
                  >
                    {risk.severity}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="text-sm leading-6">
                {risk.body || "Prepará evidencia para responder esta brecha."}
              </CardContent>
            </Card>
          ))}
        </section>
      ) : null}

      {activeTab === "argument" ? (
        <section className="space-y-3">
          {argumentario.map((item, index) => (
            <Card key={`${item.title}-${index}`}>
              <CardContent className="pt-6">
                <p className="font-medium">{item.title}</p>
                {item.body ? (
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {item.body}
                  </p>
                ) : null}
                <p className="mt-3 text-sm">
                  <span className="font-medium">Cuándo usarlo: </span>
                  {item.whenToUse || "Cuando necesites conectar tu experiencia con el desafío del rol."}
                </p>
              </CardContent>
            </Card>
          ))}
        </section>
      ) : null}

      {activeTab === "answers" ? (
        <section className="space-y-3">
          {modelAnswers.map((answer, index) => (
            <details
              className="rounded-card border border-border bg-background p-4"
              key={`${answer.question}-${index}`}
            >
              <summary className="cursor-pointer font-medium">
                {answer.question}
              </summary>
              <p className="mt-4 text-sm leading-6">{answer.answer}</p>
              {answer.tips ? (
                <p className="mt-3 rounded-2xl bg-muted p-3 text-sm">
                  {answer.tips}
                </p>
              ) : null}
            </details>
          ))}
        </section>
      ) : null}

      {activeTab === "questions" ? (
        <section className="space-y-3">
          {candidateQuestions.map((question, index) => (
            <Card key={`${question.question}-${index}`}>
              <CardContent className="pt-6">
                <p className="font-medium">{question.question}</p>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  {question.justification || "Sirve para validar expectativas, contexto y señales culturales."}
                </p>
              </CardContent>
            </Card>
          ))}
        </section>
      ) : null}

      {activeTab === "plan" ? (
        <section className="grid gap-4 md:grid-cols-3">
          {[
            ["Antes", actionPlan.before],
            ["Durante", actionPlan.during],
            ["Después", actionPlan.after]
          ].map(([label, items]) => (
            <Card key={label as string}>
              <CardHeader>
                <CardTitle>{label as string}</CardTitle>
              </CardHeader>
              <CardContent>
                <ol className="space-y-3">
                  {(items as ReturnType<typeof normalizeItems>).map(
                    (item, index) => (
                      <li className="flex gap-3 text-sm leading-6" key={`${item.title}-${index}`}>
                        <span className="mt-1 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary text-xs text-primary-foreground">
                          {index + 1}
                        </span>
                        <span>{item.title || item.body}</span>
                      </li>
                    )
                  )}
                </ol>
              </CardContent>
            </Card>
          ))}
        </section>
      ) : null}
    </main>
  );
}
