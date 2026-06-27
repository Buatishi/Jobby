"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  BriefcaseBusiness,
  Check,
  FileSearch,
  Gauge,
  MessagesSquare,
  Sparkles,
  TriangleAlert,
  Wand2
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { scoreColors } from "@/lib/utils/score-colors";

const features = [
  {
    title: "Match Score",
    description:
      "Un score claro de compatibilidad entre tu perfil, experiencia, skills y el puesto.",
    icon: Gauge,
    color: scoreColors.darkGreen
  },
  {
    title: "ATS Analyzer",
    description:
      "Detecta si tu CV pasa filtros automáticos y qué keywords faltan para esa búsqueda.",
    icon: FileSearch,
    color: scoreColors.lightGreen
  },
  {
    title: "Reality Gap",
    description:
      "Compara lo que sabés, lo que tu CV muestra y lo que el job realmente exige.",
    icon: TriangleAlert,
    color: scoreColors.yellow
  },
  {
    title: "CV Optimizer",
    description:
      "Reescribe secciones clave para mejorar representación sin inventar experiencia.",
    icon: Wand2,
    color: scoreColors.red,
    premium: true
  },
  {
    title: "Interview Kit",
    description:
      "Genera preguntas probables, respuestas modelo y un plan de preparación accionable.",
    icon: MessagesSquare,
    color: scoreColors.darkGreen,
    premium: true
  }
];

const freeFeatures = [
  "10 análisis de jobs por mes",
  "Match Score completo",
  "ATS Analyzer básico",
  "Historial de últimos 10 jobs"
];

const premiumFeatures = [
  "Análisis ilimitados",
  "CV Optimizer con IA premium",
  "Interview Kit",
  "Historial completo",
  "Reportes avanzados"
];

type BillingCycle = "monthly" | "yearly";
type ScoreMetric = {
  label: string;
  value: number;
  color: string;
};

const scoreMetrics: ScoreMetric[] = [
  { label: "Skills", value: 92, color: scoreColors.lightGreen },
  { label: "Seniority", value: 84, color: scoreColors.darkGreen },
  { label: "ATS", value: 76, color: scoreColors.yellow },
  { label: "Riesgo", value: 18, color: scoreColors.red }
];

