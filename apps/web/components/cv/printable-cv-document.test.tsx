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
