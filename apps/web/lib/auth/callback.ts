import { NextResponse } from "next/server";

import { safeRedirectPath } from "@/lib/auth/safe-redirect";
import { createSupabaseServerClient } from "@/lib/supabase/server";

type ServerSupabaseClient = Awaited<
  ReturnType<typeof createSupabaseServerClient>
>;

// El verificador PKCE vive en una cookie del navegador que empezó el inicio con Google:
// sin ella el código no se puede canjear (otro navegador, o la cookie se borró).
function describeExchangeError(error: { code?: string; message: string }) {
  return error.code === "pkce_code_verifier_not_found"
    ? "No pudimos terminar el inicio con Google en este navegador. Volvé a intentarlo."
    : error.message;
}

export async function exchangeAuthCode(
  requestUrl: URL,
  supabase: ServerSupabaseClient
) {
  const oauthError =
    requestUrl.searchParams.get("error_description") ??
    requestUrl.searchParams.get("error");
  const code = requestUrl.searchParams.get("code");
  const next = safeRedirectPath(requestUrl.searchParams.get("next"));

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
      loginUrl.searchParams.set("error", describeExchangeError(error));
      return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.redirect(new URL(next, requestUrl.origin));
}
