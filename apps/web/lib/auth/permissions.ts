/** Permisos que la API reconoce; los otorga el rol guardado en la base, no el código. */
export const Permission = {
  MetricsRead: "metrics:read"
} as const;

export type PermissionName = (typeof Permission)[keyof typeof Permission];

export type CurrentUserProfile = {
  id: string;
  email: string | null;
  role: string;
  tier: string;
  permissions: string[];
};

/**
 * Decide qué opciones mostrar. No protege nada: la API vuelve a verificar el permiso en
 * cada pedido y responde 403 si falta.
 */
export function hasPermission(
  profile: CurrentUserProfile | null | undefined,
  permission: PermissionName
): boolean {
  return Boolean(profile?.permissions.includes(permission));
}
