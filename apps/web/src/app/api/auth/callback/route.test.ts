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

  it.each([
    ["https://evil.example/phishing"],
    ["//evil.example"],
    ["/\u005cevil.example"]
  ])("never redirects to another site (next=%s)", async (next) => {
    const supabase = {
      auth: {
        exchangeCodeForSession: async () => ({ data: { session: null }, error: null })
      }
    } as unknown as Parameters<typeof exchangeAuthCode>[1];
    const url = new URL("http://localhost:3000/api/auth/callback?code=abc123");
    url.searchParams.set("next", next);

    const response = await exchangeAuthCode(url, supabase);

    expect(response.headers.get("location")).toBe("http://localhost:3000/dashboard");
  });

  it("redirects OAuth provider errors back to login", async () => {
    const supabase = {
      auth: {
        exchangeCodeForSession: async () => {
          return { data: { session: null }, error: null };
        }
      }
    } as unknown as Parameters<typeof exchangeAuthCode>[1];

    const response = await exchangeAuthCode(
      new URL(
        "http://localhost:3000/api/auth/callback?error_description=Google%20OAuth%20failed"
      ),
      supabase
    );

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe(
      "http://localhost:3000/login?error=Google+OAuth+failed"
    );
  });

  it("explains in Spanish when the PKCE verifier is missing", async () => {
    const supabase = {
      auth: {
        exchangeCodeForSession: async () => ({
          data: { session: null },
          error: {
            code: "pkce_code_verifier_not_found",
            message: "PKCE code verifier not found in storage."
          }
        })
      }
    } as unknown as Parameters<typeof exchangeAuthCode>[1];

    const response = await exchangeAuthCode(
      new URL("http://localhost:3000/api/auth/callback?code=abc123"),
      supabase
    );

    const location = new URL(response.headers.get("location") ?? "");
    expect(location.pathname).toBe("/login");
    expect(location.searchParams.get("error")).toBe(
      "No pudimos terminar el inicio con Google en este navegador. Volvé a intentarlo."
    );
  });
});
