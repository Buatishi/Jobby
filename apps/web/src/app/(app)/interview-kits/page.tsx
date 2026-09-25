"use client";

import { useMemo } from "react";
import Link from "next/link";
import { CalendarDays, Plus } from "lucide-react";

import { PremiumGate } from "@/components/premium-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { useApiResource } from "@/lib/api/use-api-resource";
import { planOf } from "@/lib/auth/permissions";
import { useCurrentUser } from "@/lib/auth/use-current-user";
import { cn } from "@/lib/utils";

type KitStatus = "pending" | "processing" | "done" | "failed";

type InterviewKitListItem = {
  id: string;
  title: string | null;
  status: KitStatus;
  error_msg: string | null;
  prep_notes: Record<string, unknown> | null;
  created_at: string | null;
};

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asText(value: unknown, fallback: string) {
  return typeof value === "string" && value.trim().length > 0
    ? value
    : fallback;
}

function statusLabel(status: KitStatus) {
  const labels: Record<KitStatus, string> = {
    pending: "Pendiente",
    processing: "Generando",
    done: "Listo",
    failed: "Falló"
  };
  return labels[status] ?? status;
}

function statusClassName(status: KitStatus) {
  return cn(
    status === "done" && "border-[#0F6E56] text-[#0F6E56]",
    status === "processing" && "border-[#F0A500] text-[#8A5F00]",
    status === "pending" && "text-muted-foreground",
    status === "failed" && "border-[#E24B4A] text-[#E24B4A]"
  );
}

export default function InterviewKitsPage() {
  const {
    data: kits,
    error,
    loading
  } = useApiResource<InterviewKitListItem[]>(
    "/api/v1/interview-kits",
    "No se pudieron cargar los kits."
  );
  // Sin plan todavía (perfil cargando) no se muestra ni el botón ni el aviso premium.
  const plan = planOf(useCurrentUser());

  const sortedKits = useMemo(
    () =>
      [...(kits ?? [])].sort((left, right) =>
        String(right.created_at ?? "").localeCompare(String(left.created_at ?? ""))
      ),
    [kits]
  );

  return (
    <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:py-8">
      <div className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="text-sm font-medium text-muted-foreground">
            Interview Kits
          </p>
          <h1 className="mt-1 text-3xl font-semibold tracking-normal">
            Preparación por entrevista
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Guardá kits personalizados por puesto, empresa y entrevistador.
          </p>
        </div>
        {plan === "premium" ? (
          <Button asChild>
            <Link href="/interview-kits/new">
              <Plus className="mr-2 h-4 w-4" />
              Nuevo Kit
            </Link>
          </Button>
        ) : null}
      </div>

      {plan === "free" ? <PremiumGate className="mb-6" /> : null}

      {error ? (
        <Card>
          <CardContent className="pt-6 text-sm text-destructive">
            {error}
          </CardContent>
        </Card>
      ) : null}

      {loading ? (
        <Card>
          <CardContent className="pt-6 text-sm text-muted-foreground">
            Cargando kits...
          </CardContent>
        </Card>
      ) : null}

      {!loading && !error && sortedKits.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No hay kits todavía</CardTitle>
            <CardDescription>
              Cuando generes tu primer kit, va a aparecer en esta lista.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {sortedKits.map((kit) => {
          const notes = asRecord(kit.prep_notes);
          const companyData = asRecord(notes.company_data);
          const interviewerData = asRecord(notes.interviewer_data);
          const company = asText(
            companyData.company_name,
            asText(notes.company_name, "Empresa sin identificar")
          );
          const interviewer = asText(
            interviewerData.full_name,
            asText(notes.interviewer_name, "Entrevistador no definido")
          );
          const date = kit.created_at
            ? new Intl.DateTimeFormat("es-AR", {
                dateStyle: "medium"
              }).format(new Date(kit.created_at))
            : "Sin fecha";

          return (
            <Card key={kit.id}>
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle className="leading-6">
                      {kit.title ?? company}
                    </CardTitle>
                    <CardDescription className="mt-2">
                      {company} · {interviewer}
                    </CardDescription>
                  </div>
                  <Badge
                    className={statusClassName(kit.status)}
                    variant="outline"
                  >
                    {statusLabel(kit.status)}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <CalendarDays className="h-4 w-4" />
                  {date}
                </div>
                {kit.error_msg ? (
                  <p className="mt-3 text-sm text-destructive">{kit.error_msg}</p>
                ) : null}
                <Button asChild className="mt-5 w-full" variant="secondary">
                  <Link href={`/interview-kits/${kit.id}`}>Ver kit</Link>
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </section>
    </main>
  );
}
