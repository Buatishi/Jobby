"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, Mail } from "lucide-react";

import { Button } from "@/components/ui/button";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { AuthLayout } from "@/src/components/auth/AuthLayout";

const inputClassName =
  "h-12 w-full rounded-xl border border-black/10 bg-white px-3 text-sm outline-none ring-offset-background transition-all duration-200 placeholder:text-black/35 hover:border-black/20 focus-visible:border-[#0F6E56] focus-visible:ring-2 focus-visible:ring-[#0F6E56]/25";

function getAuthErrorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : "No pudimos enviar el link de recuperación. Probá de nuevo.";
}

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSent, setIsSent] = useState(false);

  async function handleResetPassword(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const supabase = createSupabaseBrowserClient();
      const { error: resetError } = await supabase.auth.resetPasswordForEmail(
        email,
        {
          redirectTo: `${window.location.origin}/reset-password`
        }
      );

      if (resetError) {
        setError(resetError.message);
        return;
      }

      setIsSent(true);
    } catch (authError) {
      setError(getAuthErrorMessage(authError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthLayout headline="Recuperá el acceso a tu cuenta">
      <div className="space-y-2">
        <p className="text-sm font-bold uppercase tracking-[0.18em] text-[#0F6E56]">
          Recuperación
        </p>
        <h1 className="text-3xl font-black tracking-tight">
          Olvidaste tu contraseña
        </h1>
        <p className="text-sm leading-6 text-muted-foreground">
          Escribí tu email y te mandamos un link para restablecer el acceso.
        </p>
      </div>

      {isSent ? (
        <div className="mt-8 space-y-5">
          <div className="rounded-2xl border border-[#0F6E56]/15 bg-[#0F6E56]/10 px-4 py-4 text-sm font-medium text-[#0F6E56]">
            Revisá tu email. Te enviamos un link para restablecer tu
            contraseña.
          </div>
          <Button asChild fullWidth size="lg" variant="outline">
            <Link href="/login">
              <ArrowLeft className="h-4 w-4" />
              Volver a iniciar sesión
            </Link>
          </Button>
        </div>
      ) : (
        <form className="mt-8 space-y-4" onSubmit={handleResetPassword}>
          <div className="space-y-2">
            <label className="text-sm font-semibold" htmlFor="email">
              Email
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

          {error ? (
            <div className="rounded-2xl border border-destructive/15 bg-destructive/5 px-4 py-3 text-sm font-medium text-destructive">
              {error}
            </div>
          ) : null}

          <Button
            fullWidth
            isLoading={isSubmitting}
            leftIcon={<Mail className="h-4 w-4" />}
            size="lg"
            type="submit"
            variant="primary"
          >
            {isSubmitting ? "Enviando..." : "Enviar link de recuperación"}
          </Button>
        </form>
      )}

      {!isSent ? (
        <p className="mt-6 text-center text-sm text-muted-foreground">
          ¿Ya te acordaste?{" "}
          <Link
            className="font-semibold text-foreground transition-colors hover:text-[#0F6E56]"
            href="/login"
          >
            Volver a iniciar sesión
          </Link>
        </p>
      ) : null}
    </AuthLayout>
  );
}
