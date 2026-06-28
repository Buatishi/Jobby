import type { UserTier } from "@jobmatch/shared-types";

import { AppSidebar } from "@/components/app-sidebar";
import { WizardRedirectGuard } from "@/components/wizard-redirect-guard";

type AppShellProps = {
  children: React.ReactNode;
  pendingAnalysesCount?: number;
  userTier?: UserTier;
};

export function AppShell({
  children,
  pendingAnalysesCount = 0,
  userTier = "free"
}: AppShellProps) {
  return (
    <div className="min-h-screen bg-muted/30 lg:grid lg:grid-cols-[18rem_1fr]">
      <WizardRedirectGuard />
      <AppSidebar
        pendingAnalysesCount={pendingAnalysesCount}
        userTier={userTier}
      />
      <div className="min-w-0">{children}</div>
    </div>
  );
}
