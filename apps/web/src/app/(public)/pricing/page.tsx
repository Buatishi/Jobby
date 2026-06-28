"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Check, Loader2 } from "lucide-react";

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
import { scoreColors } from "@/lib/utils/score-colors";

type BillingCycle = "monthly" | "yearly";

type CheckoutResponse = {
  url: string;
};

const freeFeatures = [
  "10 análisis de jobs por mes",
  "5 reportes ATS por día",
  "Historial de últimos 10 jobs",
  "Match Score completo"
];

const premiumFeatures = [
  "Análisis de jobs ilimitados",
  "50 reportes ATS por día",
  "10 Interview Kits por mes",
  "CV Optimizer e IA premium",
  "Historial completo"
];

export default function PricingPage() {
  const [billingCycle, setBillingCycle] = useState<BillingCycle>("monthly");
  const [isRedirecting, setIsRedirecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const monthlyPrice = process.env.NEXT_PUBLIC_PRICE_MONTHLY ?? "[MONTHLY_PRICE]";
  const yearlyPrice = process.env.NEXT_PUBLIC_PRICE_YEARLY ?? "[YEARLY_PRICE]";
  const monthlyPriceId = process.env.NEXT_PUBLIC_STRIPE_PRICE_MONTHLY_ID ?? "";
  const yearlyPriceId = process.env.NEXT_PUBLIC_STRIPE_PRICE_YEARLY_ID ?? "";

  const premiumPrice = useMemo(
    () =>
      billingCycle === "monthly"
        ? `$${monthlyPrice}/mes`
        : `$${yearlyPrice}/año`,
    [billingCycle, monthlyPrice, yearlyPrice]
  );

  async function handleUpgrade() {
    setError(null);
    const priceId =
      billingCycle === "monthly" ? monthlyPriceId : yearlyPriceId;
    if (!priceId) {
      setError("Falta configurar el Price ID de Stripe para este plan.");
      return;
    }

    setIsRedirecting(true);
    try {
      const origin = window.location.origin;
      const response = await apiClient<CheckoutResponse>(
        "/api/v1/billing/checkout-session",
        {
          method: "POST",
          body: JSON.stringify({
            price_id: priceId,
            success_url: `${origin}/pricing/success`,
            cancel_url: `${origin}/pricing/cancel`
          })
        }
      );
      window.location.href = response.url;
    } catch (requestError) {
      setIsRedirecting(false);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No se pudo iniciar Stripe Checkout."
      );
    }
  }

  return (
    <main className="min-h-screen bg-background">
      <section className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:py-16">
        <div className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
          <div>
            <p className="text-sm font-medium text-muted-foreground">
              JobMatch AI
            </p>
            <h1 className="mt-2 text-4xl font-semibold tracking-normal">
              Elegí tu plan
            </h1>
            <p className="mt-3 max-w-2xl text-muted-foreground">
              Empezá gratis y pasá a Premium cuando quieras preparar entrevistas,
              analizar más puestos y desbloquear IA avanzada.
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
              <CardDescription>Para validar tu primer flujo.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {freeFeatures.map((item) => (
                <div className="flex gap-3 text-sm" key={item}>
                  <Check
                    className="mt-0.5 h-4 w-4 flex-none"
                    style={{ color: scoreColors.lightGreen }}
                  />
                  <span>{item}</span>
                </div>
              ))}
              <Button asChild className="mt-2 w-full" variant="secondary">
                <Link href="/dashboard">Seguir gratis</Link>
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
                Para aplicar con reportes completos y preparación personalizada.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {premiumFeatures.map((item) => (
                <div className="flex gap-3 text-sm" key={item}>
                  <Check
                    className="mt-0.5 h-4 w-4 flex-none"
                    style={{ color: scoreColors.darkGreen }}
                  />
                  <span>{item}</span>
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
                    Redirigiendo a Stripe...
                  </>
                ) : (
                  "Upgrade"
                )}
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
