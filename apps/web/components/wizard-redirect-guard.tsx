"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import {
  getWizardProgress,
  hasWizardProgress,
  wizardStepPath
} from "@/lib/wizard/progress";

export function WizardRedirectGuard() {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!hasWizardProgress()) {
      return;
    }

    const progress = getWizardProgress();
    const isWizardRoute = pathname.startsWith("/wizard");

    if (!progress.completed && progress.currentStep > 0 && !isWizardRoute) {
      router.replace(wizardStepPath(progress.currentStep));
    }
  }, [pathname, router]);

  return null;
}
