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
  { href: "#features", label: "Features" },
  { href: "#how-it-works", label: "How-It-Works" },
  { href: "#pricing", label: "Pricing" },
  { href: "#demo", label: "Demo" }
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
    description: "Pegá un URL, subí el puesto y elegí contra qué rol competir."
  },
  {
    title: "Descubrí gaps",
    description: "Verificá si tu CV pasa ATS y dónde faltan señales concretas."
  },
  {
    title: "Analizá un job",
    description: "Conectá tu perfil con recomendaciones accionables."
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
  "CV Optimizer con IA",
  "Interview Kit premium",
  "Historial completo",
  "Recomendaciones priorizadas"
];

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 }
};

const scoreRows = [
  { label: "Skills técnicas", value: 92, color: "bg-brand-accent" },
  { label: "Seniority", value: 84, color: "bg-brand-green" },
  { label: "ATS", value: 76, color: "bg-[#DDAA20]" },
  { label: "Brechas críticas", value: 18, color: "bg-[#D94B42]" }
];

const logos = ["Hooli", "pied piper", "IBM", "initech", "INITECH", "initech"];

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
              <Link href="/register">Start Free</Link>
            </Button>
            <Button asChild className="h-10 px-3 font-semibold" variant="ghost">
              <Link href="/login">Login</Link>
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
                <Link href="/login">Login</Link>
              </Button>
              <Button asChild className="bg-brand-green text-white hover:bg-[#006d52]">
                <Link href="/register">Start Free</Link>
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
              Deja de postularte a ciegas. Descubre tu match laboral perfecto.
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
                <Link href="/register">Analizá tu primer job gratis</Link>
              </Button>
            </motion.div>
          </motion.div>

          <motion.div
            animate={{ opacity: 1, y: 0 }}
            className="relative min-h-[360px]"
            initial={{ opacity: 0, y: 28 }}
            transition={{ delay: 0.25, duration: 0.6 }}
          >
            <div className="absolute right-4 top-0 h-80 w-80 rounded-full bg-brand-green-light" />
            <Card className="absolute left-0 top-7 z-10 w-full max-w-md rounded-2xl border-black/10 bg-white p-0 shadow-[0_24px_70px_rgba(15,23,42,0.14)] sm:left-4">
              <CardHeader className="border-b border-black/5 p-6">
                <div className="flex items-start justify-between">
                  <div>
                    <CardDescription className="text-xs font-semibold">
                      Match Score
                    </CardDescription>
                    <CardTitle className="mt-1 text-5xl font-black leading-none">
                      87
                    </CardTitle>
                  </div>
                  <Badge className="rounded-full bg-brand-green-light px-3 py-1 text-[11px] font-bold text-brand-green">
                    Muy alto
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 p-6">
                {scoreRows.map((row) => (
                  <div className="space-y-1.5" key={row.label}>
                    <div className="flex justify-between text-xs font-bold text-black/80">
                      <span>{row.label}</span>
                      <span>{row.value}%</span>
                    </div>
                    <div className="h-2.5 overflow-hidden rounded-full bg-[#E8EAED]">
                      <div
                        className={`h-full rounded-full ${row.color}`}
                        style={{ width: `${row.value}%` }}
                      />
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <div className="absolute bottom-8 right-[-3.5rem] z-20 hidden h-56 w-32 sm:block">
              <svg
                aria-hidden="true"
                className="h-full w-full drop-shadow-[0_10px_15px_rgba(0,0,0,0.05)]"
                fill="none"
                viewBox="0 0 128 224"
              >
                <defs>
                  <linearGradient id="personSkin" x1="55" x2="82" y1="23" y2="72">
                    <stop stopColor="#F0C9AD" />
                    <stop offset="1" stopColor="#C58B70" />
                  </linearGradient>
                  <linearGradient id="personJacket" x1="31" x2="83" y1="80" y2="146">
                    <stop stopColor="#0A9273" />
                    <stop offset="0.58" stopColor="#007A5E" />
                    <stop offset="1" stopColor="#005F4D" />
                  </linearGradient>
                  <linearGradient id="personPants" x1="39" x2="81" y1="139" y2="217">
                    <stop stopColor="#4B5563" />
                    <stop offset="1" stopColor="#1F2937" />
                  </linearGradient>
                  <linearGradient id="personHair" x1="49" x2="82" y1="17" y2="51">
                    <stop stopColor="#372A24" />
                    <stop offset="1" stopColor="#17110F" />
                  </linearGradient>
                  <radialGradient id="personCheek" cx="0" cy="0" r="1" gradientTransform="matrix(9 0 0 7 75 52)" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#D88978" stopOpacity="0.55" />
                    <stop offset="1" stopColor="#D88978" stopOpacity="0" />
                  </radialGradient>
                </defs>

                <ellipse cx="66" cy="218" fill="#0F172A" fillOpacity="0.08" rx="43" ry="5" />

                <path d="M48 67C45 75 43 85 43 96H74C75 85 73 76 69 67H48Z" fill="#F6FAF8" />
                <path
                  d="M36 78C51 68 73 69 86 82C92 103 88 123 78 143C64 150 43 147 27 138C28 115 30 94 36 78Z"
                  fill="url(#personJacket)"
                />
                <path d="M51 75C56 95 58 116 58 140" stroke="#005F4D" strokeLinecap="round" strokeOpacity="0.55" strokeWidth="1.25" />
                <path d="M40 91C45 101 48 115 49 134M79 88C74 101 70 117 68 137" stroke="#21A486" strokeLinecap="round" strokeOpacity="0.5" strokeWidth="1" />
                <path d="M48 82L57 108L64 82" stroke="#ECF7F2" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                <path d="M60 83L65 110L72 84" stroke="#005F4D" strokeLinecap="round" strokeOpacity="0.55" strokeWidth="1.2" />

                <path d="M84 91C94 104 101 118 104 132" stroke="#007A5E" strokeLinecap="round" strokeWidth="12" />
                <path d="M104 132C108 144 113 153 119 160" stroke="url(#personSkin)" strokeLinecap="round" strokeWidth="8" />

                <rect fill="#4B5563" height="34" rx="7" transform="rotate(8 93 150)" width="39" x="93" y="150" />
                <rect fill="#6B7280" height="8" opacity="0.42" rx="3" transform="rotate(8 99 158)" width="29" x="99" y="158" />
                <path d="M105 151C106 144 119 144 120 153" stroke="#374151" strokeLinecap="round" strokeWidth="1.8" />
                <path d="M100 164H126" stroke="#CBD5E1" strokeLinecap="round" strokeOpacity="0.55" />

                <path d="M40 138C41 161 37 183 30 211" stroke="url(#personPants)" strokeLinecap="round" strokeWidth="16" />
                <path d="M67 140C77 161 85 183 92 211" stroke="url(#personPants)" strokeLinecap="round" strokeWidth="16" />
                <path d="M36 163C41 167 47 168 53 166" stroke="#6B7280" strokeLinecap="round" strokeOpacity="0.48" />
                <path d="M76 166C82 168 87 166 91 163" stroke="#6B7280" strokeLinecap="round" strokeOpacity="0.48" />
                <path d="M20 217H40" stroke="#1F2937" strokeLinecap="round" strokeWidth="7" />
                <path d="M85 217H107" stroke="#1F2937" strokeLinecap="round" strokeWidth="7" />

                <path d="M56 58C56 67 52 72 47 76C55 84 69 83 77 76C70 72 68 66 70 57L56 58Z" fill="url(#personSkin)" />
                <path d="M49 33C50 21 58 15 69 16C81 17 88 25 87 38L84 50C82 62 74 69 65 69C55 68 49 60 48 48L49 33Z" fill="url(#personSkin)" />
                <path d="M49 37C52 23 61 18 74 20C82 22 87 28 89 37C81 36 72 32 65 26C62 32 55 36 49 37Z" fill="url(#personHair)" />
                <path d="M55 22C61 19 70 18 78 23M52 30C59 28 66 29 75 33" stroke="#5B4338" strokeLinecap="round" strokeOpacity="0.55" strokeWidth="1.2" />
                <ellipse cx="75" cy="47" fill="url(#personCheek)" rx="9" ry="7" />
                <circle cx="62" cy="46" fill="#17110F" r="1.25" />
                <circle cx="73" cy="46" fill="#17110F" r="1.25" />
                <path d="M68 49C66 52 66 53 69 54" stroke="#8C5E4E" strokeLinecap="round" strokeWidth="1.2" />
                <path d="M62 59C66 62 73 61 77 57" stroke="#7C3F38" strokeLinecap="round" strokeWidth="1.5" />
                <path d="M58 42C63 40 68 40 72 42" stroke="#3A2C27" strokeLinecap="round" strokeWidth="1.2" />
                <path d="M78 43C81 42 84 42 86 44" stroke="#3A2C27" strokeLinecap="round" strokeWidth="1.1" />
                <path d="M88 31C94 40 93 51 84 62" stroke="#2A211D" strokeLinecap="round" strokeOpacity="0.45" strokeWidth="2" />
                <path d="M49 39C43 48 45 59 54 66" stroke="#2A211D" strokeLinecap="round" strokeOpacity="0.4" strokeWidth="1.8" />

                <g>
                  <circle cx="112" cy="37" fill="#007a5e" r="10" />
                  <path
                    d="M107.5 37.4L111 41L117.5 33"
                    stroke="white"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                  />
                </g>
              </svg>
            </div>
          </motion.div>
        </div>
      </section>

      <section className="bg-white pb-9">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <p className="text-center text-[11px] font-bold uppercase tracking-[0.22em] text-black/45">
            Más de 12.000 análisis realizados
          </p>
          <div className="mt-5 flex flex-wrap items-center justify-center gap-x-10 gap-y-4 text-2xl font-black text-black/80">
            {logos.map((logo, index) => (
              <span
                className="grayscale opacity-80 transition hover:opacity-100"
                key={`${logo}-${index}`}
              >
                {logo}
              </span>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-white py-8" id="features">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-5">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <Card
                  className="group rounded-xl border-black/10 bg-brand-green-light/80 shadow-none transition hover:-translate-y-1 hover:shadow-md"
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
          <h2 className="text-2xl font-black tracking-tight">Cómo Funciona</h2>
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

      <section className="sr-only" id="pricing" aria-label="Pricing">
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
            Start preparing better
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
