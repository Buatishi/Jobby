"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Check, Loader2 } from "lucide-react";

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
  "landing.freeFeatures.four"
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
          <Link className="text-xl font-black" href="/">
            Jobby
          </Link>
          <LanguageToggle />
        </div>

        <div className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
          <div>
            <p className="text-sm font-medium text-muted-foreground">Jobby</p>
            <h1 className="mt-2 text-4xl font-semibold tracking-normal">
              {t("pricing.title")}
            </h1>
            <p className="mt-3 max-w-2xl text-muted-foreground">
              {t("pricing.subtitle")}
            </p>
          </div>
          <div className="inline-flex w-fit rounded-lg border border-border bg-background p-1">
            <button
              className="rounded-md px-4 py-2 text-sm font-medium data-[active=true]:bg-primary data-[active=true]:text-primary-foreground"
              data-active={billingCycle === "monthly"}
              onClick={() => setBillingCycle("monthly")}
              type="button"
            >
              {t("landing.monthly")}
            </button>
            <button
              className="rounded-md px-4 py-2 text-sm font-medium data-[active=true]:bg-primary data-[active=true]:text-primary-foreground"
              data-active={billingCycle === "yearly"}
              onClick={() => setBillingCycle("yearly")}
              type="button"
            >
              {t("landing.yearly")}
            </button>
          </div>
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>{t("common.free")}</CardTitle>
              <p className="text-3xl font-semibold">$0</p>
              <CardDescription>{t("pricing.freeDescription")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {freeFeatures.map((item) => (
                <div className="flex gap-3 text-sm" key={item}>
                  <Check
                    className="mt-0.5 h-4 w-4 flex-none"
                    style={{ color: scoreColors.lightGreen }}
                  />
                  <span>{t(item)}</span>
                </div>
              ))}
              <Button asChild className="mt-2 w-full" variant="secondary">
                <Link href="/dashboard">{t("pricing.followFree")}</Link>
              </Button>
            </CardContent>
          </Card>

          <Card className="border-2" style={{ borderColor: scoreColors.darkGreen }}>
            <CardHeader>
              <div className="flex items-center justify-between gap-3">
                <CardTitle>{t("common.premium")}</CardTitle>
                <Badge>{t("common.premium")}</Badge>
              </div>
              <p className="text-3xl font-semibold">{premiumPrice}</p>
              <CardDescription>{t("pricing.premiumDescription")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {premiumFeatures.map((item) => (
                <div className="flex gap-3 text-sm" key={item}>
                  <Check
                    className="mt-0.5 h-4 w-4 flex-none"
                    style={{ color: scoreColors.darkGreen }}
                  />
                  <span>{t(item)}</span>
                </div>
              ))}
              {error ? (
                <p className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
                  {error}
                </p>
              ) : null}
              <Button
                className="mt-2 w-full"
                disabled={isRedirecting}
                onClick={() => void handleUpgrade()}
                type="button"
              >
                {isRedirecting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t("pricing.redirecting")}
                  </>
                ) : (
                  t("common.upgrade")
                )}
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
