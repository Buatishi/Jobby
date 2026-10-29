"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2 } from "lucide-react";

import { WizardProgress } from "@/components/wizard-progress";
import { useWizardOwner } from "@/components/wizard-owner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import {
  completeWizard,
  getWizardProgress,
  type WizardSkillDraft
} from "@/lib/wizard/progress";
import {
  applyStepFourWrite,
  mergeLoadedValues,
  planStepFourWrites,
  resolveStepFour,
  STEP_FOUR_DEFAULTS,
  STEP_FOUR_NOTHING_SAVED,
  type StepFourDetails,
  type StepFourField,
  type StepFourSaved,
  type StepFourValues
} from "@/lib/wizard/step-four";

type ProfilePreview = {
  headline?: string | null;
  target_role?: string | null;
  completeness_pct?: number | null;
};

export default function WizardStepFourPage() {
  const router = useRouter();
  const ownerId = useWizardOwner();
  const [values, setValues] = useState<StepFourValues>(STEP_FOUR_DEFAULTS);
  // Campos que la persona ya tocó: lo guardado, al llegar, no los pisa.
  const touchedRef = useRef<Set<StepFourField>>(new Set());
  const { company, title, education, language } = values;
  // Las filas que este paso edita; si ya existen, guardar las modifica en vez de agregar.
  const [saved, setSaved] = useState<StepFourSaved>(STEP_FOUR_NOTHING_SAVED);
  const [savedExperienceCount, setSavedExperienceCount] = useState(0);
  const [isLoadingDetails, setIsLoadingDetails] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [isPrefilled, setIsPrefilled] = useState(false);
  const [profile, setProfile] = useState<ProfilePreview | null>(null);
  const [skills, setSkills] = useState<WizardSkillDraft[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function edit(field: StepFourField, value: string) {
    touchedRef.current.add(field);
    setValues((current) => ({ ...current, [field]: value }));
  }

  const loadDetails = useCallback(() => {
    let active = true;
    setIsLoadingDetails(true);
    setLoadFailed(false);

    apiClient<StepFourDetails>("/api/v1/profiles/details")
      .then((details) => {
        if (!active) {
          return;
        }

        const resolved = resolveStepFour(details);
        setValues((current) =>
          mergeLoadedValues(current, touchedRef.current, resolved.values)
        );
        setSaved(resolved.saved);
        setSavedExperienceCount(resolved.experienceCount);
        setIsPrefilled(resolved.prefilled);
        setIsLoadingDetails(false);
      })
      .catch(() => {
        if (!active) {
          return;
        }

        // Sin saber qué hay guardado, guardar podría repetir datos: se espera al reintento.
        setLoadFailed(true);
        setIsLoadingDetails(false);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const progress = getWizardProgress(ownerId);
    setSkills((progress.parsedSkills ?? []).filter((skill) => !skill.rejected));

    void apiClient<ProfilePreview>("/api/v1/profiles/me")
      .then(setProfile)
      .catch(() => setProfile(null));

    return loadDetails();
  }, [loadDetails, ownerId]);

  const visibleSkills = useMemo(() => skills.slice(0, 8), [skills]);
  const hasExperience = company.trim() !== "" || title.trim() !== "";
  const experienceCount = Math.max(savedExperienceCount, hasExperience ? 1 : 0);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const writes = planStepFourWrites(values, saved);
      const results = await Promise.allSettled(
        writes.map((write) =>
          apiClient<{ id?: string | null }>(write.path, {
            method: write.method,
            // Editar una fila deja el mismo resultado si se repite (un deploy puede dar
            // 502); crear una no: repetirlo la duplicaría.
            idempotent: write.method === "PATCH",
            body: JSON.stringify(write.body)
          })
        )
      );

      // Lo que salió bien queda como guardado: si otro pedido falló y la persona
      // reintenta, esas filas se editan y no se vuelven a crear.
      let nextSaved = saved;
      let firstFailure: unknown = null;
      results.forEach((result, index) => {
        const write = writes[index];
        if (!write) {
          return;
        }
        if (result.status === "fulfilled") {
          nextSaved = applyStepFourWrite(
            nextSaved,
            write,
            result.value?.id ?? null
          );
        } else if (firstFailure === null) {
          firstFailure = result.reason;
        }
      });
      setSaved(nextSaved);

      if (firstFailure !== null) {
        throw firstFailure;
      }

      completeWizard(ownerId);
      router.push("/dashboard");
      router.refresh();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No se pudo completar el onboarding."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <WizardProgress currentStep={4} completionPercent={85} />
      <Card>
        <CardHeader>
          <CardTitle>Enriquecé tu perfil</CardTitle>
          <CardDescription>
            Sumá señales adicionales para mejorar el primer reporte. Este paso
            es opcional y editable más adelante.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-5 rounded-2xl border border-brand-green/20 bg-brand-green-light p-4 text-sm">
            <div className="flex gap-3">
              <CheckCircle2 className="mt-0.5 h-4 w-4 flex-none text-brand-green" />
              <p className="text-muted-foreground">
                Ya podés usar el dashboard. Estos datos solo ayudan a que el
                sistema entienda mejor experiencia, educación e idiomas.
              </p>
            </div>
          </div>

          {isLoadingDetails ? (
            <p className="mb-4 text-sm text-muted-foreground">
              Cargando lo que ya guardaste: podés escribir y el guardado se
              habilita en un momento.
            </p>
          ) : loadFailed ? (
            <div className="mb-4 flex flex-col gap-2 text-sm sm:flex-row sm:items-center">
              <p className="text-destructive">
                No pudimos cargar lo que ya guardaste, así que no se puede
                guardar desde acá sin repetir datos.
              </p>
              <Button onClick={loadDetails} size="sm" type="button" variant="outline">
                Reintentar
              </Button>
            </div>
          ) : isPrefilled ? (
            <p className="mb-4 text-sm text-muted-foreground">
              Cargamos lo que ya tenías guardado. Cambiá solo lo que quieras
              actualizar: si no tocás nada, no se vuelve a guardar.
            </p>
          ) : null}

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="company">
                  Empresa reciente
                </label>
                <input
                  className="h-11 w-full rounded-full border border-input bg-background px-5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  id="company"
                  onChange={(event) => edit("company", event.target.value)}
                  placeholder="Acme"
                  value={company}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="title">
                  Cargo
                </label>
                <input
                  className="h-11 w-full rounded-full border border-input bg-background px-5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  id="title"
                  onChange={(event) => edit("title", event.target.value)}
                  placeholder="Software Engineer"
                  value={title}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="education">
                Educación
              </label>
              <input
                className="h-11 w-full rounded-full border border-input bg-background px-5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                id="education"
                onChange={(event) => edit("education", event.target.value)}
                placeholder="Universidad, bootcamp o certificación principal"
                value={education}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="language">
                Idioma adicional
              </label>
              <input
                className="h-11 w-full rounded-full border border-input bg-background px-5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                id="language"
                onChange={(event) => edit("language", event.target.value)}
                placeholder="Inglés"
                value={language}
              />
            </div>

            <Card className="border-brand-green/20 bg-brand-green-light shadow-none">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">
                  Así va a ver tu perfil la IA
                </CardTitle>
                <CardDescription>
                  Revisá el resumen antes de terminar la configuración.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm font-semibold">
                    {profile?.headline || "Headline pendiente"}
                    {profile?.target_role ? ` · ${profile.target_role}` : ""}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Experiencias en tu perfil: {experienceCount}
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  {visibleSkills.length > 0 ? (
                    visibleSkills.map((skill) => (
                      <Badge
                        className="rounded-full bg-white text-brand-green"
                        key={skill.id}
                        variant="outline"
                      >
                        {skill.name}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-xs text-muted-foreground">
                      Todavía no hay skills confirmadas en este wizard.
                    </span>
                  )}
                </div>

                <Badge className="bg-brand-green text-white">
                  Completeness actual: {profile?.completeness_pct ?? 0}%
                </Badge>
              </CardContent>
            </Card>

            {error ? <p className="text-sm text-destructive">{error}</p> : null}

            <div className="flex flex-col gap-3 sm:flex-row">
              <Button
                disabled={isSubmitting || isLoadingDetails || loadFailed}
                type="submit"
              >
                {isSubmitting ? "Guardando..." : "Guardar y finalizar"}
              </Button>
              <Button
                disabled={isSubmitting}
                onClick={() => {
                  completeWizard(ownerId);
                  router.push("/dashboard");
                }}
                type="button"
                variant="ghost"
              >
                Finalizar sin agregar más
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
