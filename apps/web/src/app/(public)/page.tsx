"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  ArrowRight,
  BadgeCheck,
  FileSearch,
  Gauge,
  Lock,
  Menu,
  MessageSquareText,
  TrendingUp,
  Wand2,
  X
} from "lucide-react";

import { MatchScoreCard } from "@/components/match-score-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";

type BillingCycle = "monthly" | "yearly";

const navLinks = [
  { href: "#features", label: "Funciones" },
  { href: "#how-it-works", label: "Cómo funciona" },
  { href: "#pricing", label: "Precios" },
  { href: "#demo", label: "Vista previa" }
];

const features = [
  {
    title: "Match Score",
    description: "Compatibilidad numérica 0-100 entre tu perfil y el puesto.",
    icon: Gauge
  },
  {
    title: "ATS Analyzer",
    description: "Verificá si tu CV pasa filtros automáticos de reclutamiento.",
    icon: FileSearch
  },
  {
    title: "Reality Gap",
    description: "Detectá incoherencias entre tu CV, LinkedIn y perfil real.",
    icon: BadgeCheck
  },
  {
    title: "CV Optimizer",
    description: "Reescribí tu CV con IA para el puesto específico.",
    icon: Wand2,
    premium: true
  },
  {
    title: "Interview Kit",
    description: "Kit completo para preparación previa a la entrevista.",
    icon: MessageSquareText,
    premium: true
  }
];

const steps = [
  {
    title: "Analizá tu CV",
    description: "Pegá una URL, subí el puesto y elegí contra qué rol competir."
  },
  {
    title: "Descubrí gaps",
    description: "Verificá si tu CV pasa ATS y dónde faltan señales concretas."
  },
  {
    title: "Analizá un puesto",
    description: "Conectá tu perfil con recomendaciones accionables."
  }
];

const freeFeatures = [
  "10 análisis de puestos por mes",
  "Match Score completo",
  "ATS Analyzer básico",
  "Historial de últimos 10 puestos"
];

const premiumFeatures = [
  "Análisis ilimitados",
  "CV Optimizer con IA",
  "Interview Kit premium",
  "Historial completo",
  "Recomendaciones priorizadas"
];

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 }
};

