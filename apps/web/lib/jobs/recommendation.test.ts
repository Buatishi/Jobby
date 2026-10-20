import { describe, expect, it } from "vitest";

import {
  toRecommendationView,
  type Recommendation
} from "@/lib/jobs/recommendation";

// Así las guarda el backend: title = línea[:80] y description = la línea completa,
// y su regex de bullets se come los `*` iniciales (queda solo el `**` de cierre).
function stored(line: string): Recommendation {
  return { title: line.slice(0, 80), description: line, priority: "high" };
}

describe("toRecommendationView", () => {
  it("uses what comes before the colon as heading and the rest as body", () => {
    const view = toRecommendationView(
      stored(
        "Agregá SQL explícito al CV**: mencioná consultas, joins y mantenimiento de base"
      )
    );

    expect(view).toEqual({
      heading: "Agregá SQL explícito al CV",
      body: "mencioná consultas, joins y mantenimiento de base"
    });
  });

  it("does not show the title cut at 80 characters nor repeat the text in the body", () => {
    const line =
      'Sumá "API REST" y "Git" como skills nombradas**: incluí proyectos donde hayas construido o consumido APIs y trabajado con Git en equipo.';
    const recommendation = stored(line);
    expect(recommendation.title).toHaveLength(80);

    const view = toRecommendationView(recommendation);

    expect(view).toEqual({
      heading: 'Sumá "API REST" y "Git" como skills nombradas',
      body: "incluí proyectos donde hayas construido o consumido APIs y trabajado con Git en equipo."
    });
  });

  it("removes balanced bold markers from the start of the text", () => {
    const view = toRecommendationView(
      stored("**Mencioná liderazgo**: contá cómo coordinaste al equipo en tu último proyecto")
    );

    expect(view).toEqual({
      heading: "Mencioná liderazgo",
      body: "contá cómo coordinaste al equipo en tu último proyecto"
    });
  });

  it("uses the whole text as heading and no body when there is no colon", () => {
    const view = toRecommendationView(stored("Agregá React al CV"));

    expect(view).toEqual({ heading: "Agregá React al CV", body: null });
  });

  it("does not split on colons that are not followed by a space", () => {
    const view = toRecommendationView(
      stored("Publicá tu GitHub en https://github.com/usuario y ordená los repos")
    );

    expect(view).toEqual({
      heading: "Publicá tu GitHub en https://github.com/usuario y ordená los repos",
      body: null
    });
  });

  it("keeps the heading and no body when the colon is at the end", () => {
    const view = toRecommendationView(stored("**Reforzá estos puntos:**"));

    expect(view).toEqual({ heading: "Reforzá estos puntos", body: null });
  });

  it("splits a recommendation that has only a title", () => {
    const view = toRecommendationView({
      title: "Sumá Docker**: mencioná contenedores en tus proyectos"
    });

    expect(view).toEqual({
      heading: "Sumá Docker",
      body: "mencioná contenedores en tus proyectos"
    });
  });

  it("splits a recommendation that has only a description", () => {
    const view = toRecommendationView({
      description: "Sumá Docker**: mencioná contenedores en tus proyectos"
    });

    expect(view).toEqual({
      heading: "Sumá Docker",
      body: "mencioná contenedores en tus proyectos"
    });
  });

  it("respects a real title that is not a cut of the description", () => {
    const view = toRecommendationView({
      title: "**Reforzá tu stack**",
      description: "Mencioná: React, Node y SQL en la sección de skills."
    });

    expect(view).toEqual({
      heading: "Reforzá tu stack",
      body: "Mencioná: React, Node y SQL en la sección de skills."
    });
  });

  it("removes other raw markdown marks", () => {
    const view = toRecommendationView({
      description:
        "## Documentá tu `SQL` con *ejemplos* y _casos_: leé [esta guía](https://example.com/sql) y usá snake_case_names"
    });

    expect(view).toEqual({
      heading: "Documentá tu SQL con ejemplos y casos",
      body: "leé esta guía y usá snake_case_names"
    });
  });

  it("never leaves asterisks in the result", () => {
    const view = toRecommendationView(
      stored("**Primero** **segundo**: **tercero** y ** cuarto")
    );

    expect(`${view?.heading} ${view?.body}`).not.toContain("*");
  });

  it("returns null when there is nothing to show", () => {
    expect(toRecommendationView({})).toBeNull();
    expect(toRecommendationView({ title: "", description: "   " })).toBeNull();
    expect(toRecommendationView({ title: "**", description: "****" })).toBeNull();
  });
});
