import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/supabase/client", () => ({
  createSupabaseBrowserClient: () => ({
    auth: { signOut: async () => ({ error: null }) }
  })
}));

import { SIGNED_OUT_URL, signOutAndLeave } from "@/lib/auth/sign-out";
import { WIZARD_PROGRESS_KEY } from "@/lib/wizard/progress";

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

  it("clears the onboarding progress that the browser kept for the account", async () => {
    const removed: string[] = [];
    vi.stubGlobal("window", {
      localStorage: { removeItem: (key: string) => removed.push(key) }
    });

    try {
      await signOutAndLeave({
        signOut: async () => ({ error: null }),
        navigate: () => undefined
      });
    } finally {
      vi.unstubAllGlobals();
    }

    expect(removed).toEqual([WIZARD_PROGRESS_KEY]);
  });

  it("keeps the onboarding progress when the session could not be closed", async () => {
    const removeItem = vi.fn();
    vi.stubGlobal("window", { localStorage: { removeItem } });

    try {
      await signOutAndLeave({
        signOut: async () => ({ error: new Error("503") }),
        navigate: () => undefined
      });
    } finally {
      vi.unstubAllGlobals();
    }

    expect(removeItem).not.toHaveBeenCalled();
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
