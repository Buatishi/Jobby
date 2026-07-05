"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { motion, useInView } from "framer-motion";
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

import { LanguageToggle } from "@/components/language-toggle";
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
import { useI18n } from "@/lib/i18n/provider";
import { cn } from "@/lib/utils";
import { DemoSection } from "@/src/components/landing/DemoSection";
import { ProblemSection } from "@/src/components/landing/ProblemSection";

type BillingCycle = "monthly" | "yearly";

const navLinks = [
  { href: "#features", labelKey: "landing.navFeatures" },
  { href: "#how-it-works", labelKey: "landing.navHow" },
  { href: "#pricing", labelKey: "landing.navPricing" },
  { href: "#demo", labelKey: "landing.navDemo" }
];

const features = [
  {
    titleKey: "landing.features.matchTitle",
    descriptionKey: "landing.features.matchDescription",
    icon: Gauge
  },
  {
    titleKey: "landing.features.atsTitle",
    descriptionKey: "landing.features.atsDescription",
    icon: FileSearch
  },
  {
    titleKey: "landing.features.gapTitle",
    descriptionKey: "landing.features.gapDescription",
    icon: BadgeCheck
  },
  {
    titleKey: "landing.features.optimizerTitle",
    descriptionKey: "landing.features.optimizerDescription",
    icon: Wand2,
    premium: true
  },
  {
    titleKey: "landing.features.kitTitle",
    descriptionKey: "landing.features.kitDescription",
    icon: MessageSquareText,
    premium: true
  }
];

const steps = [
  {
    titleKey: "landing.steps.oneTitle",
    descriptionKey: "landing.steps.oneDescription"
  },
  {
    titleKey: "landing.steps.twoTitle",
    descriptionKey: "landing.steps.twoDescription"
  },
  {
    titleKey: "landing.steps.threeTitle",
    descriptionKey: "landing.steps.threeDescription"
  }
];

const freeFeatures = [
  "landing.freeFeatures.one",
  "landing.freeFeatures.two",
  "landing.freeFeatures.three",
  "landing.freeFeatures.four"
];

const premiumFeatures = [
  "landing.premiumFeatures.one",
  "landing.premiumFeatures.two",
  "landing.premiumFeatures.three",
  "landing.premiumFeatures.four",
  "landing.premiumFeatures.five"
];

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 }
};

const primaryButtonClass =
  "transition-transform duration-150 hover:scale-[1.02] active:scale-[0.98]";

