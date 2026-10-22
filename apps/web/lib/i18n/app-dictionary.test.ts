import { describe, expect, it } from "vitest";

import { dictionaries } from "@/lib/i18n/dictionaries";

type Tree = { [key: string]: string | Tree };

function flatten(tree: Tree, prefix = ""): string[] {
  return Object.entries(tree).flatMap(([key, value]) =>
    typeof value === "string"
      ? [`${prefix}${key}`]
      : flatten(value, `${prefix}${key}.`)
  );
}

describe("app dictionary", () => {
  const es = flatten(dictionaries.es.app as Tree).sort();
  const en = flatten(dictionaries.en.app as Tree).sort();

  it("has the same keys in Spanish and English", () => {
    expect(en).toEqual(es);
  });

  it("names the dashboard figure as an average, in both languages", () => {
    expect(es).not.toContain("globalScore");
    expect((dictionaries.es.app as Tree).averageScore).toBe(
      "Promedio de tus últimos 5 análisis"
    );
    expect((dictionaries.en.app as Tree).averageScore).toBe(
      "Average of your last 5 analyses"
    );

    for (const key of [
      "averageScoreHint",
      "averageScoreEmptyHint",
      "potentialScoreHint",
      "representationScoreHint"
    ]) {
      expect(es).toContain(key);
    }
  });

  it("keeps the keys the ATS entry points read", () => {
    for (const key of [
      "viewAtsReport",
      "atsListTitle",
      "atsListDescription",
      "atsEmptyTitle",
      "atsEmptyDescription",
      "atsAnalyzeNew",
      "atsLoading",
      "atsLoadError"
    ]) {
      expect(es).toContain(key);
    }
  });

  it("keeps the keys the match rating card reads", () => {
    for (const key of ["ratingThanks", "ratingSaveError"]) {
      expect(es).toContain(key);
    }
  });

  it("keeps the keys the CV card and the LinkedIn PDF labels read", () => {
    for (const key of [
      "cvCardTitle",
      "cvCardDescription",
      "cvCardReplaceNote",
      "cvCardCurrent",
      "cvCardCurrentNoDate",
      "cvCardPick",
      "cvCardUpload",
      "cvCardProcessing",
      "cvCardPickFirst",
      "cvCardUploadError",
      "cvCardDone",
      "cvCardStillReading",
      "cvStageUploading",
      "cvStageRegistering",
      "cvStageReading",
      "cvReadFailedHint",
      "linkedinPdfLabel",
      "linkedinPdfNotCv",
      "linkedinPdfHowTo"
    ]) {
      expect(es).toContain(key);
    }
  });

  it("tells the CV and the LinkedIn PDF apart in both languages", () => {
    const esApp = dictionaries.es.app as Tree;
    const enApp = dictionaries.en.app as Tree;

    expect(esApp.cvCardDescription).toMatch(/empresas/);
    expect(enApp.cvCardDescription).toMatch(/employers/);
    expect(esApp.linkedinPdfNotCv).toMatch(/No es tu CV/);
    expect(esApp.linkedinPdfNotCv).toMatch(/Guardar en PDF/);
    expect(enApp.linkedinPdfNotCv).toMatch(/not your CV/i);
    expect(enApp.linkedinPdfNotCv).toMatch(/Save to PDF/);
  });
});
