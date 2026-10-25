import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
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

const full: PrintableCV = {
  ...cv,
  summary: "Resumen de ejemplo.",
  experiences: [
    {
      ...cv.experiences[0],
      achievements: ["Armé tableros de ventas."]
    }
  ],
  educations: [
    {
      institution: "Universidad de ejemplo",
      field_of_study: "Administración",
      degree_level: null,
      started_at: "2020-03-01",
      ended_at: null,
      is_ongoing: true
    },
    {
      institution: "Centro de ejemplo",
      field_of_study: "Recursos Humanos",
      degree_level: null,
      started_at: "2021-03-01",
      ended_at: "2021-08-01",
      is_ongoing: false
    }
  ],
  certifications: [{ name: "Certificado de ejemplo", issuer: "Entidad" }]
};

function render(value: PrintableCV) {
  return renderToStaticMarkup(<PrintableCVDocument cv={value} />);
}

function sectionTitles(html: string) {
  return [...html.matchAll(/<h2[^>]*>([^<]+)<\/h2>/g)].map((match) =>
    match[1].trim()
  );
}

describe("PrintableCVDocument", () => {
  it("prints the header with only the contact data it has", () => {
    const html = render(cv);

    expect(html).toContain("Lucía Ferreyra");
    expect(html).toContain("lucia.demo@example.com · Buenos Aires");
    expect(html).toContain("Pasante de datos");
    expect(html).toContain("Distribuidora Andina");
    expect(html).toContain("Mar 2026 – Actualidad");
  });

  it("leaves out the sections that are empty", () => {
    const html = render(cv);

    expect(sectionTitles(html)).toEqual(["Habilidades", "Experiencia", "Idiomas"]);
    expect(html).not.toContain("Educación");
    expect(html).not.toContain("Certificaciones");
    expect(html).toContain("Inglés");
  });

  it("puts the name, the headline and the contact line in the centered header", () => {
    const html = render(cv);

    expect(html.indexOf("Lucía Ferreyra")).toBeLessThan(html.indexOf("Analista de datos"));
    expect(html.indexOf("Analista de datos")).toBeLessThan(
      html.indexOf("lucia.demo@example.com")
    );
    expect(html).toMatch(/<header class="[^"]*\btext-center\b/);
  });

  it("spaces the name a little, not letter by letter", () => {
    // Con mucho espaciado el ATS lee «L U C Í A» y no encuentra el nombre.
    const h1 = render(cv).match(/<h1 class="([^"]*)"/);
    const tracking = h1?.[1].match(/tracking-\[([\d.]+)em\]/);

    expect(tracking).not.toBeNull();
    expect(Number(tracking?.[1])).toBeGreaterThan(0);
    expect(Number(tracking?.[1])).toBeLessThanOrEqual(0.1);
  });

  it("prints the summary under the header without a title of its own", () => {
    const html = render(full);

    expect(html).toContain("Resumen de ejemplo.");
    expect(html).not.toMatch(/>\s*(Perfil|Resumen)\s*</);
    expect(html.indexOf("Resumen de ejemplo.")).toBeLessThan(html.indexOf("Habilidades"));
  });

  it("puts the skills in a single centered paragraph", () => {
    const html = render(full);

    expect(html).toMatch(/<p class="[^"]*\btext-center\b[^"]*">Python · SQL<\/p>/);
  });

  it("puts each job's period on the right of the company and the role below", () => {
    const html = render(full);

    expect(html).toMatch(
      /Distribuidora Andina<\/p><p[^>]*>Mar 2026 – Actualidad<\/p>/
    );
    expect(html.indexOf("Distribuidora Andina")).toBeLessThan(
      html.indexOf("Pasante de datos")
    );
    expect(html).toContain("Armé tableros de ventas.");
  });

  it("prints the dates of each education next to its title", () => {
    const html = render(full);

    expect(html).toMatch(/Administración<\/p><p[^>]*>Mar 2020 – Actualidad<\/p>/);
    expect(html).toMatch(/Recursos Humanos<\/p><p[^>]*>Mar 2021 – Ago 2021<\/p>/);
    expect(html.indexOf("Administración")).toBeLessThan(
      html.indexOf("Universidad de ejemplo")
    );
  });

  it("does not invent a period for an education without dates", () => {
    const html = render({
      ...full,
      experiences: [],
      educations: [
        {
          institution: "Escuela de ejemplo",
          field_of_study: "Programación",
          degree_level: null,
          started_at: null,
          ended_at: null,
          is_ongoing: false
        }
      ]
    });

    expect(html).toContain("Programación");
    expect(html).toContain("Escuela de ejemplo");
    expect(html).not.toContain("Actualidad<");
  });
});

describe("PrintableCVDocument format", () => {
  // `ats_analyzer/format_checker.py` (`penalty_after_download`) da por hecho que este
  // documento no tiene tablas, columnas ni imágenes: si alguna prueba de acá falla, esa
  // lista y el «después» del optimizador dejaron de ser ciertos.
  it("is a single flow of text without images, tables or columns", () => {
    const html = render(full);

    expect(html).not.toMatch(/<(img|svg|picture|canvas|table|iframe)\b/);
    expect(html).not.toMatch(/\b(columns-\d|grid|float-|flex-row|basis-)/);
    expect(html).not.toContain("background-image");
  });

  it("uses only the section titles the ATS check recognizes", () => {
    const source = readFileSync(
      fileURLToPath(
        new URL(
          "../../../../services/api/app/services/ats_analyzer/format_checker.py",
          import.meta.url
        )
      ),
      "utf8"
    );
    const standard = new Set(
      [...(source.match(/STANDARD_HEADERS = \{([^}]*)\}/)?.[1] ?? "").matchAll(/"(\w+)"/g)].map(
        (match) => match[1]
      )
    );
    const plain = (title: string) =>
      title
        .normalize("NFKD")
        .replace(/[̀-ͯ]/g, "")
        .toLowerCase();

    const titles = sectionTitles(render(full));

    expect(standard.size).toBeGreaterThan(0);
    expect(titles.length).toBeGreaterThan(0);
    for (const title of titles) {
      expect(standard.has(plain(title)), title).toBe(true);
    }
  });

  it("orders the sections like the reference designs", () => {
    expect(sectionTitles(render(full))).toEqual([
      "Habilidades",
      "Experiencia",
      "Educación",
      "Idiomas",
      "Certificaciones"
    ]);
  });

  it("keeps an entry together instead of splitting it across pages", () => {
    expect(render(full)).toContain("break-inside-avoid");
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
