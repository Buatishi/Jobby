import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "@/lib/i18n/provider";
import SectionLoading from "@/src/app/(app)/loading";

describe("SectionLoading", () => {
  it("announces the wait and hides the placeholders from screen readers", () => {
    const html = renderToStaticMarkup(
      <I18nProvider>
        <SectionLoading />
      </I18nProvider>
    );

    expect(html).toContain('aria-busy="true"');
    expect(html).toContain('role="status"');
    expect(html).toContain("Cargando la sección…");
    expect(html).toContain('aria-hidden="true"');
  });
});
