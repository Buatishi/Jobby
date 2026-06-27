import { redirect } from "next/navigation";

import { createSupabaseServerClient } from "@/lib/supabase/server";

type ServerSupabaseClient = Awaited<
  ReturnType<typeof createSupabaseServerClient>
>;

export async function requireAuthenticatedSession(
  supabase: ServerSupabaseClient
) {
  const {
    data: { session }
  } = await supabase.auth.getSession();

  if (!session) {
    redirect("/login");
  }

  return session;
}
