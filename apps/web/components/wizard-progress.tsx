import { Check } from "lucide-react";

import { cn } from "@/lib/utils";
import type { WizardStep } from "@/lib/wizard/progress";

const steps: Array<{ id: WizardStep; label: string }> = [
  { id: 1, label: "Info" },
  { id: 2, label: "CV" },
  { id: 3, label: "Skills" },
  { id: 4, label: "Perfil" }
];

type WizardProgressProps = {
  currentStep: WizardStep;
};

export function WizardProgress({ currentStep }: WizardProgressProps) {
  return (
    <nav aria-label="Progreso del onboarding" className="mb-8">
      <ol className="grid grid-cols-4 gap-2">
        {steps.map((step) => {
          const isComplete = step.id < currentStep;
          const isCurrent = step.id === currentStep;

          return (
            <li key={step.id}>
              <div className="flex items-center gap-2">
                <div
                  className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-md border text-sm font-medium",
                    isComplete &&
                      "border-secondary bg-secondary text-secondary-foreground",
                    isCurrent && "border-primary bg-primary text-primary-foreground",
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
  );
}
