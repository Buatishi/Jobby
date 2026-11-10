import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "@/lib/i18n/provider";
import PrivacyPage from "@/src/app/privacy/page";

describe("privacy policy: visit measurement", () => {
  it("tells that the public pages are measured and the account is not", () => {
    const html = renderToStaticMarkup(
      <I18nProvider>
        <PrivacyPage />
      </I18nProvider>
    );

    expect(html).toContain("Medición de visitas");
    expect(html).toContain("Vercel Web Analytics");
    expect(html).toContain("inicio, precios y guías");
    expect(html).toContain("No medimos lo que hacés dentro de tu cuenta");
  });

  // La página solo se dibuja en español sin el navegador: el inglés se mira en el código.
  it("says the same in English", () => {
    const source = readFileSync(
      fileURLToPath(new URL("./page.tsx", import.meta.url)),
      "utf8"
    );

    expect(source).toContain("Visit measurement");
    expect(source).toContain("We do not measure what you do inside your account");
  });
});
