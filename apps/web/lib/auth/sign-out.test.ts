import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/supabase/client", () => ({
  createSupabaseBrowserClient: () => ({
    auth: { signOut: async () => ({ error: null }) }
  })
}));

import { SIGNED_OUT_URL, signOutAndLeave } from "@/lib/auth/sign-out";

describe("signOutAndLeave", () => {
  it("closes the session and then leaves for the login", async () => {
    const steps: string[] = [];

    const closed = await signOutAndLeave({
      signOut: async () => {
        steps.push("signOut");
        return { error: null };
      },
      navigate: (url) => {
        steps.push(`navigate ${url}`);
      }
    });

    expect(closed).toBe(true);
    expect(steps).toEqual(["signOut", `navigate ${SIGNED_OUT_URL}`]);
  });

  it.each([
    ["Supabase answers with an error", async () => ({ error: new Error("503") })],
    [
      "the request cannot be sent",
      async () => {
        throw new Error("sin conexión");
      }
    ]
  ])("stays when %s, because the session is still open", async (_case, signOut) => {
    const navigate = vi.fn();

    const closed = await signOutAndLeave({ signOut, navigate });

    expect(closed).toBe(false);
    expect(navigate).not.toHaveBeenCalled();
  });

  it("asks Supabase to close only this device's session", async () => {
    const signOut = vi.fn(async () => ({ error: null }));
    vi.resetModules();
    vi.doMock("@/lib/supabase/client", () => ({
      createSupabaseBrowserClient: () => ({ auth: { signOut } })
    }));
    const { signOutAndLeave: fresh } = await import("@/lib/auth/sign-out");

    await fresh({ navigate: () => undefined });

    expect(signOut).toHaveBeenCalledWith({ scope: "local" });
  });
});
