import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  RequirementsCard,
  type ATSRequirement
} from "@/src/app/(app)/ats/[id]/requirements-card";

const experience: ATSRequirement = {
  key: "experience",
  label: "Experiencia directa",
  required: "5 años (según el nivel del puesto)",
  actual: "6 meses",
  status: "unmet",
  ratio: 0.1,
  note: null,
  estimated: true,
  detail: [
    "Paogi — Python Developer: 3 meses",
    "Independiente — Operador Digital: no cuenta (no se relaciona con lo que pide el puesto)"
  ]
};

const language: ATSRequirement = {
  key: "language:english",
  label: "Inglés",
  required: "nivel no indicado",
  actual: "avanzado",
  status: "met",
  ratio: 1,
  note: "Superás lo pedido: no suma ni resta puntos.",
  estimated: false,
  detail: []
};

describe("RequirementsCard", () => {
  it("shows what the posting asks, what the person has and whether it is met", () => {
    const html = renderToStaticMarkup(
      <RequirementsCard requirements={[experience, language]} />
    );

    expect(html).toContain("Requisitos del puesto");
    expect(html).toContain("Experiencia directa");
    expect(html).toContain("Pide: 5 años (según el nivel del puesto)");
    expect(html).toContain("6 meses");
    expect(html).toContain("No cumple");
    expect(html).toContain("Inglés");
    expect(html).toContain("Cumple");
  });

  it("explains a requirement the person exceeds without scoring it", () => {
    const html = renderToStaticMarkup(<RequirementsCard requirements={[language]} />);

    expect(html).toContain("Superás lo pedido: no suma ni resta puntos.");
  });

  it("lists which roles were counted and which were not", () => {
    const html = renderToStaticMarkup(<RequirementsCard requirements={[experience]} />);

    expect(html).toContain("Qué se tuvo en cuenta");
    expect(html).toContain("Paogi — Python Developer: 3 meses");
    expect(html).toContain("no cuenta (no se relaciona con lo que pide el puesto)");
  });

  it("labels a partial requirement as partial", () => {
    const html = renderToStaticMarkup(
      <RequirementsCard requirements={[{ ...language, status: "partial", note: null }]} />
    );

    expect(html).toContain("Cumple en parte");
  });

  it("shows nothing when the posting asks for nothing or the API sends nothing", () => {
    expect(renderToStaticMarkup(<RequirementsCard requirements={[]} />)).toBe("");
    expect(renderToStaticMarkup(<RequirementsCard requirements={undefined} />)).toBe("");
  });
});
