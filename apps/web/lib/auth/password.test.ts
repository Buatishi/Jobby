import { describe, expect, it } from "vitest";

import { validateNewPassword } from "@/lib/auth/password";

describe("validateNewPassword", () => {
  it("accepts a long enough password that matches its confirmation", () => {
    expect(validateNewPassword("secreta123", "secreta123")).toBeNull();
  });

  it("rejects a password shorter than 8 characters", () => {
    expect(validateNewPassword("corta", "corta")).toBe(
      "La contraseña debe tener al menos 8 caracteres."
    );
  });

  it("rejects a confirmation that does not match", () => {
    expect(validateNewPassword("secreta123", "otra12345")).toBe(
      "Las contraseñas no coinciden."
    );
  });
});