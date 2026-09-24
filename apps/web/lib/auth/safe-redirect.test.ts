import { describe, expect, it } from "vitest";

import { safeRedirectPath } from "@/lib/auth/safe-redirect";

describe("safeRedirectPath", () => {
  it.each([
    ["/dashboard", "/dashboard"],
    ["/jobs/123?tab=ats#resumen", "/jobs/123?tab=ats#resumen"],
    ["/profile", "/profile"]
  ])("keeps the internal path %s", (value, expected) => {
    expect(safeRedirectPath(value)).toBe(expected);
  });

  it.each([
    ["https://evil.example/login"],
    ["http://evil.example"],
    ["//evil.example/path"],
    ["/\u005cevil.example"],
    ["/\t/evil.example"],
    ["javascript:alert(1)"],
    ["dashboard"],
    [""],
    [null],
    [undefined]
  ])("falls back to the dashboard for %s", (value) => {
    expect(safeRedirectPath(value)).toBe("/dashboard");
  });

  it("uses the given fallback", () => {
    expect(safeRedirectPath("https://evil.example", "/login")).toBe("/login");
  });
});
