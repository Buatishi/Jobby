import { describe, expect, it } from "vitest";

import {
  availableFilters,
  filterLabels,
  matchesFilter
} from "@/lib/reality-gap/filters";

type Marks = Parameters<typeof matchesFilter>[0];

const skill = (overrides: Partial<Marks>): Marks => ({
  in_cv: true,
  in_linkedin: true,
  saved: true,
  confirmed: true,
  ...overrides
});

describe("matchesFilter", () => {
  it("lets everything through with «all»", () => {
    expect(matchesFilter(skill({ in_cv: null, in_linkedin: null }), "all")).toBe(
      true
    );
  });

  it.each([
    ["both", { in_cv: true, in_linkedin: true }, true],
    ["both", { in_cv: true, in_linkedin: false }, false],
    ["only_cv", { in_cv: true, in_linkedin: false }, true],
    ["only_cv", { in_cv: true, in_linkedin: true }, false],
    ["only_linkedin", { in_cv: false, in_linkedin: true }, true],
    ["only_linkedin", { in_cv: false, in_linkedin: false }, false]
  ] as const)("%s with %j is %s", (filter, marks, expected) => {
    expect(matchesFilter(skill(marks), filter)).toBe(expected);
  });

  it("does not guess when a document is missing", () => {
    // Sin el PDF de LinkedIn no se sabe si «solo está en el CV»: no entra en ningún grupo.
    const noLinkedin = skill({ in_cv: true, in_linkedin: null });
    expect(matchesFilter(noLinkedin, "both")).toBe(false);
    expect(matchesFilter(noLinkedin, "only_cv")).toBe(false);
    expect(matchesFilter(noLinkedin, "only_linkedin")).toBe(false);
  });

  it("counts as unconfirmed only the saved skills nobody confirmed", () => {
    expect(matchesFilter(skill({ confirmed: false }), "unconfirmed")).toBe(true);
    expect(matchesFilter(skill({ confirmed: true }), "unconfirmed")).toBe(false);
    // Una que solo nombra LinkedIn no está guardada: no hay nada que confirmar todavía.
    expect(
      matchesFilter(skill({ saved: false, confirmed: false }), "unconfirmed")
    ).toBe(false);
  });
});

describe("availableFilters", () => {
  it("always offers «all» and hides the groups with nothing in them", () => {
    const result = availableFilters([
      skill({ in_cv: true, in_linkedin: true }),
      skill({ in_cv: true, in_linkedin: false, confirmed: false })
    ]);

    expect(result).toEqual([
      { filter: "all", count: 2 },
      { filter: "both", count: 1 },
      { filter: "only_cv", count: 1 },
      { filter: "unconfirmed", count: 1 }
    ]);
  });

  it("offers only «all» for an empty list", () => {
    expect(availableFilters([])).toEqual([{ filter: "all", count: 0 }]);
  });

  it("has a label for every filter", () => {
    const filters = availableFilters([
      skill({ in_cv: true, in_linkedin: true, confirmed: false }),
      skill({ in_cv: true, in_linkedin: false }),
      skill({ in_cv: false, in_linkedin: true })
    ]).map(({ filter }) => filter);

    expect(filters).toHaveLength(5);
    for (const filter of filters) {
      expect(filterLabels[filter]).toBeTruthy();
    }
  });
});
