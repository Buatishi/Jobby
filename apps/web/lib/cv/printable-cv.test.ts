import { describe, expect, it } from "vitest";

import {
  applyOptimizedSections,
  splitSkills,
  type PrintableCV
} from "@/lib/cv/printable-cv";

const cv: PrintableCV = {
  contact: {
    full_name: "Lucía Ferreyra",
    email: "lucia.demo@example.com",
    phone: "",
    location: "Buenos Aires",
    linkedin_url: ""
  },
  headline: "Analista de datos",
  summary: "Técnica en programación con foco en datos.",
  skills: ["Python", "SQL"],
  experiences: [
    {
      company: "Distribuidora Andina",
      title: "Pasante de datos",
      started_at: "2026-03-01",
      ended_at: "2026-08-01",
      is_current: false,
      description: "Tableros en Looker Studio\ncon ventas por zona.",
      achievements: ["Limpieza de planillas con pandas."]
    }
  ],
  educations: [],
  languages: [],
  certifications: []
};

describe("applyOptimizedSections", () => {
  it("replaces the excerpt inside an experience even across line breaks", () => {
    const { cv: result, unplaced } = applyOptimizedSections(cv, [
      {
        section_name: "experiences",
        original_excerpt: "Tableros en Looker Studio con ventas por zona.",
        rewritten_text: "Tableros en Looker Studio (similar a Power BI) con ventas por zona."
      }
    ]);

    expect(result.experiences[0].description).toBe(
      "Tableros en Looker Studio (similar a Power BI) con ventas por zona."
    );
    expect(unplaced).toEqual([]);
  });

  it("replaces an achievement when the excerpt is there", () => {
    const { cv: result } = applyOptimizedSections(cv, [
      {
        section_name: "experiences",
        original_excerpt: "Limpieza de planillas con pandas.",
        rewritten_text: "Limpieza de planillas de 4 sucursales con Python (pandas)."
      }
    ]);

    expect(result.experiences[0].achievements).toEqual([
      "Limpieza de planillas de 4 sucursales con Python (pandas)."
    ]);
  });

  it("swaps the whole summary and skills when the excerpt is not literal", () => {
    const { cv: result, unplaced } = applyOptimizedSections(cv, [
      {
        section_name: "summary",
        original_excerpt: "texto que no está",
        rewritten_text: "Analista de datos junior con SQL y Python."
      },
      {
        section_name: "skills",
        original_excerpt: "Python, SQL",
        rewritten_text: "Python; SQL; Power BI"
      }
    ]);

    expect(result.summary).toBe("Analista de datos junior con SQL y Python.");
    expect(result.skills).toEqual(["Python", "SQL", "Power BI"]);
    expect(unplaced).toEqual([]);
  });

  it("never overwrites an experience it cannot find", () => {
    const section = {
      section_name: "experiences",
      original_excerpt: "Un trabajo que no está en el CV",
      rewritten_text: "Texto nuevo"
    };

    const { cv: result, unplaced } = applyOptimizedSections(cv, [section]);

    expect(result.experiences).toEqual(cv.experiences);
    expect(unplaced).toEqual([section]);
  });

  it("does not change the CV it receives", () => {
    applyOptimizedSections(cv, [
      { section_name: "summary", original_excerpt: "x", rewritten_text: "Otro resumen" }
    ]);

    expect(cv.summary).toBe("Técnica en programación con foco en datos.");
  });
});

describe("splitSkills", () => {
  it("splits on the usual separators and drops empty items", () => {
    expect(splitSkills("Python, SQL;\nPower BI • Excel.")).toEqual([
      "Python",
      "SQL",
      "Power BI",
      "Excel"
    ]);
  });
});
