"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { startWizard } from "@/lib/wizard/progress";
import { AuthLayout } from "@/src/components/auth/AuthLayout";

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [acceptedTos, setAcceptedTos] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleRegister(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!acceptedTos) {
      setError("Tenés que aceptar los Términos de Servicio para registrarte.");
      return;
    }

    setIsSubmitting(true);
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
        emailRedirectTo: `${origin}/api/auth/callback?next=/wizard/step-1`
      }
    });
    setIsSubmitting(false);

    if (signUpError) {
      setError(signUpError.message);
      return;
    }

    startWizard();
    router.push("/wizard/step-1");
    router.refresh();
  }

  return (
    <AuthLayout headline="Empezá a prepararte mejor">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold">Registrarse</h1>
        <p className="text-muted-foreground">
          Creá tu cuenta y analizá tu primer puesto gratis.
        </p>
      </div>

      <form className="mt-8 space-y-4" onSubmit={handleRegister}>
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="fullName">
            Nombre completo
          </label>
          <input
            className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
            id="fullName"
            onChange={(event) => setFullName(event.target.value)}
            required
            type="text"
            value={fullName}
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="email">
            Email
          </label>
          <input
            className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
            id="email"
            onChange={(event) => setEmail(event.target.value)}
            placeholder="tu@email.com"
            required
            type="email"
            value={email}
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="password">
            Password
          </label>
          <input
            className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
            id="password"
            minLength={6}
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </div>

        <label className="flex items-start gap-3 text-sm leading-6">
          <input
            checked={acceptedTos}
            className="mt-1 h-4 w-4 rounded border-input"
            onChange={(event) => setAcceptedTos(event.target.checked)}
            required
            type="checkbox"
          />
          <span>
            Acepto los Términos de Servicio y el procesamiento de mis datos con
            sistemas de IA para generar análisis del servicio.
          </span>
        </label>

        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        <Button
          className="w-full bg-[#0F6E56] hover:bg-[#0d5c48]"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "Creando cuenta..." : "Registrarse"}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        ¿Ya tenés cuenta?{" "}
        <Link className="font-medium text-foreground" href="/login">
          Iniciar sesión
        </Link>
      </p>
    </AuthLayout>
  );
}
