"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, Info, Lightbulb, Save } from "lucide-react";
import { useRouter } from "next/navigation";

import { WizardProgress } from "@/components/wizard-progress";
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
  saveWizardProgress
} from "@/lib/wizard/progress";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "@/components/ui/tooltip";
import {
  mergeLoadedValues,
  resolveStepOneValues,
  SENIORITY_OPTIONS,
  STEP_ONE_DEFAULTS,
  WORK_MODALITIES,
  type StepOneField,
  type StepOneProfile,
  type StepOneValues
} from "@/lib/wizard/step-one";

const seniorityOptions = SENIORITY_OPTIONS;
const workModalities = WORK_MODALITIES;

export default function WizardStepOnePage() {
  const router = useRouter();
  const [values, setValues] = useState<StepOneValues>(STEP_ONE_DEFAULTS);
  // Campos que la persona ya tocó: el perfil, al llegar, no los pisa.
  const touchedRef = useRef<Set<StepOneField>>(new Set());
  const { headline, summary, targetRole, targetSeniority, workModality } = values;
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [profileId, setProfileId] = useState<string | undefined>(undefined);
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);
  const [isPrefilled, setIsPrefilled] = useState(false);

  function edit(field: StepOneField, value: string) {
    touchedRef.current.add(field);
    setValues((current) => ({ ...current, [field]: value }));
  }

  useEffect(() => {
    let active = true;
    const draft = getWizardProgress().stepOneDraft;

    // Se abre con lo que ya está guardado en el perfil; si la carga falla, con el borrador.
    apiClient<StepOneProfile>("/api/v1/profiles/me")
      .catch(() => null)
      .then((profile) => {
        if (!active) {
          return;
        }

        const resolved = resolveStepOneValues(profile, draft);
        const prefilled = resolved.prefilled;
        setValues((current) =>
          mergeLoadedValues(current, touchedRef.current, resolved.values)
        );
        setProfileId(profile?.id ?? undefined);
        setIsPrefilled(prefilled);
        setIsLoadingProfile(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const completionPercent = useMemo(() => {
    const checks = [
      headline.trim().length >= 4,
      summary.trim().length >= 20,
      targetRole.trim().length >= 3,
      Boolean(targetSeniority),
      Boolean(workModality)
    ];
    const done = checks.filter(Boolean).length;
    return Math.round((done / checks.length) * 25);
  }, [headline, summary, targetRole, targetSeniority, workModality]);

  const saveDraft = useCallback(() => {
    saveWizardProgress({
      currentStep: 1,
      stepOneDraft: {
        profileId,
        headline,
        summary,
        targetRole,
        targetSeniority,
        workModality
      }
    });
    setSavedAt(new Date().toLocaleTimeString("es-AR", { timeStyle: "short" }));
  }, [profileId, headline, summary, targetRole, targetSeniority, workModality]);

  useEffect(() => {
    // Antes de cargar el perfil el formulario tiene los valores por defecto: no se guardan.
    if (isLoadingProfile) {
      return;
    }

    const timeout = window.setTimeout(saveDraft, 500);
    return () => window.clearTimeout(timeout);
  }, [isLoadingProfile, saveDraft]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    saveDraft();

    try {
      await apiClient("/api/v1/profiles/me", {
        method: "PATCH",
        body: JSON.stringify({
          headline,
          summary,
          target_role: targetRole,
          target_seniority: targetSeniority,
          work_modality: workModality
        })
      });
      saveWizardProgress({
        currentStep: 2,
        stepOneDraft: {
          profileId,
          headline,
          summary,
          targetRole,
          targetSeniority,
          workModality
        }
      });
      router.push("/wizard/step-2");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No se pudo guardar tu perfil."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <WizardProgress currentStep={1} completionPercent={completionPercent} />
      <Card>
        <CardHeader>
          <CardTitle>Tu objetivo laboral</CardTitle>
          <CardDescription>
            Estos datos calibran el Match Score. Podés guardarlos como borrador
            y volver al dashboard cuando quieras.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-5 rounded-2xl border border-brand-green/20 bg-brand-green-light p-4 text-sm">
            <div className="flex gap-3">
              <Lightbulb className="mt-0.5 h-4 w-4 flex-none text-brand-green" />
              <div>
                <p className="font-medium text-brand-green">
                  ¿Por qué pedimos esto?
                </p>
                <p className="mt-1 text-muted-foreground">
                  El rol, seniority y modalidad definen contra qué puestos
                  comparar tu perfil. La bio ayuda a detectar brechas reales,
                  no solo keywords sueltas.
                </p>
              </div>
            </div>
          </div>

          {isLoadingProfile ? (
            <p className="mb-4 text-sm text-muted-foreground">
              Cargando tu perfil: ya podés escribir y el guardado se habilita en
              un momento.
            </p>
          ) : isPrefilled ? (
            <p className="mb-4 text-sm text-muted-foreground">
              Ya cargamos lo que tenés guardado: editá solo lo que quieras
              cambiar y guardá.
            </p>
          ) : null}

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="headline">
                Headline
              </label>
              <input
                className="h-11 w-full rounded-full border border-input bg-background px-5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                id="headline"
                onChange={(event) => edit("headline", event.target.value)}
                placeholder="Backend Engineer"
                required
                value={headline}
              />
              <p className="text-xs text-muted-foreground">
                Ejemplo: Backend Engineer especializado en APIs y automatización.
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="summary">
                Bio
              </label>
              <textarea
                className="min-h-28 w-full resize-none rounded-2xl border border-input bg-background p-4 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                id="summary"
                onChange={(event) => edit("summary", event.target.value)}
                placeholder="Contame en pocas líneas qué hacés y hacia dónde querés ir."
                value={summary}
              />
              <p className="text-xs text-muted-foreground">
                Mínimo sugerido: 20 caracteres. No bloquea, pero mejora el
                análisis.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium" htmlFor="targetRole">
                    Rol objetivo
                  </label>
                  <TooltipProvider delayDuration={150}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Info className="h-3.5 w-3.5 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent>
                        Usamos esto para encontrar coincidencias más precisas con
                        los puestos que analices.
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
                <input
                  className="h-11 w-full rounded-full border border-input bg-background px-5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  id="targetRole"
                  onChange={(event) => edit("targetRole", event.target.value)}
                  placeholder="AI Product Engineer"
                  required
                  value={targetRole}
                />
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium" htmlFor="seniority">
                    Seniority
                  </label>
                  <TooltipProvider delayDuration={150}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Info className="h-3.5 w-3.5 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent>
                        Comparamos tu nivel con el que pide cada puesto para
                        calcular tu Seniority Score.
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
                <select
                  className="h-11 w-full rounded-full border border-input bg-background px-5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  id="seniority"
                  onChange={(event) => edit("targetSeniority", event.target.value)}
                  value={targetSeniority}
                >
                  {seniorityOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <fieldset className="space-y-3">
              <legend className="text-sm font-medium">
                <span className="inline-flex items-center gap-2">
                  Modalidad
                <TooltipProvider delayDuration={150}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="h-3.5 w-3.5 text-muted-foreground" />
                    </TooltipTrigger>
                    <TooltipContent>
                      Afecta tu Company Fit Score si el puesto tiene modalidad
                      distinta a tu preferencia.
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                </span>
              </legend>
              <div className="grid gap-3 sm:grid-cols-3">
                {workModalities.map((option) => (
                  <label
                    className="flex h-11 items-center gap-3 rounded-full border border-input px-4 text-sm"
                    key={option.value}
                  >
                    <input
                      checked={workModality === option.value}
                      name="workModality"
                      onChange={() => edit("workModality", option.value)}
                      type="radio"
                    />
                    {option.label}
                  </label>
                ))}
              </div>
            </fieldset>

            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            {savedAt ? (
              <p className="text-xs text-muted-foreground">
                Borrador guardado automáticamente a las {savedAt}.
              </p>
            ) : null}

            <div className="flex flex-col gap-3 sm:flex-row">
              <Button
                className="w-full sm:w-auto"
                disabled={isSubmitting || isLoadingProfile}
                type="submit"
              >
                {isSubmitting ? "Guardando..." : "Guardar y continuar"}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
              <Button
                disabled={isSubmitting || isLoadingProfile}
                onClick={saveDraft}
                type="button"
                variant="secondary"
              >
                <Save className="mr-2 h-4 w-4" />
                Guardar borrador
              </Button>
              <Button
                disabled={isSubmitting || isLoadingProfile}
                onClick={() => {
                  saveDraft();
                  completeWizard();
                  router.push("/dashboard");
                }}
                type="button"
                variant="ghost"
              >
                Ir al dashboard
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
