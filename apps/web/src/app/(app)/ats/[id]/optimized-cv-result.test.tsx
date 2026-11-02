import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  declaredKeywordsOf,
  OptimizedCVResult,
  type ATSOptimizeResponse
} from "@/src/app/(app)/ats/[id]/optimized-cv-result";

const section = {
  section_name: "skills",
  original_excerpt: "Python, SQL, Looker Studio",
  rewritten_text: "Python, SQL, Power BI y Kubernetes",
  added_keywords: ["Power BI"],
  rationale: "Cubre keywords del puesto."
};

describe("OptimizedCVResult", () => {
  it("shows the verified score before and after the rewrite", () => {
    const optimized: ATSOptimizeResponse = {
      job_id: "job-1",
      sections: [section],
      ats_score_before: 38,
      ats_score_after: 50
    };

    const html = renderToStaticMarkup(<OptimizedCVResult optimized={optimized} />);

    expect(html).toContain("38");
    expect(html).toContain("50");
    expect(html).toContain("Solo cuenta lo que tu CV respalda.");
  });

  it("warns about keywords the CV does not back", () => {
    const optimized: ATSOptimizeResponse = {
      job_id: "job-1",
      sections: [{ ...section, unverified_keywords: ["Kubernetes"] }]
    };

    const html = renderToStaticMarkup(<OptimizedCVResult optimized={optimized} />);

    expect(html).toContain("Sin respaldo en tu CV:");
    expect(html).toContain("Kubernetes");
  });

  it("explains why the score does not move when it stays the same", () => {
    const same: ATSOptimizeResponse = {
      job_id: "job-1",
      sections: [section],
      ats_score_before: 0,
      ats_score_after: 0
    };
    const better: ATSOptimizeResponse = { ...same, ats_score_after: 12 };

    expect(renderToStaticMarkup(<OptimizedCVResult optimized={same} />)).toContain(
      "No cambia: las palabras que faltan no figuran en tu CV"
    );
    expect(renderToStaticMarkup(<OptimizedCVResult optimized={better} />)).not.toContain(
      "No cambia"
    );
  });

  it("shows two sections with the same name without merging them", () => {
    const optimized: ATSOptimizeResponse = {
      job_id: "job-1",
      sections: [
        { ...section, section_name: "experiences", rewritten_text: "Texto A nuevo" },
        { ...section, section_name: "experiences", rewritten_text: "Texto B nuevo" }
      ]
    };

    const html = renderToStaticMarkup(<OptimizedCVResult optimized={optimized} />);

    expect(html).toContain("Texto A nuevo");
    expect(html).toContain("Texto B nuevo");
  });

  it("tells which keywords the CV already says in other words", () => {
    const optimized: ATSOptimizeResponse = {
      job_id: "job-1",
      sections: [{ ...section, backed_keywords: ["Testing", "Observability"] }]
    };

    const html = renderToStaticMarkup(<OptimizedCVResult optimized={optimized} />);

    expect(html).toContain("Tu CV ya lo dice con otras palabras");
    expect(html).toContain("Testing, Observability");
  });

  it("shows the keywords the person declared apart from the ones the CV backs", () => {
    const optimized: ATSOptimizeResponse = {
      job_id: "job-1",
      sections: [
        { ...section, declared_keywords: ["CI/CD", "Django"] },
        { ...section, declared_keywords: ["Django"] }
      ],
      ats_score_before: 39,
      ats_score_after: 62
    };

    const html = renderToStaticMarkup(<OptimizedCVResult optimized={optimized} />);

    expect(html).toContain("Incluye 2 palabras que declaraste saber: CI/CD, Django.");
    expect(html).toContain("las contamos porque lo confirmaste");
    expect(html).toContain("Escritas porque dijiste que las sabés");
    expect(declaredKeywordsOf(optimized)).toEqual(["CI/CD", "Django"]);
  });

  it("says one word in the singular", () => {
    const optimized: ATSOptimizeResponse = {
      job_id: "job-1",
      sections: [{ ...section, declared_keywords: ["CI/CD"] }],
      ats_score_before: 39,
      ats_score_after: 45
    };

    expect(renderToStaticMarkup(<OptimizedCVResult optimized={optimized} />)).toContain(
      "Incluye una palabra que declaraste saber: CI/CD."
    );
  });

  it("does not mention declared keywords when there are none", () => {
    const optimized: ATSOptimizeResponse = {
      job_id: "job-1",
      sections: [section],
      ats_score_before: 39,
      ats_score_after: 45
    };

    const html = renderToStaticMarkup(<OptimizedCVResult optimized={optimized} />);

    expect(html).not.toContain("declaraste");
    expect(declaredKeywordsOf(optimized)).toEqual([]);
  });

  it("points to the confirmation when the score stays the same", () => {
    const optimized: ATSOptimizeResponse = {
      job_id: "job-1",
      sections: [section],
      ats_score_before: 39,
      ats_score_after: 39
    };

    const html = renderToStaticMarkup(<OptimizedCVResult optimized={optimized} />);

    expect(html).toContain("ni en tu LinkedIn");
    expect(html).toContain("Qué falta para que el puntaje suba");
  });

  it("keeps working with answers from before the verification", () => {
    const optimized: ATSOptimizeResponse = { job_id: "job-1", sections: [section] };

    const html = renderToStaticMarkup(<OptimizedCVResult optimized={optimized} />);

    expect(html).not.toContain("Sin respaldo en tu CV:");
    expect(html).not.toContain("Puntaje ATS con las secciones nuevas");
  });
});
