"use client";

import { Check, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

type ProgressStepsProps = {
  currentStep: number;
  companyName?: string;
  interviewerName?: string;
  failed?: boolean;
};

export function ProgressSteps({
  currentStep,
  companyName,
  interviewerName,
  failed = false
}: ProgressStepsProps) {
  const steps = [
    "Analizando descripción del puesto",
    `Obteniendo información de ${companyName || "la empresa"} en LinkedIn`,
    `Analizando perfil de ${interviewerName || "el entrevistador"}`,
    "Generando tu kit personalizado"
  ];

  return (
    <ol className="space-y-3">
      {steps.map((label, index) => {
        const stepNumber = index + 1;
        const done = currentStep > stepNumber;
        const active = currentStep === stepNumber && !failed;
        const isFailed = currentStep === stepNumber && failed;

        return (
          <li
            className={cn(
              "flex items-center gap-3 rounded-md border border-border p-3 text-sm",
              active && "border-primary bg-primary/5",
              done && "bg-muted/40",
              isFailed && "border-destructive bg-destructive/5"
            )}
            key={label}
          >
            <span
              className={cn(
                "inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border",
                done && "border-[#0F6E56] bg-[#0F6E56] text-white",
                active && "border-primary text-primary",
                isFailed && "border-destructive text-destructive"
              )}
            >
              {done ? (
                <Check className="h-4 w-4" />
              ) : active ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                stepNumber
              )}
            </span>
            <span className="font-medium">{label}</span>
          </li>
        );
      })}
    </ol>
  );
}
