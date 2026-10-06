"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { CircleCheck } from "lucide-react";

import { DarkPanel } from "@/components/dark-panel";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n/provider";
import { cn } from "@/lib/utils";
import { SectionHead } from "@/src/components/landing/shared";

type BillingCycle = "monthly" | "yearly";

const freeFeatures = [
  "landing.freeFeatures.one",
  "landing.freeFeatures.two",
  "landing.freeFeatures.three",
  "landing.freeFeatures.four",
  "landing.freeFeatures.five"
];

const premiumFeatures = [
  "landing.premiumFeatures.one",
  "landing.premiumFeatures.two",
  "landing.premiumFeatures.three",
  "landing.premiumFeatures.four",
  "landing.premiumFeatures.five"
];

function Radar() {
  return (
    <svg
      aria-hidden="true"
      className="pointer-events-none absolute -bottom-[70px] -right-[70px] z-0 h-80 w-80 opacity-40"
      fill="none"
      stroke="#2BD48A"
      strokeWidth={1}
      viewBox="-170 -170 340 340"
    >
      <circle r={40} />
      <circle r={80} />
      <circle r={120} />
      <circle r={160} />
      <path d="M-160 0H160M0 -160V160M-113 -113L113 113M-113 113L113 -113" />
      <path d="M0 0L113 -113" strokeWidth={2} />
    </svg>
  );
}

export function Plans() {
  const { t } = useI18n();
  const [billingCycle, setBillingCycle] = useState<BillingCycle>("monthly");
  const monthlyPrice = process.env.NEXT_PUBLIC_PRICE_MONTHLY ?? "0";
  const yearlyPrice = process.env.NEXT_PUBLIC_PRICE_YEARLY ?? "0";

  const premiumPrice = useMemo(() => {
    return billingCycle === "monthly"
      ? `$${monthlyPrice}/${t("landing.perMonth")}`
      : `$${yearlyPrice}/${t("landing.perYear")}`;
  }, [billingCycle, monthlyPrice, t, yearlyPrice]);

  return (
    <section className="mx-auto max-w-6xl px-5 pt-28 sm:px-8" id="precios">
      <SectionHead eyebrow={t("landing.pricingEyebrow")} title={t("landing.pricingTitle")} />

      <div className="mb-8 flex justify-center">
        <div className="inline-grid grid-cols-2 rounded-full border border-brand-line bg-bg-dashboard p-1">
          {(["monthly", "yearly"] as const).map((cycle) => (
            <button
              aria-pressed={billingCycle === cycle}
              className={cn(
                "h-10 rounded-full px-5 text-sm font-semibold text-neutral-500 transition-colors",
                billingCycle === cycle && "bg-white text-brand-green shadow-sm"
              )}
              key={cycle}
              onClick={() => setBillingCycle(cycle)}
              type="button"
            >
              {cycle === "monthly" ? t("landing.monthly") : t("landing.yearly")}
            </button>
          ))}
        </div>
      </div>

      <div className="mx-auto grid max-w-[880px] gap-5 md:grid-cols-2">
        <article className="rounded-panel border border-brand-line bg-white p-9 shadow-card">
          <h3 className="text-[22px] font-semibold">{t("common.free")}</h3>
          <p className="mt-3 text-[44px] font-semibold leading-none tracking-tight">$0</p>
          <p className="mt-2 text-[13px] font-medium text-neutral-500">{t("landing.freeDescription")}</p>
          <ul className="my-6 grid gap-3 text-sm font-medium">
            {freeFeatures.map((item) => (
              <li className="flex items-start gap-2.5" key={item}>
                <CircleCheck aria-hidden="true" className="mt-0.5 h-[18px] w-[18px] flex-none text-brand-green" />
                {t(item)}
              </li>
            ))}
          </ul>
          <Button asChild>
            <Link href="/register">{t("common.startFree")}</Link>
          </Button>
        </article>

        <DarkPanel backdrop={<Radar />} className="border border-brand-green p-9" variant="forest">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-[22px] font-semibold">{t("common.premium")}</h3>
            <span className="rounded-full bg-brand-bright px-3 py-0.5 text-xs font-bold text-brand-ink">
              {t("landing.mostPopular")}
            </span>
          </div>
          <p className="mt-3 text-[44px] font-semibold leading-none tracking-tight">{premiumPrice}</p>
          <p className="mt-2 text-[13px] font-medium text-emerald-100/80">{t("landing.premiumDescription")}</p>
          <ul className="my-6 grid gap-3 text-sm font-medium">
            {premiumFeatures.map((item) => (
              <li className="flex items-start gap-2.5" key={item}>
                <CircleCheck aria-hidden="true" className="mt-0.5 h-[18px] w-[18px] flex-none text-brand-bright" />
                {t(item)}
              </li>
            ))}
          </ul>
          <Button asChild>
            <Link href="/register">{t("common.upgrade")}</Link>
          </Button>
        </DarkPanel>
      </div>
    </section>
  );
}
