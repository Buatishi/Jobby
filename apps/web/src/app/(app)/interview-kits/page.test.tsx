import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type { CurrentUserProfile } from "@/lib/auth/permissions";

const session = vi.hoisted(() => ({ profile: null as CurrentUserProfile | null }));

vi.mock("@/lib/api/client", () => ({ apiClient: vi.fn() }));
vi.mock("@/lib/auth/use-current-user", () => ({
  useCurrentUser: () => session.profile
}));

import InterviewKitsPage from "@/src/app/(app)/interview-kits/page";

function renderWithTier(tier: string | null) {
  session.profile =
    tier === null
      ? null
      : { id: "user-1", email: null, role: "user", tier, permissions: [] };
  return renderToStaticMarkup(<InterviewKitsPage />);
}

describe("InterviewKitsPage", () => {
  it("lets premium users create a kit", () => {
    const html = renderWithTier("premium");

    expect(html).toContain('href="/interview-kits/new"');
    expect(html).not.toContain("Función Premium");
  });

  it("shows the premium notice instead of a button the free plan cannot use", () => {
    const html = renderWithTier("free");

    expect(html).toContain("Función Premium");
    expect(html).toContain('href="/pricing"');
    expect(html).not.toContain("Nuevo Kit");
  });

  it("offers neither while the plan is loading", () => {
    const html = renderWithTier(null);

    expect(html).not.toContain("Nuevo Kit");
    expect(html).not.toContain("Función Premium");
  });
});
