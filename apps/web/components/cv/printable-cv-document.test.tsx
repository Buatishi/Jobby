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
    phone: "",
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

describe("PrintableCVDocument", () => {
  it("prints the header with only the contact data it has", () => {
    const html = renderToStaticMarkup(<PrintableCVDocument cv={cv} />);

    expect(html).toContain("Lucía Ferreyra");
    expect(html).toContain("lucia.demo@example.com · Buenos Aires");
    expect(html).toContain("Pasante de datos — Distribuidora Andina");
    expect(html).toContain("2026-03 – actualidad");
  });

  it("leaves out the sections that are empty", () => {
    const html = renderToStaticMarkup(<PrintableCVDocument cv={cv} />);

    expect(html).not.toContain("Perfil</h2>");
    expect(html).not.toContain("Educación");
    expect(html).not.toContain("Certificaciones");
    expect(html).toContain("Inglés");
  });
});

describe("PrintableCVDocument format", () => {
  // `ats_analyzer/format_checker.py` (`penalty_after_download`) da por hecho que este
  // documento no tiene tablas, columnas ni imágenes: si alguna prueba de acá falla, esa
  // lista y el «después» del optimizador dejaron de ser ciertos.
  const full: PrintableCV = {
    ...cv,
    summary: "Resumen de ejemplo.",
    educations: [
      {
        institution: "Instituto de ejemplo",
        field_of_study: "Datos",
        degree_level: "tecnicatura"
      }
    ],
    certifications: [{ name: "Certificado de ejemplo", issuer: "Entidad" }]
  };

  it("is a single flow of text without images, tables or columns", () => {
    const html = renderToStaticMarkup(<PrintableCVDocument cv={full} />);

    expect(html).not.toMatch(/<(img|svg|picture|canvas|table|iframe)\b/);
    expect(html).not.toMatch(/\b(columns-\d|grid|float-|flex-row|basis-)/);
    expect(html).not.toContain("background-image");
  });

  it("prints every section with a title the ATS check recognizes", () => {
    const html = renderToStaticMarkup(<PrintableCVDocument cv={full} />);
    const titles = [...html.matchAll(/<h2[^>]*>([^<]+)<\/h2>/g)].map((match) =>
      match[1].trim()
    );

    // «Perfil» no está en `STANDARD_HEADERS` y por eso sigue restando 5 al «después».
    expect(titles).toEqual([
      "Perfil",
      "Experiencia",
      "Educación",
      "Habilidades",
      "Idiomas",
      "Certificaciones"
    ]);
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
