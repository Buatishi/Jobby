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

describe("landing dictionary", () => {
  const es = flatten(dictionaries.es.landing as Tree).sort();
  const en = flatten(dictionaries.en.landing as Tree).sort();

  it("has the same keys in Spanish and English", () => {
    expect(en).toEqual(es);
  });

  it("keeps the keys the pricing page still reads", () => {
    for (const key of [
      "freeFeatures.one",
      "premiumFeatures.five",
      "monthly",
      "yearly",
      "perMonth",
      "perYear"
    ]) {
      expect(es).toContain(key);
    }
  });
});