function RevealSection({
  children,
  className,
  id
}: {
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  const ref = useRef<HTMLElement>(null);
  const isInView = useInView(ref, { amount: 0.2, once: true });

  return (
    <motion.section
      animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
      className={className}
      id={id}
      initial={{ opacity: 0, y: 20 }}
      ref={ref}
      transition={{ duration: 0.3, ease: "easeOut" }}
    >
      {children}
    </motion.section>
  );
}

function RevealItem({
  children,
  delay = 0
}: {
  children: ReactNode;
  delay?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { amount: 0.2, once: true });

  return (
    <motion.div
      animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
      initial={{ opacity: 0, y: 20 }}
      ref={ref}
      transition={{ delay, duration: 0.3, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}

export default function LandingPage() {
  const { t } = useI18n();
  const [billingCycle, setBillingCycle] = useState<BillingCycle>("monthly");
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [hasScrolled, setHasScrolled] = useState(false);
  const monthlyPrice = process.env.NEXT_PUBLIC_PRICE_MONTHLY ?? "0";
  const yearlyPrice = process.env.NEXT_PUBLIC_PRICE_YEARLY ?? "0";

  const premiumPrice = useMemo(() => {
    return billingCycle === "monthly"
      ? `$${monthlyPrice}/${t("landing.perMonth")}`
      : `$${yearlyPrice}/${t("landing.perYear")}`;
  }, [billingCycle, monthlyPrice, t, yearlyPrice]);

  useEffect(() => {
    function handleScroll() {
      setHasScrolled(window.scrollY > 20);
    }

    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <main className="min-h-screen bg-white text-foreground" id="top">
      <nav
        className={cn(
          "sticky top-0 z-50 border-b border-black/5 bg-white/90 backdrop-blur-xl transition-shadow duration-200",
          hasScrolled && "shadow-[0_12px_30px_rgba(15,23,42,0.06)]"
        )}
      >
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8">
          <a
            className="flex items-center gap-2 text-xl font-black tracking-tight"
            href="#top"
          >
            <span className="relative flex h-8 w-8 items-center justify-center rounded-xl bg-brand-green text-white shadow-sm">
              J
            </span>
            Jobby
          </a>

          <div className="hidden items-center gap-8 md:flex">
            {navLinks.map((link) => (
              <Link
                className="text-sm font-semibold text-black/75 transition hover:text-brand-green"
                href={link.href}
                key={link.href}
              >
                {t(link.labelKey)}
              </Link>
            ))}
          </div>

          <div className="hidden items-center gap-3 md:flex">
            <LanguageToggle />
            <Button
              asChild
              className={cn(
                "h-10 rounded-lg bg-brand-green px-5 text-white shadow-sm hover:bg-[#006d52]",
                primaryButtonClass
              )}
            >
              <Link href="/register">{t("common.startFree")}</Link>
            </Button>
            <Button asChild className="h-10 px-3 font-semibold" variant="ghost">
              <Link href="/login">{t("common.login")}</Link>
            </Button>
          </div>

          <button
            aria-label={t("common.openMenu")}
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
                  {t(link.labelKey)}
                </Link>
              ))}
              <LanguageToggle className="w-fit" />
              <Button asChild variant="ghost">
                <Link href="/login">{t("common.login")}</Link>
              </Button>
              <Button
                asChild
                className={cn(
                  "bg-brand-green text-white hover:bg-[#006d52]",
                  primaryButtonClass
                )}
              >
                <Link href="/register">{t("common.startFree")}</Link>
              </Button>
            </div>
          </div>
        ) : null}
      </nav>

      <section className="relative overflow-hidden bg-white">
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
              transition={{ duration: 0.3 }}
              variants={fadeUp}
            >
              {t("landing.heroTitle")}
            </motion.h1>
            <motion.p
              className="mt-6 max-w-lg text-base font-medium leading-7 text-black/70"
              transition={{ duration: 0.3 }}
              variants={fadeUp}
            >
              {t("landing.heroSubtitle")}
            </motion.p>
            <motion.div
              className="mt-7 flex flex-col gap-3 sm:flex-row"
              transition={{ duration: 0.3 }}
              variants={fadeUp}
            >
              <Button
                asChild
                className={cn(
                  "h-12 rounded-xl bg-brand-green px-6 text-base font-bold text-white shadow-sm hover:bg-[#006d52]",
                  primaryButtonClass
                )}
              >
                <Link href="/register">{t("landing.heroCta")}</Link>
              </Button>
            </motion.div>
          </motion.div>

          <motion.div
            animate={{ opacity: 1, y: 0 }}
            className="relative flex min-h-[360px] items-center justify-center"
            initial={{ opacity: 0, y: 28 }}
            transition={{ delay: 0.25, duration: 0.3 }}
          >
            <div className="absolute right-4 top-0 h-80 w-80 rounded-full bg-brand-green-light" />
            <MatchScoreCard className="relative z-10 w-full max-w-lg scale-100 sm:scale-[1.08] lg:scale-[1.2]" />
          </motion.div>
        </div>
      </section>

      <ProblemSection />

      <RevealSection className="bg-white py-20" id="features">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-5">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <RevealItem delay={index * 0.08} key={feature.titleKey}>
                  <Card className="group rounded-xl border-black/10 bg-brand-green-light/80 shadow-none transition-all duration-200 hover:-translate-y-1 hover:shadow-md">
                    <CardHeader className="space-y-3 p-5">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex h-9 w-9 items-center justify-center rounded-full border border-brand-green/20 bg-white/60 text-brand-green">
                          <Icon className="h-4 w-4" />
                        </div>
                        {feature.premium ? (
                          <Badge className="gap-1 rounded-full bg-brand-green px-2 py-0.5 text-[10px] text-white">
                            <Lock className="h-2.5 w-2.5" />
                            {t("common.premium")}
                          </Badge>
                        ) : null}
                      </div>
                      <CardTitle className="text-base font-black">
                        {t(feature.titleKey)}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="px-5 pb-5 pt-0">
                      <CardDescription className="text-xs font-semibold leading-5 text-black/70">
                        {t(feature.descriptionKey)}
                      </CardDescription>
                    </CardContent>
                  </Card>
                </RevealItem>
              );
            })}
          </div>
        </div>
      </RevealSection>

      <RevealSection
        className="border-y border-black/5 bg-bg-dashboard py-20"
        id="how-it-works"
      >
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <h2 className="text-2xl font-black tracking-tight">
            {t("landing.howTitle")}
          </h2>
          <div className="mt-7 grid gap-6 md:grid-cols-[1fr_auto_1fr_auto_1fr] md:items-start">
            {steps.map((step, index) => (
              <div className="contents" key={step.titleKey}>
                <div className="flex gap-4">
                  <span className="text-5xl font-black leading-none text-black">
                    {index + 1}
                  </span>
                  <div>
                    <h3 className="text-base font-black">{t(step.titleKey)}</h3>
                    <p className="mt-1 max-w-xs text-xs font-medium leading-5 text-black/65">
                      {t(step.descriptionKey)}
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
      </RevealSection>

      <DemoSection />

      <RevealSection className="bg-white px-5 py-20 sm:px-8" id="pricing">
        <div className="mx-auto max-w-6xl">
          <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.2em] text-brand-green">
                {t("landing.pricingEyebrow")}
              </p>
              <h2 className="mt-3 text-3xl font-black tracking-tight text-black md:text-5xl">
                {t("landing.pricingTitle")}
              </h2>
            </div>
            <div className="inline-grid w-fit grid-cols-2 rounded-2xl border border-black/10 bg-bg-dashboard p-1">
              {(["monthly", "yearly"] as const).map((cycle) => (
                <button
                  className={cn(
                    "h-10 rounded-xl px-5 text-sm font-bold text-black/55 transition-all duration-200",
                    billingCycle === cycle && "bg-white text-brand-green shadow-sm"
                  )}
                  data-active={billingCycle === cycle}
                  key={cycle}
                  onClick={() => setBillingCycle(cycle)}
                  type="button"
                >
                  {cycle === "monthly" ? t("landing.monthly") : t("landing.yearly")}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-10 grid gap-5 md:grid-cols-2">
            <Card className="rounded-2xl border-black/10 shadow-none">
              <CardHeader>
                <CardTitle className="text-2xl font-black">{t("common.free")}</CardTitle>
                <CardDescription>{t("landing.freeDescription")}</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-4xl font-black">$0</p>
                <ul className="mt-6 space-y-3 text-sm font-semibold text-black/70">
                  {freeFeatures.map((item) => (
                    <li className="flex gap-2" key={item}>
                      <BadgeCheck className="mt-0.5 h-4 w-4 flex-none text-brand-green" />
                      {t(item)}
                    </li>
                  ))}
                </ul>
                <Button
                  asChild
                  className={cn(
                    "mt-7 w-full rounded-xl bg-brand-green text-white hover:bg-[#006d52]",
                    primaryButtonClass
                  )}
                >
                  <Link href="/register">{t("common.startFree")}</Link>
                </Button>
              </CardContent>
            </Card>

            <Card className="rounded-2xl border-brand-green/30 shadow-[0_24px_70px_rgba(15,23,42,0.10)]">
              <CardHeader>
                <div className="flex items-center justify-between gap-4">
                  <CardTitle className="text-2xl font-black">
                    {t("common.premium")}
                  </CardTitle>
                  <Badge className="rounded-full bg-brand-green text-white">
                    {t("landing.mostPopular")}
                  </Badge>
                </div>
                <CardDescription>{t("landing.premiumDescription")}</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-4xl font-black">{premiumPrice}</p>
                <ul className="mt-6 space-y-3 text-sm font-semibold text-black/70">
                  {premiumFeatures.map((item) => (
                    <li className="flex gap-2" key={item}>
                      <BadgeCheck className="mt-0.5 h-4 w-4 flex-none text-brand-green" />
                      {t(item)}
                    </li>
                  ))}
                </ul>
                <Button
                  asChild
                  className={cn(
                    "mt-7 w-full rounded-xl bg-brand-green text-white hover:bg-[#006d52]",
                    primaryButtonClass
                  )}
                >
                  <Link href="/register">{t("common.upgrade")}</Link>
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </RevealSection>

      <section className="bg-brand-green px-5 py-12 text-white sm:px-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center text-center">
          <TrendingUp className="h-7 w-7" />
          <h2 className="mt-5 text-3xl font-black tracking-tight md:text-4xl">
            {t("landing.finalCta")}
          </h2>
          <Button
            asChild
            className={cn(
              "mt-6 rounded-lg bg-white px-6 font-black text-brand-green hover:bg-white/90",
              primaryButtonClass
            )}
          >
            <Link href="/register">{t("common.startFree")}</Link>
          </Button>
        </div>
      </section>

      <footer className="bg-brand-green px-5 pb-8 text-white sm:px-8">
        <div className="mx-auto flex max-w-6xl flex-col gap-5 border-t border-white/15 pt-6 text-xs sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-base font-black">Jobby</p>
            <p className="mt-1 text-white/75">{t("landing.footerDescription")}</p>
          </div>
          <div className="flex flex-wrap items-center gap-5 text-white/80">
            <Link className="hover:text-white" href="/privacy">
              {t("landing.privacy")}
            </Link>
            <Link className="hover:text-white" href="/terms">
              {t("landing.terms")}
            </Link>
            <span>© 2026 Jobby</span>
          </div>
        </div>
      </footer>
    </main>
  );
}
