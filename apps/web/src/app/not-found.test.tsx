import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "@/lib/i18n/provider";
import NotFound from "@/src/app/not-found";

describe("NotFound", () => {
  it("says the page does not exist and links home and to the dashboard", () => {
    const html = renderToStaticMarkup(
      <I18nProvider>
        <NotFound />
      </I18nProvider>
    );

    expect(html).toContain("Esta página no existe");
    expect(html).toContain('href="/"');
    expect(html).toContain('href="/dashboard"');
  });
});
