import { describe, expect, it } from "vitest";

import { SITE_URL } from "@/lib/seo/site";
import sitemap from "@/src/app/sitemap";

const privatePrefixes = [
  "/admin",
  "/api",
  "/dashboard",
  "/profile",
  "/jobs",
  "/ats",
  "/reality-gap",
  "/interview-kits",
  "/wizard",
  "/billing"
];

describe("sitemap", () => {
  const entries = sitemap();

  it("lists the public pages under the site url", () => {
    expect(entries.map((entry) => entry.url)).toEqual([
      SITE_URL,
      `${SITE_URL}/pricing`,
      `${SITE_URL}/terms`,
      `${SITE_URL}/privacy`
    ]);
  });

  it("never lists a private route", () => {
    for (const entry of entries) {
      const path = new URL(entry.url).pathname;
      expect(
        privatePrefixes.some(
          (prefix) => path === prefix || path.startsWith(`${prefix}/`)
        )
      ).toBe(false);
    }
  });

  it("does not publish a modification date it cannot vouch for", () => {
    for (const entry of entries) {
      expect(entry.lastModified).toBeUndefined();
    }
  });
});
