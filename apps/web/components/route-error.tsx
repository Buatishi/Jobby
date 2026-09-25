"use client";

import Link from "next/link";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { useI18n } from "@/lib/i18n/provider";

const destinations = {
  landing: { href: "/", labelKey: "status.goHome" },
  dashboard: { href: "/dashboard", labelKey: "status.goDashboard" }
} as const;

type RouteErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
  home: keyof typeof destinations;
};

/** Error de una sección: se puede reintentar y no muestra detalles internos. */
export function RouteError({ error, reset, home }: RouteErrorProps) {
  const { t } = useI18n();
  const destination = destinations[home];

  useEffect(() => {
    // El detalle queda en la consola del navegador, no en la pantalla.
    console.error(error);
  }, [error]);

  return (
    <main className="mx-auto max-w-2xl px-4 py-10 sm:px-6">
      <Card role="alert">
        <CardHeader>
          <CardTitle>{t("status.errorTitle")}</CardTitle>
          <CardDescription>{t("status.errorBody")}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 sm:flex-row">
          <Button onClick={reset} type="button">
            {t("status.retry")}
          </Button>
          <Button asChild variant="outline">
            <Link href={destination.href}>{t(destination.labelKey)}</Link>
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
