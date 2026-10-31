import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({ apiClient: vi.fn() }));

import { defaultIncluded, DownloadCVPanel } from "@/components/cv/download-cv-panel";
import { PrintableCVDocument } from "@/components/cv/printable-cv-document";
import type { PrintableCV } from "@/lib/cv/printable-cv";

const cv: PrintableCV = {
  contact: {
    full_name: "Lucía Ferreyra",
    email: "lucia.demo@example.com",
    phone: "+54 9 11 5555-0000",
    location: "Buenos Aires",
    linkedin_url: ""
  },
  headline: "Analista de datos",
  summary: null,
  skills: ["Python", "SQL"],
  experiences: [
    {
      company: "Distribuidora Andina",
      title: "Pasante de datos",
      started_at: "2026-03-01",
      ended_at: null,
      is_current: true,
      description: null,
      achievements: []
    }
  ],
  educations: [],
  languages: [{ name: "Inglés", level: null }],
  certifications: []
};

const fullCv: PrintableCV = {
  ...cv,
  summary: "Analista con base en datos. Busca su primer rol.",
  experiences: [
    {
      company: "Distribuidora Andina",
      title: "Pasante de datos",
      started_at: "2026-03-01",
      ended_at: null,
      is_current: true,
      description: "Armó tableros de ventas. Automatizó pedidos.",
      achievements: ["Ahorró 20 horas por semana"]
    },
    {
      company: "Tienda Demo",
      title: "Operadora digital",
      started_at: "2025-01-01",
      ended_at: "2025-12-01",
      is_current: false,
      description: null,
      achievements: []
    }
  ],
  educations: [
    {
      institution: "Universidad Demo",
      field_of_study: "Ingeniería en Sistemas",
      degree_level: null,
      started_at: "2025-03-01",
      ended_at: null,
      is_ongoing: true
    }
  ],
  languages: [
    { name: "Español", level: "Nativo" },
    { name: "Inglés", level: "B2" }
  ],
  certifications: [
    { name: "Excel para análisis de datos", issuer: "Plataforma Demo", issued_at: "2025-02-01" }
  ]
};

describe("PrintableCVDocument", () => {
  it("centers the name and prints only the contact data it has", () => {
    const html = renderToStaticMarkup(<PrintableCVDocument cv={cv} />);

    expect(html).toContain("text-center");
    expect(html).toContain("Lucía Ferreyra");
    expect(html).toContain("+54 9 11 5555-0000");
    expect(html).toContain("lucia.demo@example.com");
    expect(html).toContain("Buenos Aires");
    expect(html).not.toContain("linkedin");
  });

  it("follows the model: headline and summary, skills, experience, education", () => {
    const html = renderToStaticMarkup(<PrintableCVDocument cv={fullCv} />);

    const order = [
      "Analista de datos",
      "Analista con base en datos.",
      "HABILIDADES Y COMPETENCIAS",
      "EXPERIENCIA PROFESIONAL",
      "EDUCACIÓN"
    ].map((text) => html.indexOf(text));

    expect(order.every((position) => position >= 0)).toBe(true);
    expect([...order].sort((a, b) => a - b)).toEqual(order);
  });

  it("writes each experience with the company, the role and the dates on the right", () => {
    const html = renderToStaticMarkup(<PrintableCVDocument cv={fullCv} />);

    expect(html).toContain("Distribuidora Andina");
    expect(html).toContain("Pasante de datos");
    expect(html).toContain("Marzo 2026 - Presente");
    expect(html).toContain("Enero 2025 - Diciembre 2025");
    expect(html).toContain("justify-between");
    // Cada oración y cada logro es una viñeta.
    expect(html).toContain("Armó tableros de ventas.");
    expect(html).toContain("Automatizó pedidos.");
    expect(html).toContain("Ahorró 20 horas por semana");
  });

  it("puts the languages in the skills grid, as the model does", () => {
    const html = renderToStaticMarkup(<PrintableCVDocument cv={fullCv} />);

    expect(html).toContain("grid-cols-3");
    expect(html).toContain("Español Nativo / Inglés B2");
    expect(html).not.toContain("IDIOMAS");
  });

  it("lists the certificates under education with their date", () => {
    const html = renderToStaticMarkup(<PrintableCVDocument cv={fullCv} />);

    expect(html).toContain("Ingeniería en Sistemas");
    expect(html).toContain("Universidad Demo");
    expect(html).toContain("Marzo 2025 - Actualidad");
    expect(html).toContain("Excel para análisis de datos");
    expect(html).toContain("Plataforma Demo");
    expect(html).toContain("Febrero 2025");
  });

  it("prints a date the CV reader kept as free text, as it was written", () => {
    const html = renderToStaticMarkup(
      <PrintableCVDocument
        cv={{
          ...cv,
          experiences: [
            { ...cv.experiences[0], started_at: "Julio 2026", is_current: false }
          ]
        }}
      />
    );

    expect(html).toContain("Julio 2026");
    expect(html).not.toContain("Julio 2026 -");
  });

  it("prints without a page background, which a PDF reader would take for a table", () => {
    const html = renderToStaticMarkup(<PrintableCVDocument cv={cv} />);

    expect(html).toContain("print:bg-transparent");
  });

  it("uses the model's typeface", () => {
    const html = renderToStaticMarkup(<PrintableCVDocument cv={cv} />);

    expect(html).toContain("Arial, Helvetica, sans-serif");
  });

  it("leaves out the sections that are empty", () => {
    const html = renderToStaticMarkup(<PrintableCVDocument cv={cv} />);

    expect(html).not.toContain("EDUCACIÓN");
    expect(html).not.toContain("Perfil</h2>");
    expect(html).not.toContain("Analista con base");
    expect(html).toContain("HABILIDADES Y COMPETENCIAS");
    expect(html).toContain("Inglés");
  });

  it("copes with a CV that has no dates at all", () => {
    const html = renderToStaticMarkup(
      <PrintableCVDocument
        cv={{
          ...fullCv,
          experiences: [
            { ...fullCv.experiences[0], started_at: null, ended_at: null, is_current: false }
          ],
          educations: [
            { institution: "Universidad Demo", field_of_study: "Sistemas", degree_level: null }
          ],
          certifications: []
        }}
      />
    );

    expect(html).toContain("Pasante de datos");
    expect(html).toContain("Sistemas");
    expect(html).not.toContain("Presente");
    expect(html).not.toContain("Actualidad");
  });
});

describe("DownloadCVPanel", () => {
  it("starts with a single download button", () => {
    const html = renderToStaticMarkup(<DownloadCVPanel />);

    expect(html).toContain("Descargar CV en PDF");
  });

  it("includes by default only the sections the CV backs", () => {
    expect(
      defaultIncluded([
        { section_name: "skills", original_excerpt: "", rewritten_text: "" },
        {
          section_name: "experiences",
          original_excerpt: "",
          rewritten_text: "",
          unverified_keywords: ["Kubernetes"]
        }
      ])
    ).toEqual([true, false]);
  });
});
