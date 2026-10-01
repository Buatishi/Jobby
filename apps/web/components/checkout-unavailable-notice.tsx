"use client";

import { useI18n } from "@/lib/i18n/provider";

/** Aviso que reemplaza a una página de error de Lemon cuando el checkout no se pudo crear. */
export function CheckoutUnavailableNotice() {
  const { t } = useI18n();

  return (
    <div
      className="rounded-md border border-border bg-muted/50 p-3 text-sm"
      role="status"
    >
      <p className="font-semibold">{t("pricing.unavailableTitle")}</p>
      <p className="mt-1 text-muted-foreground">{t("pricing.unavailableBody")}</p>
    </div>
  );
}
