import type { SupabaseClient } from "@supabase/supabase-js";

type GoogleSignInAuth = Pick<
  SupabaseClient["auth"],
  "getSession" | "stopAutoRefresh" | "startAutoRefresh" | "signInWithOAuth"
>;

/**
 * Empieza el inicio de sesión con Google. Devuelve el mensaje de error, o null si el
 * navegador ya va camino a Google.
 */
export async function startGoogleSignIn(
  auth: GoogleSignInAuth,
  origin: string
): Promise<string | null> {
  // signInWithOAuth no espera a que el cliente termine de iniciar. Si en ese momento
  // renueva una sesión que ya estaba abierta, al guardarla la librería borra el
  // verificador PKCE recién creado y la vuelta de Google falla con «PKCE code verifier
  // not found». Por eso primero se deja terminar la inicialización y se frena la
  // renovación automática.
  await auth.getSession();
  await auth.stopAutoRefresh();

  const { error } = await auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: `${origin}/api/auth/callback?next=/dashboard`,
      queryParams: {
        access_type: "offline",
        prompt: "select_account"
      }
    }
  });

  if (error) {
    await auth.startAutoRefresh();
    return error.message;
  }
  return null;
}
