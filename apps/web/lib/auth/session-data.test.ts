import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({ apiClient: vi.fn() }));

import { apiClient } from "@/lib/api/client";
import { fetchAndRemember, rememberedResponse } from "@/lib/api/use-api-resource";
import { forgetSessionData } from "@/lib/auth/session-data";
import { loadCurrentUser } from "@/lib/auth/use-current-user";

describe("forgetSessionData", () => {
  it("forgets the profile and the screens of the previous session", async () => {
    const apiClientMock = vi.mocked(apiClient);
    apiClientMock.mockResolvedValue({ id: "previous-person" });
    await loadCurrentUser();
    await fetchAndRemember("/api/v1/jobs");

    forgetSessionData();

    expect(rememberedResponse("/api/v1/jobs")).toBeUndefined();
    await loadCurrentUser();
    // El perfil se vuelve a pedir en lugar de reutilizar el de la sesión anterior.
    expect(apiClientMock.mock.calls.map(([path]) => path)).toEqual([
      "/api/v1/users/me",
      "/api/v1/jobs",
      "/api/v1/users/me"
    ]);
  });
});
