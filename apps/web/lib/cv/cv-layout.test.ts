import { describe, expect, it } from "vitest";

import {
  experienceBullets,
  formatMonthYear,
  formatPeriod,
  MAX_SKILL_CELLS,
  skillCells,
  splitSentences
} from "@/lib/cv/cv-layout";

describe("formatMonthYear", () => {
  it("writes the month in Spanish with a capital letter", () => {
    expect(formatMonthYear("2026-07-01")).toBe("Julio 2026");
    expect(formatMonthYear("2025-01")).toBe("Enero 2025");
    expect(formatMonthYear("2024-12-31")).toBe("Diciembre 2024");
  });

  it("keeps a lone year as it is", () => {
    expect(formatMonthYear("2020")).toBe("2020");
    expect(formatMonthYear("2020-13-01")).toBe("2020");
  });

  it("keeps the date as the CV wrote it when it is not an ISO date", () => {
    expect(formatMonthYear("Julio 2026")).toBe("Julio 2026");
    expect(formatMonthYear("  Enero 2025 ")).toBe("Enero 2025");
  });

  it("leaves a missing date empty", () => {
    expect(formatMonthYear(null)).toBe("");
    expect(formatMonthYear(undefined)).toBe("");
    expect(formatMonthYear("")).toBe("");
    expect(formatMonthYear("   ")).toBe("");
  });
});

describe("formatPeriod", () => {
  it("joins the two dates with a hyphen", () => {
    expect(formatPeriod("2025-01-01", "2026-01-01", false, "Presente")).toBe(
      "Enero 2025 - Enero 2026"
    );
  });

  it("ends an ongoing period with the label it was given", () => {
    expect(formatPeriod("2026-07-01", null, true, "Presente")).toBe(
      "Julio 2026 - Presente"
    );
    expect(formatPeriod("2025-03-01", null, true, "Actualidad")).toBe(
      "Marzo 2025 - Actualidad"
    );
  });

  it("shows just the date it has when the other is missing", () => {
    expect(formatPeriod("2026-07-01", null, false, "Presente")).toBe("Julio 2026");
    expect(formatPeriod(null, "2026-05-01", false, "Presente")).toBe("Mayo 2026");
    expect(formatPeriod(null, null, false, "Presente")).toBe("");
  });
});

describe("splitSentences", () => {
  it("turns a paragraph into one bullet per sentence", () => {
    expect(
      splitSentences(
        "Administración diaria del CRM. Análisis de incidencias técnicas. Reportes en Excel."
      )
    ).toEqual([
      "Administración diaria del CRM.",
      "Análisis de incidencias técnicas.",
      "Reportes en Excel."
    ]);
  });

  it("respects the lines it already has and drops their bullet marks", () => {
    expect(splitSentences("• Primer logro\n- Segundo logro\n\n  Tercero")).toEqual([
      "Primer logro",
      "Segundo logro",
      "Tercero"
    ]);
  });

  it("does not cut after an abbreviation", () => {
    expect(splitSentences("Desarrollador Jr. Backend en una pyme. Soporte a clientes.")).toEqual(
      ["Desarrollador Jr. Backend en una pyme.", "Soporte a clientes."]
    );
  });

  it("does not cut a figure or a lowercase continuation", () => {
    expect(splitSentences("Redujo el tiempo un 70% (+200 registros/mes), sin errores.")).toEqual(
      ["Redujo el tiempo un 70% (+200 registros/mes), sin errores."]
    );
    expect(splitSentences("Versión 2.0 estable en producción.")).toEqual([
      "Versión 2.0 estable en producción."
    ]);
  });

  it("returns nothing for an empty text", () => {
    expect(splitSentences("")).toEqual([]);
    expect(splitSentences("  \n  ")).toEqual([]);
  });
});

describe("experienceBullets", () => {
  it("lists the description sentences and then each achievement", () => {
    expect(
      experienceBullets({
        description: "Operó la mesa de ayuda. Documentó procesos.",
        achievements: ["Bajó la cola de tickets un 30%", " "]
      })
    ).toEqual([
      "Operó la mesa de ayuda.",
      "Documentó procesos.",
      "Bajó la cola de tickets un 30%"
    ]);
  });

  it("copes with a missing description", () => {
    expect(experienceBullets({ description: null, achievements: [] })).toEqual([]);
  });
});

describe("skillCells", () => {
  it("gives each skill its own cell and puts the languages in the last one", () => {
    expect(
      skillCells(
        ["Python", "SQL"],
        [
          { name: "Español", level: "Nativo" },
          { name: "Inglés", level: "B2" }
        ]
      )
    ).toEqual(["Python", "SQL", "Español Nativo / Inglés B2"]);
  });

  it("writes a language without a level as just its name", () => {
    expect(skillCells([], [{ name: "Inglés", level: null }])).toEqual(["Inglés"]);
  });

  it("drops blanks and repeats nothing when there is nothing to show", () => {
    expect(skillCells([" ", ""], [])).toEqual([]);
  });

  it("groups the skills with a slash when there are more than the grid holds", () => {
    const skills = Array.from({ length: 24 }, (_, index) => `Skill ${index + 1}`);

    const cells = skillCells(skills, [{ name: "Inglés", level: "B2" }]);

    // 24 habilidades en 11 lugares (uno es de los idiomas): de a tres, 8 celdas más la última.
    expect(cells).toHaveLength(9);
    expect(cells.length).toBeLessThanOrEqual(MAX_SKILL_CELLS);
    expect(cells[0]).toBe("Skill 1 / Skill 2 / Skill 3");
    expect(cells.at(-1)).toBe("Inglés B2");
    expect(cells.join(" / ")).toContain("Skill 24");
  });
});
