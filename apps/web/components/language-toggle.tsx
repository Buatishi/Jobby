"use client";

import { Languages } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n/provider";
import { cn } from "@/lib/utils";

type LanguageToggleProps = {
  className?: string;
  compact?: boolean;
};

export function LanguageToggle({ className, compact = false }: LanguageToggleProps) {
  const { language, toggleLanguage, t } = useI18n();
  const nextLanguage = language === "es" ? "EN" : "ES";

  return (
    <Button
      aria-label={`${t("common.language")}: ${language.toUpperCase()}`}
      className={cn(
        "h-9 shrink-0 border border-brand-line bg-white px-3.5 text-xs font-bold text-brand-ink shadow-none transition hover:border-brand-green/40 hover:bg-brand-green-light hover:text-brand-green focus-visible:ring-2 focus-visible:ring-brand-green/30",
        className
      )}
      leftIcon={<Languages className="h-3.5 w-3.5" />}
      onClick={toggleLanguage}
      type="button"
      variant="ghost"
    >
      {compact ? language.toUpperCase() : `${language.toUpperCase()} / ${nextLanguage}`}
    </Button>
  );
}
