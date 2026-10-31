import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({ apiClient: vi.fn(), apiStream: vi.fn() }));

import { JobReadyActionView } from "@/components/job-ready-action";
import { dictionaries } from "@/lib/i18n/dictionaries";
import { I18nProvider } from "@/lib/i18n/provider";

function render(ready: boolean) {
  return renderToStaticMarkup(
    <I18nProvider>
      <JobReadyActionView jobId="job-9" ready={ready} />
    </I18nProvider>
  );
}

describe("JobReadyActionView", () => {
  it("opens the analyzed job once its match exists", () => {
    const html = render(true);

    expect(html).toContain('href="/jobs/job-9"');
    expect(html).toContain("Ver job");
  });

  it("does not offer a link that would land on «Match no encontrado»", () => {
    const html = render(false);

    expect(html).not.toContain("href=");
    expect(html).toContain("Calculando tu match");
    expect(html).toContain("disabled");
  });

  it("says the same in English", () => {
    const es = dictionaries.es.app as Record<string, string>;
    const en = dictionaries.en.app as Record<string, string>;

    expect(es.viewJob).toBe("Ver job");
    expect(en.viewJob).toBe("View job");
    expect(en.matchPreparing).toMatch(/Calculating your match/);
    expect(es.matchPreparing).toMatch(/Calculando tu match/);
  });
});
