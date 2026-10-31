import { describe, expect, it } from "vitest";

import {
  applyOptimizedSections,
  describeSection,
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

describe("applyOptimizedSections across several bullets", () => {
  const withBullets: PrintableCV = {
    ...cv,
    experiences: [
      {
        company: "PYME",
        title: "Desarrollador Freelance",
        started_at: "2026-03",
        ended_at: "2026-05",
        is_current: false,
        description: null,
        achievements: [
          "Pipeline end-to-end de automatización de facturas",
          "Reduje el tiempo de procesamiento un 70% sobre más de 200 registros",
          "Manejo de errores, logging y casos de prueba documentados"
        ]
      },
      {
        company: "Independiente",
        title: "Analista Digital",
        started_at: "2024-01",
        ended_at: "2024-10",
        is_current: false,
        description: null,
        achievements: ["Venta de productos online"]
      }
    ]
  };

  it("replaces the bullets the excerpt copies, keeping the others in place", () => {
    const { cv: result, unplaced } = applyOptimizedSections(withBullets, [
      {
        section_name: "experiences",
        // Con marcas de viñeta, mayúsculas y signos distintos a los guardados.
        original_excerpt:
          "• Pipeline end-to-end de automatizacion de facturas\n• Reduje el tiempo de procesamiento un 70% sobre mas de 200 registros.",
        rewritten_text:
          "Diseñé un pipeline de automatización de facturas en Python.\nRedujo un 70% el tiempo de procesamiento."
      }
    ]);

    expect(unplaced).toEqual([]);
    expect(result.experiences[0].achievements).toEqual([
      "Diseñé un pipeline de automatización de facturas en Python.",
      "Redujo un 70% el tiempo de procesamiento.",
      "Manejo de errores, logging y casos de prueba documentados"
    ]);
    // La otra experiencia no se toca.
    expect(result.experiences[1]).toEqual(withBullets.experiences[1]);
  });

  it("splits a single rewritten paragraph into one bullet per sentence", () => {
    const { cv: result } = applyOptimizedSections(withBullets, [
      {
        section_name: "experiences",
        original_excerpt:
          "Pipeline end-to-end de automatización de facturas Reduje el tiempo de procesamiento un 70% sobre más de 200 registros",
        rewritten_text: "Automaticé facturas con Python. Reduje el tiempo un 70%."
      }
    ]);

    expect(result.experiences[0].achievements).toEqual([
      "Automaticé facturas con Python.",
      "Reduje el tiempo un 70%.",
      "Manejo de errores, logging y casos de prueba documentados"
    ]);
  });

  it("replaces the description and the bullets when the excerpt covers both", () => {
    const base: PrintableCV = {
      ...withBullets,
      experiences: [
        {
          ...withBullets.experiences[0],
          description: "Proyecto de automatización para una pyme.",
          achievements: ["Pipeline end-to-end de automatización de facturas"]
        }
      ]
    };

    const { cv: result, unplaced } = applyOptimizedSections(base, [
      {
        section_name: "experiences",
        original_excerpt:
          "Proyecto de automatización para una pyme. Pipeline end-to-end de automatización de facturas",
        rewritten_text: "Automaticé la facturación de una pyme con Python."
      }
    ]);

    expect(unplaced).toEqual([]);
    expect(result.experiences[0].description).toBeNull();
    expect(result.experiences[0].achievements).toEqual([
      "Automaticé la facturación de una pyme con Python."
    ]);
  });

  it("leaves a section unplaced when the excerpt is mostly text the CV does not have", () => {
    const section = {
      section_name: "experiences",
      original_excerpt:
        "Pipeline end-to-end de automatización de facturas. Lideré un equipo de diez personas en tres países y coordiné la migración completa a la nube",
      rewritten_text: "Texto nuevo"
    };

    const { cv: result, unplaced } = applyOptimizedSections(withBullets, [section]);

    expect(result.experiences).toEqual(withBullets.experiences);
    expect(unplaced).toEqual([section]);
  });

  it("does not place an excerpt too short to tell which experience it is", () => {
    const section = {
      section_name: "experiences",
      original_excerpt: "Venta online",
      rewritten_text: "Texto nuevo"
    };

    const { cv: result, unplaced } = applyOptimizedSections(withBullets, [section]);

    expect(result.experiences).toEqual(withBullets.experiences);
    expect(unplaced).toEqual([section]);
  });
});

describe("describeSection", () => {
  it("tells apart two sections with the same name by their excerpt", () => {
    const first = describeSection({
      section_name: "experiences",
      original_excerpt: "Pipeline end-to-end de automatización de facturas",
      rewritten_text: "x"
    });
    const second = describeSection({
      section_name: "experiences",
      original_excerpt: "Venta de productos online y análisis de mercado",
      rewritten_text: "x"
    });

    expect(first).toBe("experiences «Pipeline end-to-end de automatización de facturas»");
    expect(second).not.toBe(first);
  });

  it("shortens a long excerpt and falls back to the new text, then to the name", () => {
    const long = describeSection({
      section_name: "experiences",
      original_excerpt: "palabra ".repeat(30),
      rewritten_text: "x"
    });
    const fromRewritten = describeSection({
      section_name: "educations",
      original_excerpt: "",
      rewritten_text: "Técnico informático"
    });
    const bare = describeSection({
      section_name: "certifications",
      original_excerpt: "",
      rewritten_text: ""
    });

    expect(long.endsWith("…»")).toBe(true);
    expect(long.length).toBeLessThan(80);
    expect(fromRewritten).toBe("educations «Técnico informático»");
    expect(bare).toBe("certifications");
  });

  it("keeps summary and skills as they are: there is only one of each", () => {
    expect(
      describeSection({
        section_name: "summary",
        original_excerpt: "texto",
        rewritten_text: "otro"
      })
    ).toBe("summary");
    expect(
      describeSection({ section_name: "skills", original_excerpt: "", rewritten_text: "" })
    ).toBe("skills");
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
