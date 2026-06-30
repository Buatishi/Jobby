import { NextResponse } from "next/server";

import { createSupabaseServerClient } from "@/lib/supabase/server";

type ServerSupabaseClient = Awaited<
  ReturnType<typeof createSupabaseServerClient>
>;

export async function exchangeAuthCode(
  requestUrl: URL,
  supabase: ServerSupabaseClient
) {
  const oauthError =
    requestUrl.searchParams.get("error_description") ??
    requestUrl.searchParams.get("error");
  const code = requestUrl.searchParams.get("code");
  const next = requestUrl.searchParams.get("next") ?? "/dashboard";

  if (oauthError) {
    const loginUrl = new URL("/login", requestUrl.origin);
    loginUrl.searchParams.set("error", oauthError);
    return NextResponse.redirect(loginUrl);
  }

  if (!code) {
    const loginUrl = new URL("/login", requestUrl.origin);
    loginUrl.searchParams.set("error", "No se recibió el código de Google.");
    return NextResponse.redirect(loginUrl);
  }

  if (code) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (error) {
      const loginUrl = new URL("/login", requestUrl.origin);
      loginUrl.searchParams.set("error", error.message);
      return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.redirect(new URL(next, requestUrl.origin));
}
