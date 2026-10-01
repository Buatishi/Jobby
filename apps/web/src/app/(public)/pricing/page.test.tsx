import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/lib/i18n/provider";

const session = vi.hoisted(() => ({ hasSession: null as boolean | null }));

vi.mock("@/lib/api/client", () => ({ apiClient: vi.fn() }));
vi.mock("@/lib/auth/use-has-session", () => ({
  useHasSession: () => session.hasSession
}));

import PricingPage from "@/src/app/(public)/pricing/page";

function render(hasSession: boolean | null) {
  session.hasSession = hasSession;
  return renderToStaticMarkup(
    <I18nProvider>
      <PricingPage />
    </I18nProvider>
  );
}

describe("PricingPage", () => {
  it("lets a signed-in person go back to the dashboard", () => {
    const html = render(true);

    expect(html).toContain("Volver al dashboard");
    expect(html).toContain('href="/dashboard"');
  });

  it("does not offer the dashboard without a session", () => {
    expect(render(false)).not.toContain("Volver al dashboard");
  });

  it("does not offer it while the session is being read", () => {
    expect(render(null)).not.toContain("Volver al dashboard");
  });
});
