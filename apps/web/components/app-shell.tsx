import { AppSidebar } from "@/components/app-sidebar";
import { WizardRedirectGuard } from "@/components/wizard-redirect-guard";

type AppShellProps = {
  children: React.ReactNode;
  pendingAnalysesCount?: number;
  userName?: string;
};

export function AppShell({
  children,
  pendingAnalysesCount = 0,
  userName
}: AppShellProps) {
  return (
    <div className="min-h-screen bg-white lg:grid lg:grid-cols-[15rem_1fr]">
      <WizardRedirectGuard />
      <AppSidebar
        pendingAnalysesCount={pendingAnalysesCount}
        userName={userName}
      />
      <div className="min-w-0 bg-white">{children}</div>
    </div>
  );
}
