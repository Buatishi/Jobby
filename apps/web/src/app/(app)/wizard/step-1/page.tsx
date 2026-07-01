"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
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

const seniorityOptions = ["junior", "mid", "senior", "staff", "principal"];
const workModalities = [
  { value: "remote", label: "Remoto" },
  { value: "hybrid", label: "Híbrido" },
  { value: "onsite", label: "Presencial" }
];

export default function WizardStepOnePage() {
  const router = useRouter();
  const [headline, setHeadline] = useState("");
  const [summary, setSummary] = useState("");
  const [targetRole, setTargetRole] = useState("");
  const [targetSeniority, setTargetSeniority] = useState("mid");
  const [workModality, setWorkModality] = useState("remote");
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const draft = getWizardProgress().stepOneDraft;
    if (!draft) {
      return;
    }

    setHeadline(draft.headline ?? "");
    setSummary(draft.summary ?? "");
    setTargetRole(draft.targetRole ?? "");
    setTargetSeniority(draft.targetSeniority ?? "mid");
    setWorkModality(draft.workModality ?? "remote");
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
        headline,
        summary,
        targetRole,
        targetSeniority,
        workModality
      }
    });
    setSavedAt(new Date().toLocaleTimeString("es-AR", { timeStyle: "short" }));
  }, [headline, summary, targetRole, targetSeniority, workModality]);

  useEffect(() => {
    const timeout = window.setTimeout(saveDraft, 500);
    return () => window.clearTimeout(timeout);
  }, [saveDraft]);

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
          <div className="mb-5 rounded-md border border-[#0F6E56]/20 bg-[#0F6E56]/5 p-4 text-sm">
            <div className="flex gap-3">
              <Lightbulb className="mt-0.5 h-4 w-4 flex-none text-[#0F6E56]" />
              <div>
                <p className="font-medium text-[#0F6E56]">
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

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="headline">
                Headline
              </label>
              <input
                className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                id="headline"
                onChange={(event) => setHeadline(event.target.value)}
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
                className="min-h-28 w-full resize-none rounded-md border border-input bg-background p-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                id="summary"
                onChange={(event) => setSummary(event.target.value)}
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
                  className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  id="targetRole"
                  onChange={(event) => setTargetRole(event.target.value)}
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
                  className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  id="seniority"
                  onChange={(event) => setTargetSeniority(event.target.value)}
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
                    className="flex h-11 items-center gap-3 rounded-md border border-input px-3 text-sm"
                    key={option.value}
                  >
                    <input
                      checked={workModality === option.value}
                      name="workModality"
                      onChange={() => setWorkModality(option.value)}
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
                className="w-full bg-[#0F6E56] hover:bg-[#0b5b47] sm:w-auto"
                disabled={isSubmitting}
                type="submit"
              >
                {isSubmitting ? "Guardando..." : "Guardar y continuar"}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
              <Button
                disabled={isSubmitting}
                onClick={saveDraft}
                type="button"
                variant="secondary"
              >
                <Save className="mr-2 h-4 w-4" />
                Guardar borrador
              </Button>
              <Button
                disabled={isSubmitting}
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