export default function LandingPage() {
  const [billingCycle, setBillingCycle] = useState<BillingCycle>("monthly");
  const monthlyPrice = process.env.NEXT_PUBLIC_PRICE_MONTHLY ?? "[MONTHLY_PRICE]";
  const yearlyPrice = process.env.NEXT_PUBLIC_PRICE_YEARLY ?? "[YEARLY_PRICE]";

  const premiumPrice = useMemo(() => {
    return billingCycle === "monthly"
      ? `$${monthlyPrice}/mes`
      : `$${yearlyPrice}/año`;
  }, [billingCycle, monthlyPrice, yearlyPrice]);

  return (
    <main className="min-h-screen bg-background">
      <nav className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2 font-semibold">
            <span
              className="flex h-8 w-8 items-center justify-center rounded-md text-sm font-bold text-white"
              style={{ backgroundColor: scoreColors.darkGreen }}
            >
              JM
            </span>
            <span>JobMatch AI</span>
          </Link>
          <div className="flex items-center gap-2">
            <Button asChild variant="ghost">
              <Link href="/login">Iniciar sesión</Link>
            </Button>
            <Button asChild>
              <Link href="/register">Registrarse</Link>
            </Button>
          </div>
        </div>
      </nav>

      <section className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-10 px-4 py-16 sm:px-6 lg:grid-cols-[1.08fr_0.92fr]">
        <div className="max-w-3xl space-y-7">
          <Badge variant="outline" className="gap-2">
            <Sparkles className="h-3.5 w-3.5" />
            Match Score antes de aplicar
          </Badge>
          <div className="space-y-5">
            <h1 className="text-4xl font-semibold leading-tight tracking-normal sm:text-5xl lg:text-6xl">
              Sabé exactamente qué tan compatible sos con cada puesto — antes de aplicar
            </h1>
            <p className="max-w-2xl text-lg leading-8 text-muted-foreground">
              JobMatch AI analiza tu perfil, tu CV y la descripción del puesto para
              darte un Match Score de 0 a 100, explicar tus brechas y priorizar qué
              mejorar antes de enviar la aplicación.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button asChild className="h-12 px-6 text-base">
              <Link href="/register">Analizá tu primer job gratis</Link>
            </Button>
            <Button asChild variant="ghost" className="h-12 px-6 text-base">
              <Link href="#pricing">Ver planes</Link>
            </Button>
          </div>
        </div>

        <div className="rounded-lg border border-border p-5 shadow-sm">
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Match Score</p>
                <p className="text-5xl font-semibold">87</p>
              </div>
              <Badge
                style={{
                  borderColor: scoreColors.lightGreen,
                  color: scoreColors.darkGreen
                }}
                variant="outline"
              >
                Alta compatibilidad
              </Badge>
            </div>
            <div className="space-y-3">
              {scoreMetrics.map(({ label, value, color }) => (
                <div key={label} className="space-y-1.5">
                  <div className="flex justify-between text-sm">
                    <span>{label}</span>
                    <span>{value}%</span>
                  </div>
                  <div className="h-2 rounded-md bg-muted">
                    <div
                      className="h-2 rounded-md"
                      style={{ width: `${value}%`, backgroundColor: color }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <p className="text-sm leading-6 text-muted-foreground">
              Tu perfil encaja fuerte en skills técnicas, pero el ATS necesita
              keywords más explícitas para pasar filtros iniciales.
            </p>
          </div>
        </div>
      </section>

      <section className="border-y border-border bg-muted/30 py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="mb-8 max-w-2xl">
            <h2 className="text-3xl font-semibold tracking-normal">Features</h2>
            <p className="mt-3 text-muted-foreground">
              Cinco reportes conectados para decidir mejor, adaptar tu CV y llegar
              con más claridad a cada entrevista.
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <Card
                  key={feature.title}
                  className="min-h-[250px] border-t-4"
                  style={{ borderTopColor: feature.color }}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between gap-3">
                      <Icon className="h-6 w-6" style={{ color: feature.color }} />
                      {feature.premium ? <Badge>Premium</Badge> : null}
                    </div>
                    <CardTitle>{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription>{feature.description}</CardDescription>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      <section className="py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <h2 className="text-3xl font-semibold tracking-normal">Cómo funciona</h2>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {[
              ["1", "Completá tu perfil", "Cargá tu experiencia, skills, CV y LinkedIn."],
              ["2", "Pegá el job", "Usá una URL o el texto completo de la búsqueda."],
              ["3", "Recibí tu reporte", "Leé score, brechas, ATS y próximos pasos."]
            ].map(([step, title, description]) => (
              <div key={step} className="rounded-lg border border-border p-6">
                <div
                  className="mb-5 flex h-10 w-10 items-center justify-center rounded-md font-semibold text-white"
                  style={{ backgroundColor: scoreColors.darkGreen }}
                >
                  {step}
                </div>
                <h3 className="text-lg font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  {description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="pricing" className="border-y border-border bg-muted/30 py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
            <div>
              <h2 className="text-3xl font-semibold tracking-normal">Pricing</h2>
              <p className="mt-3 max-w-xl text-muted-foreground">
                Empezá gratis y pasá a Premium cuando quieras optimizar CVs,
                preparar entrevistas y analizar sin límites.
              </p>
            </div>
            <div className="inline-flex w-fit rounded-lg border border-border bg-background p-1">
              <button
                className="rounded-md px-4 py-2 text-sm font-medium data-[active=true]:bg-primary data-[active=true]:text-primary-foreground"
                data-active={billingCycle === "monthly"}
                onClick={() => setBillingCycle("monthly")}
                type="button"
              >
                Mensual
              </button>
              <button
                className="rounded-md px-4 py-2 text-sm font-medium data-[active=true]:bg-primary data-[active=true]:text-primary-foreground"
                data-active={billingCycle === "yearly"}
                onClick={() => setBillingCycle("yearly")}
                type="button"
              >
                Anual
              </button>
            </div>
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Free</CardTitle>
                <p className="text-3xl font-semibold">$0</p>
                <CardDescription>Para probar el primer flujo completo.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {freeFeatures.map((item) => (
                  <div key={item} className="flex gap-3 text-sm">
                    <Check
                      className="mt-0.5 h-4 w-4 flex-none"
                      style={{ color: scoreColors.lightGreen }}
                    />
                    <span>{item}</span>
                  </div>
                ))}
                <Button asChild className="mt-2 w-full">
                  <Link href="/register">Empezar gratis</Link>
                </Button>
              </CardContent>
            </Card>

            <Card className="border-2" style={{ borderColor: scoreColors.darkGreen }}>
              <CardHeader>
                <div className="flex items-center justify-between gap-3">
                  <CardTitle>Premium</CardTitle>
                  <Badge>Premium</Badge>
                </div>
                <p className="text-3xl font-semibold">{premiumPrice}</p>
                <CardDescription>
                  Para aplicar mejor, más rápido y con reportes avanzados.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {premiumFeatures.map((item) => (
                  <div key={item} className="flex gap-3 text-sm">
                    <Check
                      className="mt-0.5 h-4 w-4 flex-none"
                      style={{ color: scoreColors.darkGreen }}
                    />
                    <span>{item}</span>
                  </div>
                ))}
                <Button asChild className="mt-2 w-full">
                  <Link href="/register">Analizá tu primer job gratis</Link>
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      <section className="py-16">
        <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 px-4 sm:px-6 md:flex-row md:items-center">
          <div>
            <p className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <BriefcaseBusiness className="h-4 w-4" />
              JobMatch AI
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-normal">
              Empezá gratis hoy
            </h2>
          </div>
          <Button asChild className="h-12 px-6 text-base">
            <Link href="/register">Empezá gratis hoy</Link>
          </Button>
        </div>
      </section>
    </main>
  );
}
