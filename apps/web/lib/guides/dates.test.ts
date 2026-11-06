import { describe, expect, it } from "vitest";

import { formatGuideDate } from "@/lib/guides/dates";

describe("formatGuideDate", () => {
  it("writes the day, month name and year in Spanish", () => {
    expect(formatGuideDate("2026-11-02")).toBe("2 de noviembre de 2026");
    expect(formatGuideDate("2026-10-18")).toBe("18 de octubre de 2026");
  });

  it("does not move the day with the time zone of the server", () => {
    const original = process.env.TZ;
    try {
      for (const zone of ["UTC", "America/Argentina/Buenos_Aires", "Pacific/Auckland"]) {
        process.env.TZ = zone;
        expect(formatGuideDate("2026-10-19"), zone).toBe("19 de octubre de 2026");
      }
    } finally {
      if (original === undefined) delete process.env.TZ;
      else process.env.TZ = original;
    }
  });
});
