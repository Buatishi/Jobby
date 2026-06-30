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
  const session = await requireAuthenticatedSession(supabase);
  const userName =
    typeof session.user.user_metadata.full_name === "string"
      ? session.user.user_metadata.full_name
      : session.user.email ?? undefined;

  return (
    <AppShell userName={userName} userTier="free">
      {children}
    </AppShell>
  );
}
