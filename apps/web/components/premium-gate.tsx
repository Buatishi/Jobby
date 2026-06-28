"use client";

import Link from "next/link";
import { Lock } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type PremiumGateProps = {
  className?: string;
  compact?: boolean;
};

export function PremiumGate({ className, compact = false }: PremiumGateProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-lg border border-border bg-muted/30 p-4 sm:flex-row sm:items-center sm:justify-between",
        className
      )}
    >
      <div className="flex items-start gap-3">
        <span
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-background text-muted-foreground"
          title="Disponible para usuarios Premium"
        >
          <Lock className="h-4 w-4" />
        </span>
        <div>
          <p className="text-sm font-medium">Función Premium</p>
          {!compact ? (
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              Desbloqueá Interview Kits personalizados, regeneraciones y
              preparación avanzada por puesto.
            </p>
          ) : null}
        </div>
      </div>
      <Button asChild>
        <Link href="/pricing">Upgrade a Premium</Link>
      </Button>
    </div>
  );
}
