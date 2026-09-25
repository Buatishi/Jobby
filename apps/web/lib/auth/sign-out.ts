import { forgetSessionData } from "@/lib/auth/session-data";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

export const SIGNED_OUT_URL = "/login?signed_out=1";

type SignOutDependencies = {
  signOut: () => Promise<{ error: unknown }>;
  navigate: (url: string) => void;
};

/**
 * Cierra la sesión y vuelve al login. Devuelve false si no se pudo cerrar.
 *
 * Supabase Auth borra la sesión de este dispositivo, y la API rechaza desde ese momento el
 * token que la usaba aunque no haya vencido (migración 027). Si el pedido falla (por
 * ejemplo, sin conexión), Supabase no borra la sesión: en ese caso no se sale, para no
 * mostrar como cerrada una sesión que sigue abierta. La navegación es completa para que no
 * quede en memoria nada de la persona.
 */
export async function signOutAndLeave(
  dependencies: Partial<SignOutDependencies> = {}
): Promise<boolean> {
  const signOut =
    dependencies.signOut ??
    (() => createSupabaseBrowserClient().auth.signOut({ scope: "local" }));
  const navigate =
    dependencies.navigate ?? ((url: string) => window.location.assign(url));

  try {
    const { error } = await signOut();
    if (error) {
      return false;
    }
  } catch {
    return false;
  }

  forgetSessionData();
  navigate(SIGNED_OUT_URL);
  return true;
}
