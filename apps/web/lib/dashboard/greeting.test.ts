import { afterEach, describe, expect, it } from "vitest";

import { formatToday, greetingKeyForHour } from "@/lib/dashboard/greeting";

const originalTimeZone = process.env.TZ;

afterEach(() => {
  if (originalTimeZone === undefined) {
    delete process.env.TZ;
  } else {
    process.env.TZ = originalTimeZone;
  }
});

function inTimeZone<T>(timeZone: string, run: () => T): T {
  process.env.TZ = timeZone;
  return run();
}

describe("greetingKeyForHour", () => {
  it.each([
    [0, "app.goodMorning"],
    [11, "app.goodMorning"],
    [12, "app.goodAfternoon"],
    [19, "app.goodAfternoon"],
    [20, "app.goodNight"],
    [23, "app.goodNight"]
  ])("picks the greeting for hour %i", (hour, key) => {
    expect(greetingKeyForHour(hour)).toBe(key);
  });
});

describe("formatToday", () => {
  // 23:05 en Buenos Aires es 02:05 UTC del día siguiente: el caso que desajustaba la hidratación.
  const instant = new Date("2026-10-22T02:05:00Z");

  it("writes the weekday, day and month in the language of the interface", () => {
    inTimeZone("UTC", () => {
      expect(formatToday(instant, "es-AR")).toBe("jueves, 22 de octubre");
      expect(formatToday(instant, "en-US")).toBe("Thursday, October 22");
    });
  });

  it("uses the day of the time zone where the code runs, not UTC", () => {
    inTimeZone("America/Argentina/Buenos_Aires", () => {
      // Guarda del test: si el runtime ignora TZ, el resto de las pruebas no probaría nada.
      expect(instant.getHours()).toBe(23);
      expect(formatToday(instant, "es-AR")).toBe("miércoles, 21 de octubre");
    });
  });
});
