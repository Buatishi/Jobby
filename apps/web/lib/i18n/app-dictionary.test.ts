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
});
