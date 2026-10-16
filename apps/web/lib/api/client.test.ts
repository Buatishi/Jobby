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

describe("apiClient with a gateway error on a write", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("does not repeat a PATCH that was not declared idempotent", async () => {
    const fetchMock = vi.fn(async () => new Response("", { status: 502 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      apiClient("/api/v1/profiles/me", { method: "PATCH", body: "{}" })
    ).rejects.toThrow("status 502");

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("repeats a PATCH declared idempotent until the API answers", async () => {
    vi.useFakeTimers();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response("", { status: 502 }))
      .mockResolvedValueOnce(new Response('{"ok":true}', { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const request = apiClient<{ ok: boolean }>("/api/v1/profiles/me", {
      method: "PATCH",
      body: '{"headline":"Chef"}',
      idempotent: true
    });
    await vi.advanceTimersByTimeAsync(1000);

    await expect(request).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    // La marca es de la app: no viaja como opción del fetch.
    const init = fetchMock.mock.calls[0]?.[1] as Record<string, unknown>;
    expect(init).not.toHaveProperty("idempotent");
    expect(init.method).toBe("PATCH");
  });
});
