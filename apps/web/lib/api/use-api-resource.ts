"use client";

import { useCallback, useEffect, useState } from "react";

import { apiClient } from "@/lib/api/client";

// Última respuesta de cada pantalla, solo en la memoria de esta pestaña: se pierde al recargar
// y se borra al iniciar o cerrar sesión, así que no queda nada de la persona en el navegador.
const lastResponses = new Map<string, unknown>();
// Cambia al olvidar: una respuesta pedida antes no vuelve a entrar si llega después.
let generation = 0;

export function forgetApiResources(): void {
  lastResponses.clear();
  generation += 1;
}

export function rememberedResponse<T>(path: string): T | undefined {
  return lastResponses.get(path) as T | undefined;
}

function remember(path: string, data: unknown): void {
  if (data === undefined) {
    lastResponses.delete(path);
  } else {
    lastResponses.set(path, data);
  }
}

/** Pide `path` a la API y guarda la respuesta, salvo que la sesión haya cambiado mientras. */
export async function fetchAndRemember<T>(path: string): Promise<T> {
  const startedIn = generation;
  const fresh = await apiClient<T>(path);
  if (startedIn === generation) {
    remember(path, fresh);
  }
  return fresh;
}

type ApiResource<T> = {
  data: T | undefined;
  /** Mensaje del último pedido fallido; null si salió bien o todavía no terminó. */
  error: string | null;
  /** Solo es true mientras no hay nada para mostrar. */
  loading: boolean;
  /** Cambia los datos en pantalla y en la memoria; por ejemplo, después de editar. */
  mutate: (update: (current: T | undefined) => T | undefined) => void;
};

/**
 * Datos de una pantalla (con `path` fijo). Si ya se pidieron en esta pestaña, se muestra al
 * instante la respuesta anterior mientras llega la nueva; si la nueva falla, queda la anterior
 * a la vista junto con el error.
 */
export function useApiResource<T>(path: string, fallbackError: string): ApiResource<T> {
  const [data, setData] = useState<T | undefined>(() => rememberedResponse<T>(path));
  const [failure, setFailure] = useState<{ cause: unknown } | null>(null);
  const [loading, setLoading] = useState(() => !lastResponses.has(path));

  useEffect(() => {
    let active = true;
    fetchAndRemember<T>(path)
      .then((fresh) => {
        if (active) {
          setData(fresh);
          setFailure(null);
        }
      })
      .catch((cause: unknown) => {
        if (active) {
          setFailure({ cause });
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [path]);

  const mutate = useCallback(
    (update: (current: T | undefined) => T | undefined) => {
      setData((current) => {
        const next = update(current);
        remember(path, next);
        return next;
      });
    },
    [path]
  );

  const error =
    failure === null
      ? null
      : failure.cause instanceof Error
        ? failure.cause.message
        : fallbackError;

  return { data, error, loading, mutate };
}
