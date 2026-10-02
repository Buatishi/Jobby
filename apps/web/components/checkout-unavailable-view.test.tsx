import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/lib/i18n/provider";

const session = vi.hoisted(() => ({ hasSession: null as boolean | null }));

vi.mock("@/lib/auth/use-has-session", () => ({
  useHasSession: () => session.hasSession
}));

import { CheckoutUnavailableView } from "@/components/checkout-unavailable-view";

function render(hasSession: boolean | null) {
  session.hasSession = hasSession;
  return renderToStaticMarkup(
    <I18nProvider>
      <CheckoutUnavailableView />
    </I18nProvider>
  );
}

describe("CheckoutUnavailableView", () => {
  it("shows the 404, the sad résumé and says the team is working on it", () => {
    const html = render(false);

    expect(html).toContain("404");
    expect(html).toContain("Estamos trabajando en esto");
    expect(html).toContain("plan gratis");
    expect(html).toContain('aria-label="Un CV con cara triste"');
  });

  it("goes back to the plans, and to the dashboard when there is a session", () => {
    const html = render(true);

    expect(html).toContain('href="/pricing"');
    expect(html).toContain('href="/dashboard"');
    expect(html).toContain("Ir al dashboard");
  });

  it("offers the home page instead of the dashboard without a session", () => {
    for (const hasSession of [false, null]) {
      const html = render(hasSession);

      expect(html).toContain("Ir al inicio");
      expect(html).not.toContain('href="/dashboard"');
    }
  });
});