export default function LandingPage() {
  const [billingCycle, setBillingCycle] = useState<BillingCycle>("monthly");
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const monthlyPrice = process.env.NEXT_PUBLIC_PRICE_MONTHLY ?? "0";
  const yearlyPrice = process.env.NEXT_PUBLIC_PRICE_YEARLY ?? "0";

  const premiumPrice = useMemo(() => {
    return billingCycle === "monthly"
      ? `$${monthlyPrice}/mes`
      : `$${yearlyPrice}/año`;
  }, [billingCycle, monthlyPrice, yearlyPrice]);

  return (
    <main className="min-h-screen bg-white text-foreground">
      <nav className="sticky top-0 z-50 border-b border-black/5 bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8">
          <Link className="flex items-center gap-2 text-xl font-black tracking-tight" href="/">
            <span className="relative flex h-8 w-8 items-center justify-center rounded-xl bg-brand-green text-white shadow-sm">
              J
            </span>
            Jobby
          </Link>

          <div className="hidden items-center gap-8 md:flex">
            {navLinks.map((link) => (
              <Link
                className="text-sm font-semibold text-black/75 transition hover:text-brand-green"
                href={link.href}
                key={link.href}
              >
                {link.label}
              </Link>
            ))}
          </div>

          <div className="hidden items-center gap-3 md:flex">
            <Button
              asChild
              className="h-10 rounded-lg bg-brand-green px-5 text-white shadow-sm hover:bg-[#006d52]"
            >
              <Link href="/register">Empezar gratis</Link>
            </Button>
            <Button asChild className="h-10 px-3 font-semibold" variant="ghost">
              <Link href="/login">Iniciar sesión</Link>
            </Button>
          </div>

          <button
            aria-label="Abrir menú"
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-black/10 hover:bg-muted md:hidden"
            onClick={() => setIsMenuOpen((current) => !current)}
            type="button"
          >
            {isMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {isMenuOpen ? (
          <div className="border-t border-black/5 bg-white px-5 py-4 md:hidden">
            <div className="flex flex-col gap-3">
              {navLinks.map((link) => (
                <Link
                  className="rounded-lg px-2 py-2 text-sm font-semibold text-muted-foreground hover:bg-muted hover:text-foreground"
                  href={link.href}
                  key={link.href}
                  onClick={() => setIsMenuOpen(false)}
                >
                  {link.label}
                </Link>
              ))}
              <Button asChild variant="ghost">
                <Link href="/login">Iniciar sesión</Link>
              </Button>
              <Button asChild className="bg-brand-green text-white hover:bg-[#006d52]">
                <Link href="/register">Empezar gratis</Link>
              </Button>
            </div>
          </div>
        ) : null}
      </nav>

      <section className="relative overflow-hidden bg-white" id="demo">
        <div className="pointer-events-none absolute right-12 top-16 hidden h-80 w-80 rounded-full bg-brand-green-light blur-2xl lg:block" />
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-5 py-16 sm:px-8 md:py-20 lg:grid-cols-[0.96fr_1.04fr]">
          <motion.div
            animate="visible"
            className="relative z-10"
            initial="hidden"
            transition={{ staggerChildren: 0.1 }}
          >
            <motion.h1
              className="max-w-xl text-4xl font-black leading-[0.98] tracking-[-0.02em] text-black sm:text-5xl lg:text-6xl"
              transition={{ duration: 0.5 }}
              variants={fadeUp}
            >
              Dejá de postularte a ciegas. Descubrí tu match laboral perfecto.
            </motion.h1>
            <motion.p
              className="mt-6 max-w-lg text-base font-medium leading-7 text-black/70"
              transition={{ duration: 0.5 }}
              variants={fadeUp}
            >
              Nuestra IA analiza tu CV frente a cualquier oferta de empleo para
              darte una puntuación de compatibilidad exacta e identificar brechas
              clave instantáneamente.
            </motion.p>
            <motion.div
              className="mt-7 flex flex-col gap-3 sm:flex-row"
              transition={{ duration: 0.5 }}
              variants={fadeUp}
            >
              <Button
                asChild
                className="h-12 rounded-xl bg-brand-green px-6 text-base font-bold text-white shadow-sm hover:bg-[#006d52]"
              >
                <Link href="/register">Analizá tu primer puesto gratis</Link>
              </Button>
            </motion.div>
          </motion.div>

          <motion.div
            animate={{ opacity: 1, y: 0 }}
            className="relative flex min-h-[360px] items-center justify-center"
            initial={{ opacity: 0, y: 28 }}
            transition={{ delay: 0.25, duration: 0.6 }}
          >
            <div className="absolute right-4 top-0 h-80 w-80 rounded-full bg-brand-green-light" />
            <MatchScoreCard className="relative z-10 w-full max-w-lg scale-100 sm:scale-[1.08] lg:scale-[1.2]" />
          </motion.div>
        </div>
      </section>

      <section className="bg-white py-8" id="features">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-5">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <Card
                  className="group rounded-xl border-black/10 bg-brand-green-light/80 shadow-none transition-shadow hover:shadow-md"
                  key={feature.title}
                >
                  <CardHeader className="space-y-3 p-5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex h-9 w-9 items-center justify-center rounded-full border border-brand-green/20 bg-white/60 text-brand-green">
                        <Icon className="h-4 w-4" />
                      </div>
                      {feature.premium ? (
                        <Badge className="gap-1 rounded-full bg-brand-green px-2 py-0.5 text-[10px] text-white">
                          <Lock className="h-2.5 w-2.5" />
                          Premium
                        </Badge>
                      ) : null}
                    </div>
                    <CardTitle className="text-base font-black">
                      {feature.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="px-5 pb-5 pt-0">
                    <CardDescription className="text-xs font-semibold leading-5 text-black/70">
                      {feature.description}
                    </CardDescription>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      <section className="border-y border-black/5 bg-bg-dashboard py-9" id="how-it-works">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <h2 className="text-2xl font-black tracking-tight">Cómo funciona</h2>
          <div className="mt-7 grid gap-6 md:grid-cols-[1fr_auto_1fr_auto_1fr] md:items-start">
            {steps.map((step, index) => (
              <div className="contents" key={step.title}>
                <div className="flex gap-4">
                  <span className="text-5xl font-black leading-none text-black">
                    {index + 1}
                  </span>
                  <div>
                    <h3 className="text-base font-black">{step.title}</h3>
                    <p className="mt-1 max-w-xs text-xs font-medium leading-5 text-black/65">
                      {step.description}
                    </p>
                  </div>
                </div>
                {index < steps.length - 1 ? (
                  <div className="hidden pt-5 text-brand-green md:block">
                    <ArrowRight className="h-9 w-9 stroke-[1.5]" />
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="sr-only" id="pricing" aria-label="Precios">
        <button
          data-active={billingCycle === "monthly"}
          onClick={() => setBillingCycle("monthly")}
          type="button"
        >
          Mensual
        </button>
        <button
          data-active={billingCycle === "yearly"}
          onClick={() => setBillingCycle("yearly")}
          type="button"
        >
          Anual
        </button>
        <span>{premiumPrice}</span>
        {freeFeatures.map((item) => (
          <span key={item}>{item}</span>
        ))}
        {premiumFeatures.map((item) => (
          <span key={item}>{item}</span>
        ))}
      </section>

      <section className="bg-brand-green px-5 py-12 text-white sm:px-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center text-center">
          <TrendingUp className="h-7 w-7" />
          <h2 className="mt-5 text-3xl font-black tracking-tight md:text-4xl">
            Empezá a prepararte mejor
          </h2>
          <Button
            asChild
            className="mt-6 rounded-lg bg-white px-6 font-black text-brand-green hover:bg-white/90"
          >
            <Link href="/register">Empezar gratis</Link>
          </Button>
        </div>
      </section>

      <footer className="bg-brand-green px-5 pb-8 text-white sm:px-8">
        <div className="mx-auto flex max-w-6xl flex-col gap-5 border-t border-white/15 pt-6 text-xs sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-base font-black">Jobby</p>
            <p className="mt-1 text-white/75">
              IA para entender mejor cada postulación antes de aplicar.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-5 text-white/80">
            <Link className="hover:text-white" href="/privacy">
              Privacidad
            </Link>
            <Link className="hover:text-white" href="/terms">
              Términos
            </Link>
            <span>© 2026 Jobby</span>
          </div>
        </div>
      </footer>
    </main>
  );
}
