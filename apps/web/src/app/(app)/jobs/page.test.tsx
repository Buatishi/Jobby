import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({ apiClient: vi.fn() }));

import { apiClient } from "@/lib/api/client";
import { fetchAndRemember, forgetApiResources } from "@/lib/api/use-api-resource";
import JobsPage from "@/src/app/(app)/jobs/page";

beforeEach(() => {
  forgetApiResources();
});

describe("JobsPage", () => {
  it("waits for the API on the first visit", () => {
    const html = renderToStaticMarkup(<JobsPage />);

    expect(html).toContain("Cargando jobs...");
  });

  it("shows the last list at once when coming back to the section", async () => {
    vi.mocked(apiClient).mockResolvedValueOnce([
      { id: "job-1", job_title: "Backend Engineer", company_name: "Acme" }
    ]);
    await fetchAndRemember("/api/v1/jobs");

    const html = renderToStaticMarkup(<JobsPage />);

    expect(html).toContain("Backend Engineer");
    expect(html).not.toContain("Cargando jobs...");
  });
});
