import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({ apiClient: vi.fn() }));

import { I18nProvider } from "@/lib/i18n/provider";
import {
  MatchRating,
  MatchRatingView
} from "@/src/app/(app)/jobs/[id]/match-rating";

function renderView(
  rating: number | null,
  status: "idle" | "saving" | "saved" | "error"
) {
  return renderToStaticMarkup(
    <I18nProvider>
      <MatchRatingView onSelect={() => undefined} rating={rating} status={status} />
    </I18nProvider>
  );
}

const THANKS = "Gracias por tu feedback.";
const SAVE_ERROR = "No pudimos guardar tu calificación. Probá de nuevo.";

describe("MatchRatingView", () => {
  it("renders the five stars", () => {
    const html = renderView(null, "idle");

    for (const value of [1, 2, 3, 4, 5]) {
      expect(html).toContain(`aria-label="Rating ${value}"`);
    }
  });

  it("fills as many stars as the rating", () => {
    const html = renderView(3, "idle");

    expect(html.match(/fill-secondary/g)).toHaveLength(3);
  });

  it("fills no star without a rating", () => {
    expect(renderView(null, "idle")).not.toContain("fill-secondary");
  });

  it("thanks the user only after the rating was saved", () => {
    expect(renderView(4, "saved")).toContain(THANKS);
  });

  it("does not thank while the rating is being saved", () => {
    expect(renderView(4, "saving")).not.toContain(THANKS);
  });

  it("does not thank for a rating that was already there before saving anything", () => {
    expect(renderView(4, "idle")).not.toContain(THANKS);
  });

  it("warns when the rating could not be saved, without thanking", () => {
    const html = renderView(2, "error");

    expect(html).toContain(SAVE_ERROR);
    expect(html).not.toContain(THANKS);
  });

  it("keeps a polite live region so assistive tech announces the result", () => {
    expect(renderView(null, "idle")).toContain('role="status"');
  });

  it("marks the stars as busy while a save is in flight", () => {
    expect(renderView(4, "saving")).toContain('aria-disabled="true"');
    expect(renderView(4, "idle")).not.toContain('aria-disabled="true"');
  });
});

describe("MatchRating", () => {
  it("starts from the rating stored in the report, without a message", () => {
    const html = renderToStaticMarkup(
      <I18nProvider>
        <MatchRating initialRating={2} matchId="match-1" />
      </I18nProvider>
    );

    expect(html.match(/fill-secondary/g)).toHaveLength(2);
    expect(html).not.toContain(THANKS);
    expect(html).not.toContain(SAVE_ERROR);
  });
});
