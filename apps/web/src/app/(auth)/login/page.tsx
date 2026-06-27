"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Chrome } from "lucide-react";

import { Button } from "@/components/ui/button";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

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
    const supabase = createSupabaseBrowserClient();
    const origin = window.location.origin;
    const { error: oauthError } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${origin}/api/auth/callback`
      }
    });

    if (oauthError) {
      setError(oauthError.message);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-12">
      <div className="space-y-2">
        <p className="text-sm font-medium text-secondary">JobMatch AI</p>
        <h1 className="text-3xl font-semibold">Iniciar sesión</h1>
        <p className="text-muted-foreground">
          Entrá para analizar jobs y revisar tus reportes.
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

        <Button className="w-full" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Ingresando..." : "Iniciar sesión"}
        </Button>
      </form>

      <Button
        className="mt-3 w-full gap-2"
        onClick={handleGoogleLogin}
        type="button"
        variant="ghost"
      >
        <Chrome className="h-4 w-4" />
        Continuar con Google
      </Button>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        ¿No tenés cuenta?{" "}
        <Link className="font-medium text-foreground" href="/register">
          Registrarse
        </Link>
      </p>
    </main>
  );
}
