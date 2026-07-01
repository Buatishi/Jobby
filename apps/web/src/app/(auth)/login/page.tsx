"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Chrome } from "lucide-react";

import { Button } from "@/components/ui/button";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { AuthLayout } from "@/src/components/auth/AuthLayout";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isOAuthLoading, setIsOAuthLoading] = useState(false);

  useEffect(() => {
    const oauthError = new URLSearchParams(window.location.search).get("error");
    if (oauthError) {
      setError(oauthError);
    }
  }, []);

  async function handleEmailLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    const supabase = createSupabaseBrowserClient();

    const { error: loginError } = await supabase.auth.signInWithPassword({
      email,
      password
    });

    setIsSubmitting(false);

    if (loginError) {
      setError(loginError.message);
      return;
    }

    router.push("/dashboard");
    router.refresh();
  }

  async function handleGoogleLogin() {
    setError(null);
    setIsOAuthLoading(true);
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
      setIsOAuthLoading(false);
      setError(oauthError.message);
    }
  }

  return (
    <AuthLayout headline="Tu próxima entrevista empieza acá">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold">Iniciar sesión</h1>
        <p className="text-muted-foreground">
          Entrá para analizar puestos y revisar tus reportes.
        </p>
      </div>

      <form className="mt-8 space-y-4" onSubmit={handleEmailLogin}>
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

        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        <Button
          className="w-full bg-[#0F6E56] hover:bg-[#0d5c48]"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "Ingresando..." : "Iniciar sesión"}
        </Button>
      </form>

      <Button
        className="mt-3 w-full gap-2"
        disabled={isOAuthLoading}
        onClick={handleGoogleLogin}
        type="button"
        variant="ghost"
      >
        <Chrome className="h-4 w-4" />
        {isOAuthLoading ? "Abriendo Google..." : "Continuar con Google"}
      </Button>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        ¿No tenés cuenta?{" "}
        <Link className="font-medium text-foreground" href="/register">
          Registrarse
        </Link>
      </p>
    </AuthLayout>
  );
}
