import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "@/lib/i18n/provider";

import { AuthLayout } from "./AuthLayout";

describe("AuthLayout", () => {
  it("sizes the form section with the dynamic viewport so mobile browsers do not force a scroll", () => {
    const html = renderToStaticMarkup(
      <I18nProvider>
        <AuthLayout headline="Entrá a Jobby">
          <form />
        </AuthLayout>
      </I18nProvider>
    );

    expect(html).toContain("min-h-[calc(100dvh-140px)]");
    expect(html).not.toContain("100vh-140px");
  });
});
