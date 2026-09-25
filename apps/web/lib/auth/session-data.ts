import { forgetApiResources } from "@/lib/api/use-api-resource";
import { forgetCurrentUser } from "@/lib/auth/use-current-user";

/**
 * Borra lo que la pestaña guardó en memoria de la sesión (perfil y pantallas). Se llama al
 * iniciar sesión, al registrarse y al salir: sin esto, quien entra con otra cuenta en la misma
 * pestaña vería por un momento los datos o las opciones de la anterior.
 */
export function forgetSessionData(): void {
  forgetCurrentUser();
  forgetApiResources();
}
