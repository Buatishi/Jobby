import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({ apiClient: vi.fn() }));

import { apiClient } from "@/lib/api/client";
import { fetchAndRemember, forgetApiResources } from "@/lib/api/use-api-resource";
import { I18nProvider } from "@/lib/i18n/provider";
import { AtsJobList } from "@/src/app/(app)/ats/ats-job-list";

function render() {
  return renderToStaticMarkup(
    <I18nProvider>
      <AtsJobList />
    </I18nProvider>
  );
}

beforeEach(() => {
  forgetApiResources();
  vi.mocked(apiClient).mockReset();
});

describe("AtsJobList", () => {
  it("waits for the API without claiming there are no jobs", () => {
    const html = render();

    expect(html).toContain("Cargando jobs...");
    expect(html).not.toContain("Primero analizá un puesto");
  });

  it("lists each analyzed job with a link to its ATS report", async () => {
    vi.mocked(apiClient).mockResolvedValueOnce([
      { id: "job-1", job_title: "Backend Engineer", company_name: "Acme" },
      { id: "job-2", job_title: null, company_name: null }
    ]);
    await fetchAndRemember("/api/v1/jobs");

    const html = render();

    expect(html).toContain("Backend Engineer");
    expect(html).toContain("Acme");
    expect(html).toContain('href="/ats/job-1"');
    expect(html).toContain('href="/ats/job-2"');
    expect(html.match(/Ver reporte ATS/g)).toHaveLength(2);
    expect(html).toContain("Rol sin título");
    expect(html).toContain("Empresa sin nombre");
    expect(html).not.toContain("Primero analizá un puesto");
  });

  it("shows the empty state only when the account has no jobs", async () => {
    vi.mocked(apiClient).mockResolvedValueOnce([]);
    await fetchAndRemember("/api/v1/jobs");

    const html = render();

    expect(html).toContain("Primero analizá un puesto");
    expect(html).toContain('href="/dashboard"');
    expect(html).not.toContain("Ver reporte ATS");
  });
});
