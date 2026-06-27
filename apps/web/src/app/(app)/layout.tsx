import { requireAuthenticatedSession } from "@/lib/auth/guard";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { AppShell } from "@/components/app-shell";

export const dynamic = "force-dynamic";

export default async function AppLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  const supabase = await createSupabaseServerClient();
  await requireAuthenticatedSession(supabase);

  return (
    <AppShell pendingAnalysesCount={2} userTier="free">
      {children}
    </AppShell>
  );
}
