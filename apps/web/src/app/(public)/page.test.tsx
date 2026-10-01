import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/lib/i18n/provider";

const session = vi.hoisted(() => ({ hasSession: null as boolean | null }));

vi.mock("@/lib/auth/use-has-session", () => ({
  useHasSession: () => session.hasSession
}));

import LandingPage from "@/src/app/(public)/page";

function render(hasSession: boolean | null) {
  session.hasSession = hasSession;
  return renderToStaticMarkup(
    <I18nProvider>
      <LandingPage />
    </I18nProvider>
  );
}

describe("LandingPage header", () => {
  it("offers the dashboard instead of login when the session is open", () => {
    const html = render(true);

    expect(html).toContain("Ir al dashboard");
    expect(html).not.toContain("Iniciar sesión");
  });

  it("offers login and sign up without a session", () => {
    const html = render(false);

    expect(html).toContain("Iniciar sesión");
    expect(html).toContain('href="/register"');
    expect(html).not.toContain("Ir al dashboard");
  });

  it("keeps login and sign up while the session is being read", () => {
    const html = render(null);

    expect(html).toContain("Iniciar sesión");
    expect(html).not.toContain("Ir al dashboard");
  });
});
