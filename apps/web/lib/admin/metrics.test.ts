import { describe, expect, it } from "vitest";

import {
  activityBars,
  type DailyActivity,
  formatDay,
  seriesTotal
} from "@/lib/admin/metrics";

const days: DailyActivity[] = [
  { day: "2026-09-22", cvs: 1, jobs: 4, matches: 0 },
  { day: "2026-09-23", cvs: 2, jobs: 1, matches: 0 },
  { day: "2026-09-24", cvs: 2, jobs: 0, matches: 0 }
];

describe("activityBars", () => {
  it("scales every day against the busiest one", () => {
    expect(activityBars(days, "jobs").map((bar) => bar.heightPercent)).toEqual([
      100, 25, 0
    ]);
  });

  it("labels only the most recent peak", () => {
    expect(activityBars(days, "cvs").map((bar) => bar.isPeak)).toEqual([
      false,
      false,
      true
    ]);
  });

  it("draws nothing and labels nothing for a series without activity", () => {
    const bars = activityBars(days, "matches");

    expect(bars.every((bar) => bar.heightPercent === 0 && !bar.isPeak)).toBe(true);
  });
});

describe("seriesTotal", () => {
  it("adds the whole window", () => {
    expect(seriesTotal(days, "cvs")).toBe(5);
  });
});

describe("formatDay", () => {
  it("keeps the calendar day whatever the time zone", () => {
    expect(formatDay("2026-09-01", "en-US")).toBe("Sep 1");
  });
});
