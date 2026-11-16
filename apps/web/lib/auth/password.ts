export const MIN_PASSWORD_LENGTH = 8;

/** Devuelve el mensaje de error a mostrar, o null si la contraseña nueva es válida. */
export function validateNewPassword(
  password: string,
  confirmation: string
): string | null {
  if (password.length < MIN_PASSWORD_LENGTH) {
    return `La contraseña debe tener al menos ${MIN_PASSWORD_LENGTH} caracteres.`;
  }
  if (password !== confirmation) {
    return "Las contraseñas no coinciden.";
  }
  return null;
}