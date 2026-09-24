import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({ apiClient: vi.fn() }));

import { JobCard } from "@/src/app/(app)/jobs/job-card";

function render(job: Parameters<typeof JobCard>[0]["job"]) {
  return renderToStaticMarkup(
    <JobCard job={job} onDeleted={() => undefined} onUpdated={() => undefined} />
  );
}

describe("JobCard", () => {
  it("shows the job with its report link and the edit and delete actions", () => {
    const html = render({
      id: "job-1",
      job_title: "Backend Engineer",
      company_name: "Acme",
      required_seniority: "senior",
      required_modality: "hybrid",
      salary_min: 1000,
      salary_max: 2000,
      currency: "USD"
    });

    expect(html).toContain("Backend Engineer");
    expect(html).toContain("Acme");
    expect(html).toContain("senior · Híbrido · 1.000 a 2.000 USD");
    expect(html).toContain('href="/jobs/job-1"');
    expect(html).toContain('aria-label="Editar Backend Engineer"');
    expect(html).toContain('aria-label="Eliminar Backend Engineer"');
  });

  it("names a job without title in its actions", () => {
    const html = render({ id: "job-2" });

    expect(html).toContain("Puesto sin título");
    expect(html).toContain("Empresa no detectada");
    expect(html).toContain('aria-label="Editar Puesto sin título"');
  });

  it("starts in the list view, without the form or the confirmation", () => {
    const html = render({ id: "job-3", job_title: "QA" });

    expect(html).not.toContain("<form");
    expect(html).not.toContain("No se puede deshacer");
  });
});
