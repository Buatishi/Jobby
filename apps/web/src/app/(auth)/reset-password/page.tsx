"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { AuthLayout } from "@/src/components/auth/AuthLayout";
import { PasswordInput } from "@/src/components/auth/PasswordInput";

const inputClassName =
  "h-12 w-full rounded-xl border border-black/10 bg-white px-3 text-sm outline-none ring-offset-background transition-all duration-200 placeholder:text-black/35 hover:border-black/20 focus-visible:border-[#0F6E56] focus-visible:ring-2 focus-visible:ring-[#0F6E56]/25";

function getAuthErrorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : "No pudimos actualizar tu contraseña. Probá de nuevo.";
}

export default function ResetPasswordPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isPreparingSession, setIsPreparingSession] = useState(true);

  useEffect(() => {
    async function prepareRecoverySession() {
      const searchParams = new URLSearchParams(window.location.search);
      const code = searchParams.get("code");

      if (!code) {
        setIsPreparingSession(false);
        return;
      }

      try {
        const supabase = createSupabaseBrowserClient();
        const { error: exchangeError } =
          await supabase.auth.exchangeCodeForSession(code);

        if (exchangeError) {
          setError(exchangeError.message);
          return;
        }

        window.history.replaceState(null, "", "/reset-password");
      } catch (authError) {
        setError(getAuthErrorMessage(authError));
      } finally {
        setIsPreparingSession(false);
      }
    }

    void prepareRecoverySession();
  }, []);

  async function handleUpdatePassword(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setIsSubmitting(true);

    try {
      const supabase = createSupabaseBrowserClient();
      const { error: updateError } = await supabase.auth.updateUser({
        password
      });

      if (updateError) {
        setError(updateError.message);
        return;
      }

      router.push("/login?reset=success");
      router.refresh();
    } catch (authError) {
      setError(getAuthErrorMessage(authError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthLayout headline="Elegí tu nueva contraseña">
      <div className="space-y-2">
        <p className="text-sm font-bold uppercase tracking-[0.18em] text-[#0F6E56]">
          Nueva contraseña
        </p>
        <h1 className="text-3xl font-black tracking-tight">
          Restablecer acceso
        </h1>
        <p className="text-sm leading-6 text-muted-foreground">
          Elegí una contraseña nueva para volver a entrar a Jobby.
        </p>
      </div>

      <form className="mt-8 space-y-4" onSubmit={handleUpdatePassword}>
        <div className="space-y-2">
          <label className="text-sm font-semibold" htmlFor="password">
            Nueva contraseña
          </label>
          <PasswordInput
            autoComplete="new-password"
            className={inputClassName}
            disabled={isPreparingSession}
            id="password"
            minLength={8}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Mínimo 8 caracteres"
            required
            value={password}
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-semibold" htmlFor="confirmPassword">
            Confirmar contraseña
          </label>
          <PasswordInput
            autoComplete="new-password"
            className={inputClassName}
            disabled={isPreparingSession}
            id="confirmPassword"
            minLength={8}
            onChange={(event) => setConfirmPassword(event.target.value)}
            placeholder="Repetí la contraseña"
            required
            value={confirmPassword}
          />
        </div>

        {error ? (
          <div className="rounded-2xl border border-destructive/15 bg-destructive/5 px-4 py-3 text-sm font-medium text-destructive">
            {error}
          </div>
        ) : null}

        <Button
          disabled={isPreparingSession}
          fullWidth
          isLoading={isSubmitting || isPreparingSession}
          rightIcon={<ArrowRight className="h-4 w-4" />}
          size="lg"
          type="submit"
          variant="primary"
        >
          {isPreparingSession ? "Validando link..." : "Actualizar contraseña"}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        <Link
          className="inline-flex items-center gap-2 font-semibold text-foreground transition-colors hover:text-[#0F6E56]"
          href="/login"
        >
          <ArrowLeft className="h-4 w-4" />
          Volver a iniciar sesión
        </Link>
      </p>
    </AuthLayout>
  );
}
