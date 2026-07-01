"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";

import { GoogleIcon } from "@/src/components/auth/GoogleIcon";
import { AuthLayout } from "@/src/components/auth/AuthLayout";
import { Button } from "@/components/ui/button";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

const inputClassName =
  "h-12 w-full rounded-xl border border-black/10 bg-white px-3 text-sm outline-none ring-offset-background transition-all duration-200 placeholder:text-black/35 hover:border-black/20 focus-visible:border-[#0F6E56] focus-visible:ring-2 focus-visible:ring-[#0F6E56]/25";

function getAuthErrorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : "No pudimos completar el registro. Probá de nuevo.";
}

export default function RegisterPage() {
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
      setError("Tenés que aceptar los Términos de Servicio para registrarte.");
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
      setError(getAuthErrorMessage(authError));
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
      setError(getAuthErrorMessage(authError));
      setIsOAuthLoading(false);
    }
  }

  return (
    <AuthLayout headline="Empezá a prepararte mejor">
      <div className="space-y-2">
        <p className="text-sm font-bold uppercase tracking-[0.18em] text-[#0F6E56]">
          Cuenta nueva
        </p>
        <h1 className="text-3xl font-black tracking-tight">Registrarse</h1>
        <p className="text-sm leading-6 text-muted-foreground">
          Creá tu cuenta y empezá desde el dashboard. Después podés completar tu
          perfil paso a paso.
        </p>
      </div>

      <form className="mt-8 space-y-4" onSubmit={handleRegister}>
        <div className="space-y-2">
          <label className="text-sm font-semibold" htmlFor="fullName">
            Nombre completo
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
        <div className="space-y-2">
          <label className="text-sm font-semibold" htmlFor="password">
            Contraseña
          </label>
          <input
            autoComplete="new-password"
            className={inputClassName}
            id="password"
            minLength={6}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Mínimo 6 caracteres"
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
          <span>
            Acepto los Términos de Servicio y el procesamiento de mis datos con
            sistemas de IA para generar análisis del servicio.
          </span>
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
          {isSubmitting ? "Creando cuenta..." : "Registrarse"}
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
        {isOAuthLoading ? "Abriendo Google..." : "Continuar con Google"}
      </Button>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        ¿Ya tenés cuenta?{" "}
        <Link
          className="font-semibold text-foreground transition-colors hover:text-[#0F6E56]"
          href="/login"
        >
          Iniciar sesión
        </Link>
      </p>
    </AuthLayout>
  );
}
