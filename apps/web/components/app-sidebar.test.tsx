import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type { CurrentUserProfile } from "@/lib/auth/permissions";

const session = vi.hoisted(() => ({ profile: null as CurrentUserProfile | null }));

vi.mock("next/navigation", () => ({ usePathname: () => "/dashboard" }));
vi.mock("@/lib/auth/use-current-user", () => ({
  useCurrentUser: () => session.profile
}));
vi.mock("@/lib/auth/sign-out", () => ({ signOutAndLeave: vi.fn() }));

import { AppSidebar } from "@/components/app-sidebar";
import { I18nProvider } from "@/lib/i18n/provider";

function renderWithTier(tier: string | null) {
  session.profile =
    tier === null
      ? null
      : { id: "user-1", email: null, role: "user", tier, permissions: [] };
  return renderToStaticMarkup(
    <I18nProvider>
      <AppSidebar userName="Persona de prueba" />
    </I18nProvider>
  );
}

describe("AppSidebar", () => {
  it("locks interview kits and offers the upgrade on the free plan", () => {
    const html = renderWithTier("free");

    expect(html).toContain('href="/interview-kits"');
    expect(html).toContain("lucide-lock");
    expect(html).toContain('href="/pricing"');
  });

  it("shows premium users their plan without locks or upgrade offers", () => {
    const html = renderWithTier("premium");

    expect(html).toContain('href="/interview-kits"');
    expect(html).not.toContain("lucide-lock");
    expect(html).not.toContain('href="/pricing"');
  });

  it("does not guess a plan while the profile is loading", () => {
    const html = renderWithTier(null);

    expect(html).not.toContain("lucide-lock");
    expect(html).not.toContain('href="/pricing"');
  });
});
