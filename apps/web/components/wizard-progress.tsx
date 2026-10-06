import { Check } from "lucide-react";

import { cn } from "@/lib/utils";
import type { WizardStep } from "@/lib/wizard/progress";

const steps: Array<{ id: WizardStep; label: string; reason: string }> = [
  {
    id: 1,
    label: "Objetivo",
    reason: "Define el rol contra el que calibramos tu Match Score."
  },
  {
    id: 2,
    label: "CV",
    reason: "Extrae evidencia real para evitar recomendaciones genéricas."
  },
  {
    id: 3,
    label: "Skills",
    reason: "Te deja confirmar qué datos entran al perfil maestro."
  },
  {
    id: 4,
    label: "Perfil",
    reason: "Completa señales que suelen faltar en el CV."
  }
];

type WizardProgressProps = {
  currentStep: WizardStep;
  completionPercent?: number;
};

export function WizardProgress({
  currentStep,
  completionPercent = Math.max(0, (currentStep - 1) * 25)
}: WizardProgressProps) {
  const current = steps.find((step) => step.id === currentStep) ?? steps[0];

  return (
    <section className="mb-8 rounded-card border border-border bg-background p-5 shadow-card">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-brand-green">
            Onboarding guiado
          </p>
          <h1 className="text-2xl font-semibold">{current.label}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {current.reason}
          </p>
        </div>
        <p className="text-sm font-medium">{completionPercent}% completo</p>
      </div>

      <div className="mb-5 h-2 overflow-hidden rounded-full bg-brand-mint">
        <div
          className="h-full rounded-full bg-brand-green transition-all"
          style={{ width: `${completionPercent}%` }}
        />
      </div>

      <nav aria-label="Progreso del onboarding">
        <ol className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {steps.map((step) => {
          const isComplete = step.id < currentStep;
          const isCurrent = step.id === currentStep;

          return (
            <li key={step.id}>
              <div className="flex items-center gap-2">
                <div
                  className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-sm font-semibold",
                    isComplete &&
                      "border-transparent bg-brand-green text-white",
                    isCurrent && "border-transparent bg-brand-bright text-brand-ink",
                    !isComplete && !isCurrent && "border-border bg-background"
                  )}
                >
                  {isComplete ? <Check className="h-4 w-4" /> : step.id}
                </div>
                <span className="hidden text-sm font-medium text-muted-foreground sm:inline">
                  {step.label}
                </span>
              </div>
            </li>
          );
        })}
        </ol>
      </nav>
    </section>
  );
}
