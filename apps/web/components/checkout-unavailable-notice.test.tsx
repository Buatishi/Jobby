import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CheckoutUnavailableNotice } from "@/components/checkout-unavailable-notice";
import { I18nProvider } from "@/lib/i18n/provider";

describe("CheckoutUnavailableNotice", () => {
  it("says payments are not available yet and points to the free plan", () => {
    const html = renderToStaticMarkup(
      <I18nProvider>
        <CheckoutUnavailableNotice />
      </I18nProvider>
    );

    expect(html).toContain("Los pagos todavía no están disponibles");
    expect(html).toContain("plan gratis");
    expect(html).toContain('role="status"');
  });
});
