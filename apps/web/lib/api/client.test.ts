import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/supabase/client", () => ({
  createSupabaseBrowserClient: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "token" } } }),
      refreshSession: async () => ({
        data: { session: { access_token: "token" } },
        error: null
      }),
      signOut: async () => ({ error: null })
    }
  })
}));

import { ApiForbiddenError, apiClient } from "@/lib/api/client";

function respondWith(status: number, body: string) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(body, { status }))
  );
}

describe("apiClient with a 403", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("raises ApiForbiddenError with the message of the API", async () => {
    respondWith(
      403,
      JSON.stringify({ error: "No tenés permiso para esta acción", code: "FORBIDDEN" })
    );

    const request = apiClient("/api/v1/admin/metrics");

    await expect(request).rejects.toBeInstanceOf(ApiForbiddenError);
    await expect(request).rejects.toThrow("No tenés permiso para esta acción");
  });

  it("explains the missing permission when the body is empty", async () => {
    respondWith(403, "");

    await expect(apiClient("/api/v1/admin/metrics")).rejects.toThrow(
      "No tenés permisos para esta acción."
    );
  });

  it("keeps other errors as plain errors", async () => {
    respondWith(404, JSON.stringify({ error: "Puesto no encontrado" }));

    const request = apiClient("/api/v1/jobs/unknown");

    await expect(request).rejects.not.toBeInstanceOf(ApiForbiddenError);
    await expect(request).rejects.toThrow("Puesto no encontrado");
  });
});

describe("apiClient with an empty success", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("resolves a 204 without reading a body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 204 }))
    );

    await expect(
      apiClient<void>("/api/v1/jobs/job-1", { method: "DELETE" })
    ).resolves.toBeUndefined();
  });
});
