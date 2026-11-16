"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { validateNewPassword } from "@/lib/auth/password";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { PasswordInput } from "@/src/components/auth/PasswordInput";

const inputClassName =
  "h-12 w-full rounded-full border border-brand-line bg-white px-5 text-sm outline-none focus-visible:border-brand-green focus-visible:ring-2 focus-visible:ring-brand-green/25";

export function ChangePasswordCard() {
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaved(false);

    const validationError = validateNewPassword(password, confirmation);
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSaving(true);
    setError(null);
    try {
      const supabase = createSupabaseBrowserClient();
      const { error: updateError } = await supabase.auth.updateUser({ password });
      if (updateError) {
        setError(updateError.message);
        return;
      }
      setPassword("");
      setConfirmation("");
      setSaved(true);
    } catch (changeError) {
      setError(
        changeError instanceof Error
          ? changeError.message
          : "No pudimos cambiar la contraseña. Probá de nuevo."
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Card className="md:col-span-2">
      <CardHeader>
        <CardTitle>Cambiar contraseña</CardTitle>
        <CardDescription>Elegí una nueva contraseña para tu cuenta.</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={changePassword}>
          <PasswordInput
            aria-label="Nueva contraseña"
            autoComplete="new-password"
            className={inputClassName}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Nueva contraseña (mínimo 8 caracteres)"
            value={password}
          />
          <PasswordInput
            aria-label="Repetir contraseña"
            autoComplete="new-password"
            className={inputClassName}
            onChange={(event) => setConfirmation(event.target.value)}
            placeholder="Repetí la contraseña"
            value={confirmation}
          />
          {error ? <p className="text-sm font-medium text-destructive">{error}</p> : null}
          {saved ? (
            <p className="text-sm font-medium text-brand-green">Contraseña actualizada.</p>
          ) : null}
          <Button isLoading={isSaving} type="submit">
            Guardar contraseña
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}