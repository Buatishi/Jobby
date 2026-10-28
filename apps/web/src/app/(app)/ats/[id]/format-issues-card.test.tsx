import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { dictionaries } from "@/lib/i18n/dictionaries";
import { I18nProvider } from "@/lib/i18n/provider";
import {
  FormatIssuesCard,
  formatWasEvaluated
} from "@/src/app/(app)/ats/[id]/format-issues-card";

const issues = [
  { code: "MULTI_COLUMN", message: "El CV usa múltiples columnas.", penalty: 10 },
  { code: "IMAGES", message: "El CV contiene imágenes.", penalty: 10 }
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
  it("lists each format issue with the percentage it takes off", () => {
    const html = render({ issues, evaluated: true });

    expect(html).toContain("El CV usa múltiples columnas.");
    expect(html).toContain("El CV contiene imágenes.");
    expect(html).toContain("-10%");
    expect(html).toContain(es.atsFormatPenaltyHint);
    expect(html).not.toContain(es.atsFormatNotEvaluatedTitle);
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
    expect(html).not.toContain(es.atsFormatClean);
    expect(html).not.toContain("No detectamos problemas de formato.");
  });

  it("has every text it shows in Spanish and in English", () => {
    for (const key of [
      "atsFormatTitle",
      "atsFormatClean",
      "atsFormatPenaltyHint",
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
