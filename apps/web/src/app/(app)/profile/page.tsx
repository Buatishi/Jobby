"use client";

import { ArrowRight, Loader2 } from "lucide-react";

import { DownloadCVPanel } from "@/components/cv/download-cv-panel";
import { PageBanner } from "@/components/page-banner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { useApiResource } from "@/lib/api/use-api-resource";

type Profile = {
  headline?: string | null;
  summary?: string | null;
  target_role?: string | null;
  target_seniority?: string | null;
  work_modality?: string | null;
  completeness_pct?: number | null;
};

export default function ProfilePage() {
  const { data: profile, error } = useApiResource<Profile>(
    "/api/v1/profiles/me",
    "No se pudo cargar el perfil."
  );

  return (
    <main className="min-h-screen bg-white p-4 pb-14">
      <PageBanner
        description="Revisá la base que usa Jobby para calcular compatibilidad."
        eyebrow="Perfil maestro"
        title="Mi perfil"
      />

      <div className="mt-5 space-y-5">
        <DownloadCVPanel />

        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        {!profile && !error ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Cargando perfil...
          </div>
        ) : null}

        {profile ? (
          <div className="grid gap-5 md:grid-cols-2">
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
                <p className="text-5xl font-semibold italic tracking-[-0.04em] text-brand-green">
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
      </div>
    </main>
  );
}
