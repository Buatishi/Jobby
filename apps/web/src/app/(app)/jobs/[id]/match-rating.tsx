"use client";

import { useState, useSyncExternalStore } from "react";
import { Star } from "lucide-react";

import { useI18n } from "@/lib/i18n/provider";
import { cn } from "@/lib/utils";

import { createRatingStore, type RatingStatus } from "./match-rating-store";

type MatchRatingViewProps = {
  rating: number | null;
  status: RatingStatus;
  onSelect: (value: number) => void;
};

export function MatchRatingView({
  rating,
  status,
  onSelect
}: MatchRatingViewProps) {
  const { t } = useI18n();
  const saving = status === "saving";

  return (
    <>
      <div className="flex gap-2">
        {[1, 2, 3, 4, 5].map((value) => (
          <button
            aria-disabled={saving}
            aria-label={`Rating ${value}`}
            className="rounded-full p-1 hover:bg-muted"
            key={value}
            onClick={() => onSelect(value)}
            type="button"
          >
            <Star
              className={cn(
                "h-7 w-7",
                rating && value <= rating
                  ? "fill-secondary text-secondary"
                  : "text-muted-foreground"
              )}
            />
          </button>
        ))}
      </div>
      {/* La región existe siempre para que el lector de pantalla anuncie el aviso al aparecer. */}
      <p
        className={cn(
          "mt-3 min-h-5 text-sm",
          status === "error" ? "text-destructive" : "text-muted-foreground"
        )}
        role="status"
      >
        {status === "saved" ? t("app.ratingThanks") : null}
        {status === "error" ? t("app.ratingSaveError") : null}
      </p>
    </>
  );
}

type MatchRatingProps = {
  matchId: string;
  initialRating: number | null;
};

export function MatchRating({ matchId, initialRating }: MatchRatingProps) {
  const [store] = useState(() => createRatingStore(matchId, initialRating));
  const { rating, status } = useSyncExternalStore(
    store.subscribe,
    store.getState,
    store.getState
  );

  return (
    <MatchRatingView
      onSelect={(value) => void store.select(value)}
      rating={rating}
      status={status}
    />
  );
}
