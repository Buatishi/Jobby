import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "@/lib/i18n/provider";
import { AtsReportLink } from "@/src/app/(app)/jobs/[id]/ats-report-link";

describe("AtsReportLink", () => {
  it("opens the ATS report of the given job", () => {
    const html = renderToStaticMarkup(
      <I18nProvider>
        <AtsReportLink jobId="job-9" />
      </I18nProvider>
    );

    expect(html).toContain('href="/ats/job-9"');
    expect(html).toContain("Ver reporte ATS");
  });
});
