"use client";

import Link from "next/link";
import { useState } from "react";
import { Menu, X } from "lucide-react";

import { LanguageToggle } from "@/components/language-toggle";
import { Button } from "@/components/ui/button";
import { useHasSession } from "@/lib/auth/use-has-session";
import { useI18n } from "@/lib/i18n/provider";

const navLinks = [
  { href: "#cuando", labelKey: "landing.navWhen" },
  { href: "#funciones", labelKey: "landing.navFeatures" },
  { href: "#precios", labelKey: "landing.navPricing" }
];

export function LandingNav() {
  const { t } = useI18n();
  const hasSession = useHasSession();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const actions = hasSession ? (
    <Button asChild size="sm">
      <Link href="/dashboard">{t("common.goDashboard")}</Link>
    </Button>
  ) : (
    <>
      <Button asChild size="sm">
        <Link href="/register">{t("common.startFree")}</Link>
      </Button>
      <Button asChild size="sm" variant="outline">
        <Link href="/login">{t("common.login")}</Link>
      </Button>
    </>
  );

  return (
    <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md">
      <div className="mx-auto flex h-[68px] max-w-6xl items-center justify-between gap-4 px-5 sm:px-8">
        <a className="flex items-center gap-2 text-[22px] font-bold tracking-tight" href="#top">
          <span
            aria-hidden="true"
            className="flex h-[30px] w-[30px] items-center justify-center rounded-[10px] bg-brand-bright text-[17px]"
          >
            J
          </span>
          Jobby
        </a>

        <nav aria-label="Principal" className="hidden gap-7 text-sm font-medium text-neutral-600 md:flex">
          {navLinks.map((link) => (
            <a className="transition-colors hover:text-brand-ink" href={link.href} key={link.href}>
              {t(link.labelKey)}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-2.5 md:flex">
          <LanguageToggle />
          {actions}
        </div>

        <button
          aria-expanded={isMenuOpen}
          aria-label={t("common.openMenu")}
          className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-brand-line hover:bg-muted md:hidden"
          onClick={() => setIsMenuOpen((current) => !current)}
          type="button"
        >
          {isMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {isMenuOpen ? (
        <div className="border-t border-brand-line bg-white px-5 py-4 md:hidden">
          <div className="flex flex-col gap-3">
            {navLinks.map((link) => (
              <a
                className="rounded-full px-3 py-2 text-sm font-semibold text-neutral-700 hover:bg-brand-green-light"
                href={link.href}
                key={link.href}
                onClick={() => setIsMenuOpen(false)}
              >
                {t(link.labelKey)}
              </a>
            ))}
            <LanguageToggle className="w-fit" />
            <div className="flex flex-wrap gap-2.5">{actions}</div>
          </div>
        </div>
      ) : null}
    </header>
  );
}
