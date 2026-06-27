import { describe, expect, it } from "vitest";

import { exchangeAuthCode } from "@/lib/auth/callback";

describe("auth callback route", () => {
  it("exchanges the auth code and redirects to the next URL", async () => {
    let exchangedCode: string | null = null;
    const supabase = {
      auth: {
        exchangeCodeForSession: async (code: string) => {
          exchangedCode = code;
          return { data: { session: null }, error: null };
        }
      }
    } as unknown as Parameters<typeof exchangeAuthCode>[1];

    const response = await exchangeAuthCode(
      new URL("http://localhost:3000/api/auth/callback?code=abc123&next=/dashboard"),
      supabase
    );

    expect(exchangedCode).toBe("abc123");
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost:3000/dashboard");
  });
});
