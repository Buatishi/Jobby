import type { ReactNode } from "react";

import { WizardOwnerProvider } from "@/components/wizard-owner";

export default function WizardLayout({ children }: { children: ReactNode }) {
  return <WizardOwnerProvider>{children}</WizardOwnerProvider>;
}
