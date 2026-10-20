import { apiClient } from "@/lib/api/client";

export type RatingStatus = "idle" | "saving" | "saved" | "error";

export type RatingState = {
  rating: number | null;
  status: RatingStatus;
};

/**
 * Estado de la calificación de un match, sin React para poder probarlo con el
 * `apiClient` mockeado. La estrella se pinta antes de que responda la API y se
 * revierte si el guardado falla.
 */
export function createRatingStore(
  matchId: string,
  initialRating: number | null
) {
  let state: RatingState = { rating: initialRating, status: "idle" };
  const listeners = new Set<() => void>();

  function setState(next: RatingState) {
    state = next;
    listeners.forEach((listener) => listener());
  }

  async function select(value: number) {
    // Un solo pedido a la vez: si ya hay uno en curso, el clic se ignora.
    if (state.status === "saving") {
      return;
    }

    const previousRating = state.rating;
    setState({ rating: value, status: "saving" });

    try {
      await apiClient<unknown>(`/api/v1/matches/${matchId}/rating`, {
        method: "PATCH",
        idempotent: true,
        body: JSON.stringify({ rating: value })
      });
      setState({ rating: value, status: "saved" });
    } catch {
      setState({ rating: previousRating, status: "error" });
    }
  }

  return {
    // Referencias estables: `useSyncExternalStore` las usa como dependencias.
    getState: () => state,
    subscribe(listener: () => void) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    select
  };
}
