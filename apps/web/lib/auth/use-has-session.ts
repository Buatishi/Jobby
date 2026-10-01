"use client";

import { useEffect, useState } from "react";

import { createSupabaseBrowserClient } from "@/lib/supabase/client";

/**
 * Si este navegador tiene una sesión abierta: `null` mientras se lee, después `true` o `false`.
 *
 * Lee la sesión guardada en el navegador y no hace ningún pedido a la API. Sirve para que
 * las páginas públicas (landing, Premium) no parezcan una sesión cerrada cuando no lo está.
 */
export function useHasSession(): boolean | null {
  const [hasSession, setHasSession] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;

    async function readSession() {
      try {
        const { data } = await createSupabaseBrowserClient().auth.getSession();
        if (active) {
          setHasSession(data.session !== null);
        }
      } catch {
        if (active) {
          setHasSession(false);
        }
      }
    }

    void readSession();
    return () => {
      active = false;
    };
  }, []);

  return hasSession;
}
