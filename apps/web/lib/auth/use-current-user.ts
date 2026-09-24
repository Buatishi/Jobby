"use client";

import { useEffect, useState } from "react";

import { apiClient } from "@/lib/api/client";
import type { CurrentUserProfile } from "@/lib/auth/permissions";

let pending: Promise<CurrentUserProfile | null> | null = null;

/** Un solo pedido por carga de página, compartido por todos los componentes. */
export function loadCurrentUser(): Promise<CurrentUserProfile | null> {
  pending ??= apiClient<CurrentUserProfile>("/api/v1/users/me").catch(() => {
    pending = null;
    return null;
  });
  return pending;
}

/** Olvida el perfil cargado: al cerrar sesión no debe quedar el de la persona anterior. */
export function forgetCurrentUser(): void {
  pending = null;
}

export function useCurrentUser(): CurrentUserProfile | null {
  const [profile, setProfile] = useState<CurrentUserProfile | null>(null);

  useEffect(() => {
    let active = true;
    void loadCurrentUser().then((loaded) => {
      if (active) {
        setProfile(loaded);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  return profile;
}
