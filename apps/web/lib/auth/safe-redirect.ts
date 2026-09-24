const DEFAULT_PATH = "/dashboard";
// Origen ficticio: solo sirve para que URL resuelva la ruta y detecte si escapa a otro dominio.
const PLACEHOLDER_ORIGIN = "http://jobby.invalid";

/**
 * Devuelve una ruta interna segura para redirigir después del login.
 *
 * El parámetro `next` llega en la URL y lo puede escribir cualquiera: sin este filtro,
 * `/login?next=https://sitio-falso` mandaría a la persona, ya autenticada, a otro dominio.
 * Solo se aceptan rutas del mismo sitio; lo demás vuelve al panel.
 */
export function safeRedirectPath(
  value: string | null | undefined,
  fallback: string = DEFAULT_PATH
): string {
  if (!value || !value.startsWith("/")) {
    return fallback;
  }

  try {
    const url = new URL(value, PLACEHOLDER_ORIGIN);
    if (url.origin !== PLACEHOLDER_ORIGIN) {
      return fallback;
    }
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return fallback;
  }
}
