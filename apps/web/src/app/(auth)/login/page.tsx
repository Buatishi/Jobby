"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Mail } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n/provider";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { AuthLayout } from "@/src/components/auth/AuthLayout";
import { GoogleIcon } from "@/src/components/auth/GoogleIcon";

const inputClassName =
  "h-12 w-full rounded-xl border border-black/10 bg-white px-3 text-sm outline-none ring-offset-background transition-all duration-200 placeholder:text-black/35 hover:border-black/20 focus-visible:border-[#0F6E56] focus-visible:ring-2 focus-visible:ring-[#0F6E56]/25";

function getAuthErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export default function LoginPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [resetSuccess, setResetSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isOAuthLoading, setIsOAuthLoading] = useState(false);

  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search);
    const oauthError = searchParams.get("error");

    if (oauthError) {
      setError(oauthError);
    }

    setResetSuccess(searchParams.get("reset") === "success");
  }, []);

  async function handleEmailLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const supabase = createSupabaseBrowserClient();
      const { error: loginError } = await supabase.auth.signInWithPassword({
        email,
        password
      });

      if (loginError) {
        setError(loginError.message);
        return;
      }

      router.push("/dashboard");
      router.refresh();
    } catch (authError) {
      setError(getAuthErrorMessage(authError, t("auth.authError")));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleGoogleLogin() {
    setError(null);
    setIsOAuthLoading(true);

    try {
      const supabase = createSupabaseBrowserClient();
      const { error: oauthError } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/api/auth/callback?next=/dashboard`,
          queryParams: {
            access_type: "offline",
            prompt: "select_account"
          }
        }
      });

      if (oauthError) {
        setError(oauthError.message);
        setIsOAuthLoading(false);
      }
    } catch (authError) {
      setError(getAuthErrorMessage(authError, t("auth.authError")));
      setIsOAuthLoading(false);
    }
  }

  return (
    <AuthLayout headline={t("auth.loginHeadline")}>
      <div className="space-y-2">
        <p className="text-sm font-bold uppercase tracking-[0.18em] text-[#0F6E56]">
          {t("auth.loginEyebrow")}
        </p>
        <h1 className="text-3xl font-black tracking-tight">
          {t("auth.loginTitle")}
        </h1>
        <p className="text-sm leading-6 text-muted-foreground">
          {t("auth.loginSubtitle")}
        </p>
      </div>

      {resetSuccess ? (
        <div className="mt-6 rounded-2xl border border-[#0F6E56]/15 bg-[#0F6E56]/10 px-4 py-3 text-sm font-medium text-[#0F6E56]">
          {t("auth.passwordReset")}
        </div>
      ) : null}

      <form className="mt-8 space-y-4" onSubmit={handleEmailLogin}>
        <div className="space-y-2">
          <label className="text-sm font-semibold" htmlFor="email">
            {t("auth.email")}
          </label>
          <input
            autoComplete="email"
            className={inputClassName}
            id="email"
            onChange={(event) => setEmail(event.target.value)}
            placeholder="tu@email.com"
            required
            type="email"
            value={email}
          />
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-3">
            <label className="text-sm font-semibold" htmlFor="password">
              {t("auth.password")}
            </label>
            <Link
              className="text-xs font-semibold text-[#0F6E56] transition-colors hover:text-[#0d5c48]"
              href="/forgot-password"
            >
              {t("auth.forgotPassword")}
            </Link>
          </div>
          <input
            autoComplete="current-password"
            className={inputClassName}
            id="password"
            minLength={6}
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </div>

        {error ? (
          <div className="rounded-2xl border border-destructive/15 bg-destructive/5 px-4 py-3 text-sm font-medium text-destructive">
            {error}
          </div>
        ) : null}

        <Button
          fullWidth
          isLoading={isSubmitting}
          rightIcon={<ArrowRight className="h-4 w-4" />}
          size="lg"
          type="submit"
          variant="primary"
        >
          {isSubmitting ? t("auth.loggingIn") : t("auth.loginTitle")}
        </Button>
      </form>

      <div className="my-6 flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-black/35">
        <span className="h-px flex-1 bg-black/10" />
        o
        <span className="h-px flex-1 bg-black/10" />
      </div>

      <Button
        fullWidth
        isLoading={isOAuthLoading}
        leftIcon={<GoogleIcon className="h-4 w-4" />}
        onClick={handleGoogleLogin}
        size="lg"
        type="button"
        variant="outline"
      >
        {isOAuthLoading ? t("auth.googleOpening") : t("auth.googleContinue")}
      </Button>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        {t("auth.noAccount")}{" "}
        <Link
          className="font-semibold text-foreground transition-colors hover:text-[#0F6E56]"
          href="/register"
        >
          {t("common.register")}
        </Link>
      </p>
      <p className="mt-4 flex items-center justify-center gap-2 text-center text-xs font-medium text-black/40">
        <Mail className="h-3.5 w-3.5" />
        {t("auth.protectedBy")}
      </p>
    </AuthLayout>
  );
}
