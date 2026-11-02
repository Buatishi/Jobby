import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type {
  RealityGapDocument,
  RealityGapReport,
  RealityGapSkill
} from "@/lib/reality-gap/types";

type Resource = {
  data: RealityGapReport | undefined;
  error: string | null;
  loading: boolean;
};

const resource = vi.hoisted(() => ({
  current: { data: undefined, error: null, loading: false } as Resource
}));

vi.mock("@/lib/api/use-api-resource", () => ({
  useApiResource: () => resource.current
}));

import RealityGapPage from "@/src/app/(app)/reality-gap/page";

const document = (
  overrides: Partial<RealityGapDocument> = {}
): RealityGapDocument => ({
  filename: "cv.pdf",
  uploaded_at: "2026-11-02T14:55:20+00:00",
  status: "done",
  skills_source: "document",
  ...overrides
});

const skill = (overrides: Partial<RealityGapSkill>): RealityGapSkill => ({
  skill_id: "skill-1",
  name: "Python",
  category: "technical",
  in_cv: true,
  in_linkedin: true,
  saved: true,
  confirmed: true,
  rejected: false,
  coherence_score: 100,
  recommendation: null,
  ...overrides
});

const report = (overrides: Partial<RealityGapReport> = {}): RealityGapReport => ({
  profile_id: "profile-1",
  skills: [],
  summary: {
    comparable: true,
    total: 0,
    in_both: 0,
    only_cv: 0,
    only_linkedin: 0,
    in_neither: 0,
    score: null
  },
  cv: document(),
  linkedin: document({ filename: "Profile.pdf" }),
  ...overrides
});

function render(next: Partial<Resource>): string {
  resource.current = { data: undefined, error: null, loading: false, ...next };
  return renderToStaticMarkup(<RealityGapPage />);
}

describe("RealityGapPage", () => {
  it("shows the overall score, the counts and every skill when both documents are read", () => {
    const html = render({
      data: report({
        skills: [
          skill({
            skill_id: "docker",
            name: "Docker",
            in_linkedin: false,
            confirmed: false,
            coherence_score: 60,
            recommendation: "Agregá Docker a LinkedIn."
          }),
          skill({ skill_id: "python", name: "Python" })
        ],
        summary: {
          comparable: true,
          total: 2,
          in_both: 1,
          only_cv: 1,
          only_linkedin: 0,
          in_neither: 0,
          score: 80
        }
      })
    });

    expect(html).toContain("Coherencia general");
    expect(html).toContain("2 skills comparadas");
    expect(html).toContain("Solo en el CV");
    expect(html).toContain("Docker");
    expect(html).toContain("Agregá Docker a LinkedIn.");
    expect(html).toContain("Perfil sin confirmar");
    expect(html).toContain("Perfil activa");
    expect(html).toContain("«cv.pdf»");
    expect(html).toContain("«Profile.pdf»");
    // Los grupos con algo adentro, con su cantidad.
    expect(html).toContain("En los dos (1)");
    expect(html).toContain("Solo en el CV (1)");
    expect(html).not.toContain("Solo en LinkedIn (");
  });

  it("explains what is missing instead of scoring when there is no LinkedIn PDF", () => {
    const html = render({
      data: report({
        linkedin: null,
        skills: [
          skill({
            in_linkedin: null,
            coherence_score: null,
            recommendation: null
          })
        ],
        summary: {
          comparable: false,
          total: 1,
          in_both: 0,
          only_cv: 0,
          only_linkedin: 0,
          in_neither: 0,
          score: null
        }
      })
    });

    expect(html).toContain("sin él no podemos comparar");
    expect(html).toContain('href="/profile"');
    expect(html).toContain("Subir PDF de LinkedIn");
    expect(html).toContain("LinkedIn —");
    expect(html).not.toContain("Coherencia general");
    expect(html).not.toContain("Las de menor score aparecen primero");
  });

  it("marks a skill that only LinkedIn names as not saved and says what to do", () => {
    const html = render({
      data: report({
        skills: [
          skill({
            skill_id: null,
            name: "Gestión de Software",
            category: null,
            in_cv: false,
            saved: false,
            confirmed: false,
            coherence_score: 60,
            recommendation:
              "Agregá Gestión de Software al CV para alinear tus canales."
          })
        ],
        summary: {
          comparable: true,
          total: 1,
          in_both: 0,
          only_cv: 0,
          only_linkedin: 1,
          in_neither: 0,
          score: 60
        }
      })
    });

    expect(html).toContain("Perfil no guardada");
    expect(html).toContain("CV ✗");
    expect(html).toContain("LinkedIn ✓");
    expect(html).toContain("Agregá Gestión de Software al CV");
    expect(html).toContain("Solo en LinkedIn (1)");
  });

  it("warns about a CV read before it kept its own list of skills", () => {
    const html = render({
      data: report({ cv: document({ skills_source: "saved" }) })
    });

    expect(html).toContain("Tu CV se leyó antes de esta mejora");
    expect(html).toContain("Subir CV");
  });

  it("says it is loading and not that there is nothing to compare", () => {
    const html = render({ loading: true });

    expect(html).toContain("Cargando…");
    expect(html).not.toContain("Todavía no hay skills para comparar");
  });

  it("says there is nothing to compare when the profile has no skills", () => {
    const html = render({ data: report() });

    expect(html).toContain("Todavía no hay skills para comparar");
    expect(html).not.toContain("Cargando…");
  });

  it("shows the error alone when there is nothing to show yet", () => {
    const html = render({ error: "No se pudo cargar Reality Gap." });

    expect(html).toContain("No se pudo cargar Reality Gap.");
    expect(html).not.toContain("Skills por coherencia");
  });

  it("keeps the last report on screen next to the error when a refresh fails", () => {
    const html = render({
      data: report({ skills: [skill({ name: "Python" })] }),
      error: "No se pudo cargar Reality Gap."
    });

    expect(html).toContain("No se pudo cargar Reality Gap.");
    expect(html).toContain("Python");
  });
});
