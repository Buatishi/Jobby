import { describe, expect, it } from "vitest";

import { ABOUT_UPDATED_AT } from "@/lib/about/about";
import { GUIDES } from "@/lib/guides/guides";
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
      `${SITE_URL}/que-es-jobby`,
      `${SITE_URL}/guias`,
      ...GUIDES.map((guide) => `${SITE_URL}/guias/${guide.slug}`),
      `${SITE_URL}/terms`,
      `${SITE_URL}/privacy`
    ]);
  });

  it("lists every guide once", () => {
    const urls = entries.map((entry) => entry.url);

    expect(GUIDES.length).toBeGreaterThan(0);
    expect(new Set(urls).size).toBe(urls.length);
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

  it("dates only the guides and «Qué es Jobby», with the day their content last changed", () => {
    const datedUrls = new Map<string, string>([
      ...GUIDES.map((guide) => [`${SITE_URL}/guias/${guide.slug}`, guide.updatedAt] as const),
      [`${SITE_URL}/que-es-jobby`, ABOUT_UPDATED_AT] as const
    ]);

    for (const entry of entries) {
      expect(entry.lastModified, entry.url).toBe(datedUrls.get(entry.url));
    }
    // Las demás páginas no tienen una fecha de contenido registrada: una fecha del build no es fiable.
    expect(entries.filter((entry) => entry.lastModified)).toHaveLength(GUIDES.length + 1);
  });
});
