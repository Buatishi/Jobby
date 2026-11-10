import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("@vercel/analytics/next", () => ({
  Analytics: () => <i data-analytics="on" />
}));

import PublicLayout from "@/src/app/(public)/layout";

const appDirectory = fileURLToPath(new URL("..", import.meta.url));

// Los archivos de una carpeta, a cualquier profundidad.
function filesUnder(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = `${directory}/${entry.name}`;
    return entry.isDirectory() ? filesUnder(path) : [path];
  });
}

describe("visit measurement", () => {
  it("measures the public pages and still renders them", () => {
    const html = renderToStaticMarkup(
      <PublicLayout>
        <p>Hola</p>
      </PublicLayout>
    );

    expect(html).toContain("<p>Hola</p>");
    expect(html).toContain('data-analytics="on"');
  });

  // Se mide de dónde llega la gente que no tiene cuenta: inicio, precios y guías. Lo que
  // pasa dentro de la cuenta (panel, puestos, reportes) y el acceso quedan afuera.
  it("never measures the signed-in app, the sign-in pages or every page at once", () => {
    const measured = filesUnder(appDirectory)
      .filter((file) => /\.(ts|tsx)$/.test(file) && !/\.test\.tsx?$/.test(file))
      .filter((file) => readFileSync(file, "utf8").includes("@vercel/analytics"))
      .map((file) => file.slice(appDirectory.length));

    expect(measured).toEqual(["/(public)/layout.tsx"]);
  });
});
