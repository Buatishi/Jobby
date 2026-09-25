"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n/provider";

export default function NotFound() {
  const { t } = useI18n();

  return (
    <main className="mx-auto flex min-h-[60vh] max-w-2xl flex-col items-center justify-center px-4 py-16 text-center">
      <p className="text-sm font-medium text-muted-foreground">404</p>
      <h1 className="mt-2 text-3xl font-semibold">{t("status.notFoundTitle")}</h1>
      <p className="mt-3 text-muted-foreground">{t("status.notFoundBody")}</p>
      <div className="mt-6 flex flex-col gap-3 sm:flex-row">
        <Button asChild>
          <Link href="/">{t("status.goHome")}</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/dashboard">{t("status.goDashboard")}</Link>
        </Button>
      </div>
    </main>
  );
}
