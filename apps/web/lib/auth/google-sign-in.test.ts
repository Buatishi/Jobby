import { describe, expect, it, vi } from "vitest";

import { startGoogleSignIn } from "@/lib/auth/google-sign-in";

type Auth = Parameters<typeof startGoogleSignIn>[0];

function fakeAuth(options: { oauthError?: string; sessionReady?: Promise<void> } = {}) {
  const calls: string[] = [];
  const signInWithOAuth = vi.fn(async () => {
    calls.push("signInWithOAuth");
    return options.oauthError
      ? { data: { provider: "google", url: null }, error: { message: options.oauthError } }
      : { data: { provider: "google", url: "https://auth.example/authorize" }, error: null };
  });
  const auth = {
    getSession: async () => {
      await options.sessionReady;
      calls.push("getSession");
      return { data: { session: null }, error: null };
    },
    stopAutoRefresh: async () => {
      calls.push("stopAutoRefresh");
    },
    startAutoRefresh: async () => {
      calls.push("startAutoRefresh");
    },
    signInWithOAuth
  };
  return { auth: auth as unknown as Auth, calls, signInWithOAuth };
}

describe("startGoogleSignIn", () => {
  it("waits for the client to settle before creating the PKCE verifier", async () => {
    let finishRefresh: () => void = () => undefined;
    const sessionReady = new Promise<void>((resolve) => {
      finishRefresh = resolve;
    });
    const { auth, calls, signInWithOAuth } = fakeAuth({ sessionReady });

    const started = startGoogleSignIn(auth, "https://jobbyweb.vercel.app");
    await Promise.resolve();

    // Mientras la renovación de una sesión abierta no termina, no se crea el verificador.
    expect(signInWithOAuth).not.toHaveBeenCalled();

    finishRefresh();
    await expect(started).resolves.toBeNull();
    expect(calls).toEqual(["getSession", "stopAutoRefresh", "signInWithOAuth"]);
  });

  it("sends Google back to the callback of this site", async () => {
    const { auth, signInWithOAuth } = fakeAuth();

    await startGoogleSignIn(auth, "https://jobbyweb.vercel.app");

    expect(signInWithOAuth).toHaveBeenCalledWith({
      provider: "google",
      options: {
        redirectTo: "https://jobbyweb.vercel.app/api/auth/callback?next=/dashboard",
        queryParams: { access_type: "offline", prompt: "select_account" }
      }
    });
  });

  it("returns the error and resumes the refresh when Google cannot start", async () => {
    const { auth, calls } = fakeAuth({ oauthError: "Provider is not enabled" });

    await expect(startGoogleSignIn(auth, "https://jobbyweb.vercel.app")).resolves.toBe(
      "Provider is not enabled"
    );
    expect(calls.at(-1)).toBe("startAutoRefresh");
  });
});
