import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { dictionaries } from "@/lib/i18n/dictionaries";
import { I18nProvider } from "@/lib/i18n/provider";
import {
  FormatIssuesCard,
  formatWasEvaluated
} from "@/src/app/(app)/ats/[id]/format-issues-card";

const issues = [
  { code: "MULTI_COLUMN", message: "El CV usa múltiples columnas.", penalty: 4 },
  { code: "IMAGES", message: "El CV contiene imágenes.", penalty: 3 }
];

function render(props: Parameters<typeof FormatIssuesCard>[0]) {
  return renderToStaticMarkup(
    <I18nProvider>
      <FormatIssuesCard {...props} />
    </I18nProvider>
  );
}

const es = dictionaries.es.app as Record<string, string>;
const en = dictionaries.en.app as Record<string, string>;

describe("FormatIssuesCard", () => {
  it("lists each format issue with the points it takes off", () => {
    const html = render({ issues, evaluated: true, points: 3 });

    expect(html).toContain("El CV usa múltiples columnas.");
    expect(html).toContain("El CV contiene imágenes.");
    expect(html).toContain("−4");
    expect(html).toContain("−3");
    expect(html).not.toContain(es.atsFormatNotEvaluatedTitle);
  });

  it("shows the format points out of ten", () => {
    const html = render({ issues, evaluated: true, points: 3 });

    expect(html).toContain(es.atsFormatPointsLabel);
    expect(html).toMatch(/3\s*(<!-- -->)?\s*\/\s*(<!-- -->)?\s*10/);
  });

  it("says the format is our own estimate and not the score of a real ATS", () => {
    for (const props of [
      { issues, evaluated: true, points: 3 },
      { issues: [], evaluated: true, points: 10 }
    ]) {
      const html = render(props);

      expect(html).toContain(es.atsFormatEstimate);
      expect(es.atsFormatEstimate).toContain("no el puntaje de ningún ATS real");
    }
  });

  it("does not show a penalty for a notice that takes no points", () => {
    const html = render({
      issues: [
        {
          code: "NON_STANDARD_HEADERS",
          message: "Ningún título de sección del CV es de los habituales.",
          penalty: 0
        }
      ],
      evaluated: true,
      points: 10
    });

    expect(html).toContain("Ningún título de sección");
    expect(html).not.toContain("−0");
  });

  it("shows no points when the API does not send them", () => {
    const html = render({ issues, evaluated: true });

    expect(html).not.toContain(es.atsFormatPointsLabel);
  });

  it("says no problems were found only when the format was evaluated", () => {
    const html = render({ issues: [], evaluated: true });

    expect(html).toContain(es.atsFormatClean);
    expect(html).not.toContain(es.atsFormatNotEvaluatedTitle);
  });

  it("says the format could not be evaluated instead of reporting no problems", () => {
    const html = render({ issues: [], evaluated: false });

    expect(html).toContain(es.atsFormatNotEvaluatedTitle);
    expect(html).toContain("Volvé a subir tu CV");
    // No evaluado: el formato no cuenta, y la tarjeta no inventa puntos ni estimación.
    expect(html).toContain("no cuenta en el puntaje de este reporte");
    expect(html).not.toContain(es.atsFormatPointsLabel);
    expect(html).not.toContain(es.atsFormatEstimate);
    expect(html).not.toContain(es.atsFormatClean);
    expect(html).not.toContain("No detectamos problemas de formato.");
  });

  it("has every text it shows in Spanish and in English", () => {
    for (const key of [
      "atsFormatTitle",
      "atsFormatClean",
      "atsFormatPointsLabel",
      "atsFormatEstimate",
      "atsFormatNotEvaluatedTitle",
      "atsFormatNotEvaluatedHint"
    ]) {
      expect(es[key], key).toBeTruthy();
      expect(en[key], key).toBeTruthy();
      expect(en[key], key).not.toBe(es[key]);
    }
  });
});

describe("formatWasEvaluated", () => {
  it("is false only when the API says the format was not evaluated", () => {
    expect(formatWasEvaluated({ format_evaluated: false })).toBe(false);
    expect(formatWasEvaluated({ format_evaluated: true })).toBe(true);
  });

  it("keeps the old behavior when the API does not send the field yet", () => {
    expect(formatWasEvaluated({})).toBe(true);
  });
});
