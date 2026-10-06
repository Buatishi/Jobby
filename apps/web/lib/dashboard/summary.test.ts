import { describe, expect, it } from "vitest";

import { clampScore, getFirstName, getInitials } from "@/lib/dashboard/summary";

describe("clampScore", () => {
  it("rounds and limits to 0-100", () => {
    expect(clampScore(78.4)).toBe(78);
    expect(clampScore(140)).toBe(100);
    expect(clampScore(-5)).toBe(0);
  });

  it("returns 0 when there is no usable number", () => {
    expect(clampScore(undefined)).toBe(0);
    expect(clampScore(null)).toBe(0);
    expect(clampScore(Number.NaN)).toBe(0);
  });
});

describe("getFirstName", () => {
  it("prefers the first word of the full name", () => {
    expect(getFirstName({ full_name: "Persona de Prueba" })).toBe("Persona");
  });

  it("falls back to the email local part", () => {
    expect(getFirstName({ email: "persona@example.com" })).toBe("persona");
  });

  it("is empty without data", () => {
    expect(getFirstName(undefined)).toBe("");
  });
});

describe("getInitials", () => {
  it("uses two letters of one word and one letter of two words", () => {
    expect(getInitials("Acme")).toBe("AC");
    expect(getInitials("Empresa Ejemplo")).toBe("EE");
  });

  it("skips empty names and falls back to a placeholder", () => {
    expect(getInitials("", "Backend Developer")).toBe("BD");
    expect(getInitials(null, undefined)).toBe("?");
  });
});
