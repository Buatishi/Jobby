"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Mail } from "lucide-react";

import { Button } from "@/components/ui/button";
import { startGoogleSignIn } from "@/lib/auth/google-sign-in";
import { safeRedirectPath } from "@/lib/auth/safe-redirect";
import { forgetSessionData } from "@/lib/auth/session-data";
import { useI18n } from "@/lib/i18n/provider";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { AuthLayout } from "@/src/components/auth/AuthLayout";
import { GoogleIcon } from "@/src/components/auth/GoogleIcon";
import { PasswordInput } from "@/src/components/auth/PasswordInput";

const inputClassName =
  "h-12 w-full rounded-full border border-brand-line bg-white px-5 text-sm outline-none ring-offset-background transition-all duration-200 placeholder:text-black/35 hover:border-black/20 focus-visible:border-brand-green focus-visible:ring-2 focus-visible:ring-brand-green/25";

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
  const [signedOut, setSignedOut] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isOAuthLoading, setIsOAuthLoading] = useState(false);

  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search);
    const oauthError = searchParams.get("error");

    if (oauthError) {
      setError(
        oauthError === "session-expired"
          ? "Tu sesión venció. Iniciá sesión nuevamente para continuar."
          : oauthError
      );
    }

    setResetSuccess(searchParams.get("reset") === "success");
    setSignedOut(searchParams.get("signed_out") === "1");
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

      forgetSessionData();
      const searchParams = new URLSearchParams(window.location.search);
      router.push(safeRedirectPath(searchParams.get("next")));
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
      const oauthError = await startGoogleSignIn(
        supabase.auth,
        window.location.origin
      );

      if (oauthError) {
        setError(oauthError);
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
        <p className="text-sm font-semibold text-brand-green">
          {t("auth.loginEyebrow")}
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          {t("auth.loginTitle")}
        </h1>
        <p className="text-sm leading-6 text-muted-foreground">
          {t("auth.loginSubtitle")}
        </p>
      </div>

      {resetSuccess ? (
        <div className="mt-6 rounded-2xl border border-brand-green/20 bg-brand-green-light px-4 py-3 text-sm font-medium text-brand-green">
          {t("auth.passwordReset")}
        </div>
      ) : null}

      {signedOut ? (
        <div
          className="mt-6 rounded-2xl border border-brand-green/20 bg-brand-green-light px-4 py-3 text-sm font-medium text-brand-green"
          role="status"
        >
          {t("auth.signedOut")}
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
              className="text-xs font-semibold text-brand-green transition-colors hover:text-brand-ink"
              href="/forgot-password"
            >
              {t("auth.forgotPassword")}
            </Link>
          </div>
          <PasswordInput
            autoComplete="current-password"
            className={inputClassName}
            id="password"
            minLength={6}
            onChange={(event) => setPassword(event.target.value)}
            required
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
          className="font-semibold text-foreground transition-colors hover:text-brand-green"
          href="/register"
        >
          {t("common.register")}
        </Link>
      </p>
      <p className="mt-4 flex items-center justify-center gap-2 text-center text-xs font-medium text-black/40">
        <Mail className="h-3.5 w-3.5" />
        {t("auth.protectedBy")}
      </p>
      <p className="mt-3 text-center text-xs font-medium text-black/40">
        <Link className="hover:text-brand-green" href="/terms">
          Términos
        </Link>
        <span className="px-2">·</span>
        <Link className="hover:text-brand-green" href="/privacy">
          Privacidad
        </Link>
      </p>
    </AuthLayout>
  );
}
