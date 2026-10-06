"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useHasSession } from "@/lib/auth/use-has-session";
import { useI18n } from "@/lib/i18n/provider";

/** Un CV con cara triste: sin imágenes externas, con los colores del tema. */
function SadCv({ label }: { label: string }) {
  return (
    <svg
      aria-label={label}
      className="h-44 w-36 text-muted-foreground"
      fill="none"
      role="img"
      viewBox="0 0 144 176"
    >
      {/* Hoja con la esquina doblada */}
      <path
        className="fill-background"
        d="M16 8h80l32 32v120a8 8 0 0 1-8 8H16a8 8 0 0 1-8-8V16a8 8 0 0 1 8-8Z"
        stroke="currentColor"
        strokeLinejoin="round"
        strokeWidth="3"
      />
      <path
        d="M96 8v24a8 8 0 0 0 8 8h24"
        stroke="currentColor"
        strokeLinejoin="round"
        strokeWidth="3"
      />
      {/* Encabezado del CV: foto y renglones */}
      <circle className="fill-muted" cx="40" cy="38" r="10" />
      <path
        d="M58 33h28M58 43h18"
        stroke="currentColor"
        strokeLinecap="round"
        strokeOpacity="0.45"
        strokeWidth="4"
      />
      {/* Cara triste */}
      <circle cx="52" cy="92" fill="currentColor" r="4.5" />
      <circle cx="92" cy="92" fill="currentColor" r="4.5" />
      <path
        d="M47 82l11-4M97 82l-11-4"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="3"
      />
      <path
        d="M54 118c6-8 30-8 36 0"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="3.5"
      />
      {/* Lágrima */}
      <path
        className="fill-primary"
        d="M98 100c4 6 6 9 6 12a6 6 0 0 1-12 0c0-3 2-6 6-12Z"
        fillOpacity="0.55"
      />
      {/* Renglones del CV, sin completar */}
      <path
        d="M24 142h56M24 154h40"
        stroke="currentColor"
        strokeLinecap="round"
        strokeOpacity="0.3"
        strokeWidth="4"
      />
    </svg>
  );
}

/** Adonde se llega cuando el checkout no se pudo crear (por ejemplo, la tienda de pagos no está activa). */
export function CheckoutUnavailableView() {
  const { t } = useI18n();
  const hasSession = useHasSession();

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center px-4 py-16 text-center">
      <Link className="mb-8 text-xl font-bold" href="/">
        Jobby
      </Link>
      <SadCv label={t("pricing.unavailableAlt")} />
      <p className="mt-6 text-6xl font-semibold tracking-tight text-primary">404</p>
      <h1 className="mt-2 text-2xl font-semibold">{t("pricing.unavailableTitle")}</h1>
      <p className="mt-3 max-w-md text-muted-foreground">
        {t("pricing.unavailableBody")}
      </p>
      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <Button asChild>
          <Link href="/pricing">{t("pricing.backToPlans")}</Link>
        </Button>
        <Button asChild variant="outline">
          {hasSession ? (
            <Link href="/dashboard">{t("status.goDashboard")}</Link>
          ) : (
            <Link href="/">{t("status.goHome")}</Link>
          )}
        </Button>
      </div>
    </main>
  );
}
