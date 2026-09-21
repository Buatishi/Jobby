"use client";

import { useEffect, useSyncExternalStore } from "react";

import { coldStartNotice, warmUpApi } from "@/lib/api/cold-start";
import { useI18n } from "@/lib/i18n/provider";

/**
 * Pre-calienta la API al abrir la web (una vez cada 10 minutos por pestaña) y muestra un
 * aviso mientras un pedido tarda de más. Ver docs/operacion/arranque-en-frio.md.
 */
export function ColdStartNotice() {
  const { t } = useI18n();
  const visible = useSyncExternalStore(
    coldStartNotice.subscribe,
    coldStartNotice.getSnapshot,
    coldStartNotice.getServerSnapshot
  );

  useEffect(() => {
    warmUpApi();
  }, []);

  if (!visible) {
    return null;
  }

  return (
    <div
      aria-live="polite"
      className="fixed inset-x-0 bottom-4 z-50 mx-auto w-[min(92vw,28rem)] rounded-xl border border-border bg-background px-4 py-3 text-sm text-foreground shadow-lg"
      role="status"
    >
      <p className="font-semibold">{t("common.coldStartTitle")}</p>
      <p className="mt-1 text-muted-foreground">{t("common.coldStartBody")}</p>
    </div>
  );
}
