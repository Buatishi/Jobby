"use client";

import { useEffect, useState } from "react";
import { ArrowRight, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";

type Profile = {
  headline?: string | null;
  summary?: string | null;
  target_role?: string | null;
  target_seniority?: string | null;
  work_modality?: string | null;
  completeness_pct?: number | null;
};

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient<Profile>("/api/v1/profiles/me")
      .then(setProfile)
      .catch((requestError: unknown) => {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "No se pudo cargar el perfil."
        );
      });
  }, []);

  return (
    <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6">
        <p className="text-sm font-medium text-[#0F6E56]">Perfil maestro</p>
        <h1 className="text-3xl font-semibold">Mi perfil</h1>
        <p className="mt-2 text-muted-foreground">
          Revisá la base que usa Jobby para calcular compatibilidad.
        </p>
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {!profile && !error ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Cargando perfil...
        </div>
      ) : null}

      {profile ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Objetivo</CardTitle>
              <CardDescription>
                Campos principales para calibrar el Match Score.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p>
                <span className="font-medium">Headline:</span>{" "}
                {profile.headline || "Pendiente"}
              </p>
              <p>
                <span className="font-medium">Rol objetivo:</span>{" "}
                {profile.target_role || "Pendiente"}
              </p>
              <p>
                <span className="font-medium">Seniority:</span>{" "}
                {profile.target_seniority || "Pendiente"}
              </p>
              <p>
                <span className="font-medium">Modalidad:</span>{" "}
                {profile.work_modality || "Pendiente"}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Completitud</CardTitle>
              <CardDescription>
                Cuanto más completo esté, mejores reportes genera.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-5xl font-semibold text-[#0F6E56]">
                {profile.completeness_pct ?? 0}%
              </p>
              <Button asChild className="mt-5">
                <a href="/wizard/step-1">
                  Mejorar perfil
                  <ArrowRight className="ml-2 h-4 w-4" />
                </a>
              </Button>
            </CardContent>
          </Card>

          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle>Bio</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-6 text-muted-foreground">
                {profile.summary || "Todavía no agregaste una bio."}
              </p>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </main>
  );
}
