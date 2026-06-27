import { describe, expect, it, vi } from "vitest";

import { requireAuthenticatedSession } from "@/lib/auth/guard";

vi.mock("next/navigation", () => ({
  redirect: (path: string) => {
    throw new Error(`NEXT_REDIRECT:${path}`);
  }
}));

describe("app auth layout", () => {
  it("redirects to login when there is no session", async () => {
    const supabase = {
      auth: {
        getSession: async () => ({ data: { session: null } })
      }
    } as unknown as Parameters<typeof requireAuthenticatedSession>[0];

    await expect(requireAuthenticatedSession(supabase)).rejects.toThrow(
      "NEXT_REDIRECT:/login"
    );
  });
});
