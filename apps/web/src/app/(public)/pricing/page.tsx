"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ArrowLeft, Check } from "lucide-react";


import { DarkPanel } from "@/components/dark-panel";
import { LanguageToggle } from "@/components/language-toggle";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { useHasSession } from "@/lib/auth/use-has-session";

import { isCheckoutUnavailable } from "@/lib/billing/checkout-error";
import { useI18n } from "@/lib/i18n/provider";
import { scoreColors } from "@/lib/utils/score-colors";

type BillingCycle = "monthly" | "yearly";

type CheckoutResponse = {
  checkout_url: string;
};

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

export default function PricingPage() {
  const { t } = useI18n();
  const router = useRouter();
  const hasSession = useHasSession();
  const [billingCycle, setBillingCycle] = useState<BillingCycle>("monthly");
  const [isRedirecting, setIsRedirecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const monthlyPrice = process.env.NEXT_PUBLIC_PRICE_MONTHLY ?? "[MONTHLY_PRICE]";
  const yearlyPrice = process.env.NEXT_PUBLIC_PRICE_YEARLY ?? "[YEARLY_PRICE]";

  const premiumPrice = useMemo(
    () =>
      billingCycle === "monthly"
        ? `$${monthlyPrice}/${t("landing.perMonth")}`
        : `$${yearlyPrice}/${t("landing.perYear")}`,
    [billingCycle, monthlyPrice, t, yearlyPrice]
  );

  async function handleUpgrade() {
    setError(null);
    setIsRedirecting(true);
    try {
      const response = await apiClient<CheckoutResponse>(
        "/api/v1/billing/checkout",
        { method: "POST" }
      );
      window.location.href = response.checkout_url;
    } catch (requestError) {
      if (isCheckoutUnavailable(requestError)) {
        // Falla del checkout (Lemon, configuración, red): una página nuestra que lo explica,
        // en vez de dejar a la persona en una página de error de otro sitio. El botón sigue
        // en «Redirigiendo…» hasta que cambia la página.
        router.push("/pricing/unavailable");
        return;
      }
      setIsRedirecting(false);
      setError(
        requestError instanceof Error
          ? requestError.message
          : t("pricing.checkoutFail")
      );
    }
  }

  return (
    <main className="min-h-screen bg-background">
      <section className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:py-16">
        <div className="mb-8 flex items-center justify-between gap-4">
          <Link className="flex items-center gap-2 text-xl font-bold" href="/">
            <span
              aria-hidden="true"
              className="flex h-[30px] w-[30px] items-center justify-center rounded-[10px] bg-brand-bright text-[17px]"
            >
              J
            </span>
            Jobby
          </Link>
          <div className="flex items-center gap-3">
            {hasSession ? (
              <Button asChild size="sm" variant="ghost">
                <Link href="/dashboard">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  {t("common.backToDashboard")}
                </Link>
              </Button>
            ) : null}
            <LanguageToggle />
          </div>
        </div>

        <DarkPanel floor>
          <div className="flex flex-col justify-between gap-6 px-6 pb-14 pt-8 sm:px-10 sm:pt-10 md:flex-row md:items-end">
            <div>
              <p className="text-sm font-semibold text-brand-bright">Jobby</p>
              <h1 className="mt-2 text-[clamp(1.875rem,4vw,2.75rem)] font-semibold leading-[1.1] tracking-[-0.025em]">
                {t("pricing.title")}
              </h1>
              <p className="mt-3 max-w-2xl text-[15px] font-medium text-neutral-300">
                {t("pricing.subtitle")}
              </p>
            </div>
            <div className="inline-flex w-fit rounded-full border border-white/20 bg-white/10 p-1">
              <button
                className="rounded-full px-4 py-2 text-sm font-semibold text-white data-[active=true]:bg-brand-bright data-[active=true]:text-brand-ink"
                data-active={billingCycle === "monthly"}
                onClick={() => setBillingCycle("monthly")}
                type="button"
              >
                {t("landing.monthly")}
              </button>
              <button
                className="rounded-full px-4 py-2 text-sm font-semibold text-white data-[active=true]:bg-brand-bright data-[active=true]:text-brand-ink"
                data-active={billingCycle === "yearly"}
                onClick={() => setBillingCycle("yearly")}
                type="button"
              >
                {t("landing.yearly")}
              </button>
            </div>
          </div>
        </DarkPanel>

        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <Card className="flex flex-col">
            <CardHeader>
              <div className="flex h-6 items-center">
                <CardTitle>{t("common.free")}</CardTitle>
              </div>
              <p className="text-3xl font-semibold">$0</p>
              <CardDescription>{t("pricing.freeDescription")}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-1 flex-col gap-4">
              {freeFeatures.map((item) => (
                <div className="flex gap-3 text-sm" key={item}>
                  <Check
                    className="mt-0.5 h-4 w-4 flex-none"
                    style={{ color: scoreColors.lightGreen }}
                  />
                  <span>{t(item)}</span>
                </div>
              ))}
              {/* Los botones van al fondo de cada tarjeta: quedan a la misma altura aunque
                  un plan tenga más ítems o muestre un aviso. */}
              <div className="mt-auto pt-2">
                <Button asChild className="w-full" variant="secondary">
                  <Link href="/dashboard">{t("pricing.followFree")}</Link>
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card
            className="flex flex-col border-2"
            style={{ borderColor: scoreColors.darkGreen }}
          >
            <CardHeader>
              <div className="flex h-6 items-center justify-between gap-3">
                <CardTitle>{t("common.premium")}</CardTitle>
                <Badge>{t("common.premium")}</Badge>
              </div>
              <p className="text-3xl font-semibold">{premiumPrice}</p>
              <CardDescription>{t("pricing.premiumDescription")}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-1 flex-col gap-4">
              {premiumFeatures.map((item) => (
                <div className="flex gap-3 text-sm" key={item}>
                  <Check
                    className="mt-0.5 h-4 w-4 flex-none"
                    style={{ color: scoreColors.darkGreen }}
                  />
                  <span>{t(item)}</span>
                </div>
              ))}
              <div className="mt-auto flex flex-col gap-4 pt-2">
                {error ? (
                  <p className="rounded-2xl border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
                    {error}
                  </p>
                ) : null}
                <Button
                  aria-busy={isRedirecting}
                  className="w-full"
                  isLoading={isRedirecting}
                  onClick={() => void handleUpgrade()}
                  type="button"
                >
                  {isRedirecting ? t("pricing.redirecting") : t("common.upgrade")}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-4 text-xs font-medium text-muted-foreground">
          <Link className="hover:text-primary" href="/terms">
            Términos y Condiciones
          </Link>
          <span>·</span>
          <Link className="hover:text-primary" href="/privacy">
            Política de Privacidad
          </Link>
        </div>
      </section>
    </main>
  );
}
