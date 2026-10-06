"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { ArrowRight, X } from "lucide-react";

import {
  getWizardProgress,
  hasWizardProgress,
  wizardStepPath,
  type WizardProgress
} from "@/lib/wizard/progress";

export function WizardRedirectGuard() {
  const pathname = usePathname();
  const [progress, setProgress] = useState<WizardProgress | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (hasWizardProgress()) {
      setProgress(getWizardProgress());
    }
  }, [pathname]);

  if (!progress || progress.completed || dismissed || pathname.startsWith("/wizard")) {
    return null;
  }

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 rounded-card border border-brand-green/20 bg-background p-4 shadow-lg sm:left-auto sm:max-w-md">
      <div className="flex gap-3">
        <div className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-brand-green-light text-sm font-semibold text-brand-green">
          {progress.currentStep}
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-medium">Terminá tu onboarding cuando quieras</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Guardamos tu avance. Podés seguir navegando o retomar el paso
            pendiente para mejorar tus reportes.
          </p>
          <Link
            className="mt-3 inline-flex items-center text-sm font-medium text-brand-green"
            href={wizardStepPath(progress.currentStep)}
          >
            Retomar onboarding
            <ArrowRight className="ml-1 h-4 w-4" />
          </Link>
        </div>
        <button
          aria-label="Ocultar aviso de onboarding"
          className="flex h-8 w-8 flex-none items-center justify-center rounded-full hover:bg-muted"
          onClick={() => setDismissed(true)}
          type="button"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
