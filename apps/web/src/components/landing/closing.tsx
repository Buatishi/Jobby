"use client";

import Link from "next/link";

import { DarkPanel } from "@/components/dark-panel";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n/provider";

export function Closing() {
  const { t } = useI18n();

  return (
    <>
      <DarkPanel className="mx-4 mt-28" floor>
        <div className="px-6 pb-36 pt-24 text-center">
          <h2 className="mx-auto max-w-[18ch] text-[clamp(1.875rem,4vw,3rem)] font-semibold leading-[1.08] tracking-[-0.025em]">
            {t("landing.finalCta")}
          </h2>
          <p className="mt-4 text-base font-medium text-neutral-300">{t("landing.finalCtaSubtitle")}</p>
          <Button asChild className="mt-8" size="lg">
            <Link href="/register">{t("landing.heroCta")}</Link>
          </Button>
        </div>
      </DarkPanel>

      <footer className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-5 pb-14 pt-10 text-[13px] font-medium text-neutral-500 sm:px-8">
        <div>
          <p className="text-base font-bold text-brand-ink">Jobby</p>
          <p className="mt-1">{t("landing.footerDescription")}</p>
        </div>
        <div className="flex flex-wrap items-center gap-5">
          <Link className="hover:text-brand-ink" href="/privacy">
            {t("landing.privacy")}
          </Link>
          <Link className="hover:text-brand-ink" href="/terms">
            {t("landing.terms")}
          </Link>
          <span>© 2026 Jobby</span>
        </div>
      </footer>
    </>
  );
}
