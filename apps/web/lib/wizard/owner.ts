import { loadCurrentUser } from "@/lib/auth/use-current-user";

/**
 * El id de la cuenta que usa el wizard, o `null` si no se pudo saber. Es el dueño bajo el
 * que se guarda el avance (ver `progress.ts`).
 */
export async function resolveWizardOwner(
  load: () => Promise<{ id: string } | null> = loadCurrentUser
): Promise<string | null> {
  try {
    return (await load())?.id ?? null;
  } catch {
    return null;
  }
}
