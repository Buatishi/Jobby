"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";

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

export default function RegisterPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [acceptedTos, setAcceptedTos] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isOAuthLoading, setIsOAuthLoading] = useState(false);

  function validateTos() {
    if (!acceptedTos) {
      setError(t("auth.tosRequired"));
      return false;
    }

    return true;
  }

  async function handleRegister(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!validateTos()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const supabase = createSupabaseBrowserClient();
      const origin = window.location.origin;
      const { error: signUpError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: fullName,
            accepted_tos: true
          },
          emailRedirectTo: `${origin}/api/auth/callback?next=/dashboard`
        }
      });

      if (signUpError) {
        setError(signUpError.message);
        return;
      }

      router.push("/dashboard");
      router.refresh();
    } catch (authError) {
      setError(getAuthErrorMessage(authError, t("auth.registerError")));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleGoogleRegister() {
    setError(null);

    if (!validateTos()) {
      return;
    }

    setIsOAuthLoading(true);

    try {
      const supabase = createSupabaseBrowserClient();
      const origin = window.location.origin;
      const { error: oauthError } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${origin}/api/auth/callback?next=/dashboard`,
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
      setError(getAuthErrorMessage(authError, t("auth.registerError")));
      setIsOAuthLoading(false);
    }
  }

  return (
    <AuthLayout headline={t("auth.registerHeadline")}>
      <div className="space-y-2">
        <p className="text-sm font-bold uppercase tracking-[0.18em] text-[#0F6E56]">
          {t("auth.registerEyebrow")}
        </p>
        <h1 className="text-3xl font-black tracking-tight">
          {t("auth.registerTitle")}
        </h1>
        <p className="text-sm leading-6 text-muted-foreground">
          {t("auth.registerSubtitle")}
        </p>
      </div>

      <form className="mt-8 space-y-4" onSubmit={handleRegister}>
        <div className="space-y-2">
          <label className="text-sm font-semibold" htmlFor="fullName">
            {t("auth.fullName")}
          </label>
          <input
            autoComplete="name"
            className={inputClassName}
            id="fullName"
            onChange={(event) => setFullName(event.target.value)}
            placeholder="Bautista Giraud"
            required
            type="text"
            value={fullName}
          />
        </div>
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
          <label className="text-sm font-semibold" htmlFor="password">
            {t("auth.password")}
          </label>
          <input
            autoComplete="new-password"
            className={inputClassName}
            id="password"
            minLength={6}
            onChange={(event) => setPassword(event.target.value)}
            placeholder={t("auth.minPassword")}
            required
            type="password"
            value={password}
          />
        </div>

        <label className="flex items-start gap-3 rounded-2xl border border-black/5 bg-[#fbfcfb] p-3 text-sm leading-6 transition-colors hover:bg-brand-green-light/40">
          <input
            checked={acceptedTos}
            className="mt-1 h-4 w-4 rounded border-input accent-[#0F6E56]"
            onChange={(event) => setAcceptedTos(event.target.checked)}
            required
            type="checkbox"
          />
          <span>{t("auth.tos")}</span>
        </label>

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
          {isSubmitting ? t("auth.creating") : t("auth.registerTitle")}
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
        onClick={handleGoogleRegister}
        size="lg"
        type="button"
        variant="outline"
      >
        {isOAuthLoading ? t("auth.googleOpening") : t("auth.googleContinue")}
      </Button>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        {t("auth.hasAccount")}{" "}
        <Link
          className="font-semibold text-foreground transition-colors hover:text-[#0F6E56]"
          href="/login"
        >
          {t("common.login")}
        </Link>
      </p>
    </AuthLayout>
  );
}
