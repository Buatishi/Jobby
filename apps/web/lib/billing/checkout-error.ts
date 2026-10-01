import { ApiAuthenticationError } from "@/lib/api/client";

/**
 * Si una falla al pedir el checkout se muestra como «los pagos todavía no están
 * disponibles». Solo la sesión vencida tiene su propio mensaje: la persona tiene que volver
 * a entrar. Todo lo demás (Lemon, configuración, red) es del lado nuestro.
 */
export function isCheckoutUnavailable(error: unknown): boolean {
  return !(error instanceof ApiAuthenticationError);
}
