import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

// Versiones mínimas por seguridad: si el lock vuelve atrás, este test lo avisa.
const lockfile = readFileSync(
  fileURLToPath(new URL("../../../../pnpm-lock.yaml", import.meta.url)),
  "utf8"
);

function resolvedVersions(name: string): string[] {
  const pattern = new RegExp(`^ {2}${name}@(\\d+\\.\\d+\\.\\d+):`, "gm");
  return [...lockfile.matchAll(pattern)].map((match) => match[1] ?? "");
}

function atLeast(version: string, minimum: string): boolean {
  const found = version.split(".").map(Number);
  const wanted = minimum.split(".").map(Number);
  for (let index = 0; index < wanted.length; index += 1) {
    const current = found[index] ?? 0;
    const required = wanted[index] ?? 0;
    if (current !== required) {
      return current > required;
    }
  }
  return true;
}

describe("security-sensitive dependencies keep their minimum version", () => {
  // La 6.x de postcss-selector-parser no tiene parche (alerta 81 de Dependabot: complejidad
  // cuadrática al analizar selectores). Tailwind 3 y postcss-nested la piden con ^6, así que
  // el override de package.json la sube a 7.1.6; la compilación y el CSS generado quedaron
  // idénticos (Decisión 28).
  it("resolves postcss-selector-parser to 7.1.6 or newer only", () => {
    const versions = resolvedVersions("postcss-selector-parser");

    expect(versions.length).toBeGreaterThan(0);
    expect(versions.filter((version) => !atLeast(version, "7.1.6"))).toEqual([]);
  });

  // Next 15.5.28 corrige GHSA-2464-fhr4-w9xw (ejecución remota de código sin autenticación
  // en la optimización de imágenes con SVG, crítica) y CVE-2026-94482 (denegación de
  // servicio contra Server Actions, alta). Es lo que sirve cada página de la web
  // (Decisión 28).
  it("resolves next to 15.5.28 or newer only", () => {
    const versions = resolvedVersions("next");

    expect(versions.length).toBeGreaterThan(0);
    expect(versions.filter((version) => !atLeast(version, "15.5.28"))).toEqual([]);
  });
});
