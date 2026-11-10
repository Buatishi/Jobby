import { describe, expect, it } from "vitest";

import { ABOUT_PAGE } from "@/lib/about/about";
import {
  CV_OPTIMIZATIONS_PER_MONTH,
  FREE_JOB_ANALYSES_PER_MONTH,
  MATCH_SCORE_WEIGHTS,
  formatPercent
} from "@/lib/guides/facts";
import { GUIDES } from "@/lib/guides/guides";

// Todo el texto de la página en un solo bloque: introducción, secciones y preguntas.
function allText(): string {
  const blocks = ABOUT_PAGE.sections.flatMap((section) =>
    section.blocks.flatMap((block) =>
      block.type === "paragraph" ? [block.text] : block.items
    )
  );
  const faq = ABOUT_PAGE.faq.flatMap((item) => [item.question, item.answer]);
  return [ABOUT_PAGE.intro, ...blocks, ...faq].join("\n");
}

describe("«Qué es Jobby» page content", () => {
  it("fits the results page: short title, description of a useful length", () => {
    expect(ABOUT_PAGE.seoTitle.length).toBeLessThanOrEqual(60);
    expect(ABOUT_PAGE.description.length).toBeGreaterThanOrEqual(70);
    expect(ABOUT_PAGE.description.length).toBeLessThanOrEqual(160);
  });

  // Las cifras salen de `facts.ts`, que `guides.test.ts` compara con el backend: si el
  // producto cambia, esta página no puede quedar con un número viejo.
  it("gives the six weights of the match score the guides cite", () => {
    const text = allText();

    for (const weight of MATCH_SCORE_WEIGHTS) {
      expect(text, weight.label).toContain(
        `${weight.label} (${formatPercent(weight.percent)})`
      );
    }
  });

  it("quotes the limits of each plan from the shared facts", () => {
    const text = allText();

    expect(text).toContain(`${FREE_JOB_ANALYSES_PER_MONTH} análisis de puestos por mes`);
    expect(text).toContain(`${CV_OPTIMIZATIONS_PER_MONTH.free} optimizaciones de CV por mes`);
    expect(text).toContain(`${CV_OPTIMIZATIONS_PER_MONTH.premium} por mes`);
  });

  it("promises no result and says what Jobby does not do", () => {
    const text = allText().toLowerCase();

    expect(text).toContain("no garantiza");
    expect(text).toContain("no inventa");
    expect(text).toContain("no es el puntaje de ningún ats real");
  });

  it("has a question and a plain-text answer for every FAQ entry", () => {
    expect(ABOUT_PAGE.faq.length).toBeGreaterThanOrEqual(8);
    for (const { question, answer } of ABOUT_PAGE.faq) {
      expect(question.endsWith("?"), question).toBe(true);
      expect(question.startsWith("¿"), question).toBe(true);
      // El marcado del buscador lleva la respuesta tal cual: sin etiquetas ni Markdown.
      expect(answer, question).not.toMatch(/[<>*_`#]/);
      expect(answer.length, question).toBeGreaterThan(40);
    }
    expect(new Set(ABOUT_PAGE.faq.map((item) => item.question)).size).toBe(
      ABOUT_PAGE.faq.length
    );
  });

  it("only links to pages that exist", () => {
    const guideSlugs = GUIDES.map((guide) => guide.slug);

    expect(ABOUT_PAGE.links.length).toBeGreaterThan(0);
    for (const { path, label } of ABOUT_PAGE.links) {
      expect(label.length, path).toBeGreaterThan(0);
      const exists =
        ["/pricing", "/privacy", "/terms", "/guias"].includes(path) ||
        guideSlugs.some((slug) => path === `/guias/${slug}`);
      expect(exists, path).toBe(true);
    }
  });
});
