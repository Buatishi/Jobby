import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({ apiClient: vi.fn(), apiStream: vi.fn() }));

import { forgetApiResources } from "@/lib/api/use-api-resource";
import { I18nProvider } from "@/lib/i18n/provider";
import ProfilePage from "@/src/app/(app)/profile/page";

beforeEach(() => {
  forgetApiResources();
});

describe("ProfilePage", () => {
  it("has a card for the CV and another for the LinkedIn PDF, the CV first", () => {
    const html = renderToStaticMarkup(
      <I18nProvider>
        <ProfilePage />
      </I18nProvider>
    );

    const cvCard = html.indexOf("Tu CV");
    const linkedinCard = html.indexOf("PDF de tu perfil de LinkedIn");

    expect(cvCard).toBeGreaterThan(-1);
    expect(linkedinCard).toBeGreaterThan(-1);
    expect(cvCard).toBeLessThan(linkedinCard);
  });
});
