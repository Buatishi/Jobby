import { describe, expect, it, vi } from "vitest";

// `next/font` solo existe dentro del compilador de Next; el layout raíz lo llama al importarse.
vi.mock("next/font/google", () => ({
  Montserrat: () => ({ variable: "font-sans-brand" })
}));

import { metadata as root } from "@/src/app/layout";
import { metadata as pricing } from "@/src/app/(public)/pricing/layout";
import { metadata as privacy } from "@/src/app/privacy/layout";
import { metadata as terms } from "@/src/app/terms/layout";

describe("public pages metadata", () => {
  it("gives every public page its own title and description", () => {
    const pages = [root, pricing, terms, privacy];

    expect(new Set(pages.map((page) => page.title)).size).toBe(pages.length);
    expect(new Set(pages.map((page) => page.description)).size).toBe(
      pages.length
    );
  });

  it("keeps the brand name in every title", () => {
    for (const page of [pricing, terms, privacy]) {
      expect(String(page.title)).toContain("Jobby");
    }
  });

  it("names the brand and what it does in the home title", () => {
    const title = String(root.title);

    expect(title.startsWith("Jobby")).toBe(true);
    expect(title).toMatch(/\bCV\b/);
    expect(title).toMatch(/\bATS\b/);
    expect(title.toLowerCase()).toContain("match score");
  });

  it("keeps the home title short enough for the results page", () => {
    expect(String(root.title).length).toBeLessThanOrEqual(60);
  });

  // Quien busca «jobby web» o «jobby cv» tiene que encontrar esas palabras en lo que Google lee.
  it("uses the search wording «Jobby web» and «analizador de CV» in the home and pricing metadata", () => {
    for (const page of [root, pricing]) {
      expect(String(page.title)).toContain("Jobby web");
      expect(String(page.title).toLowerCase()).toContain("analizador de cv");
      expect(String(page.description)).toContain("Jobby web");
      expect(String(page.description).toLowerCase()).toContain("cv");
    }
  });

  it("keeps the pricing title and every description short enough for the results page", () => {
    expect(String(pricing.title).length).toBeLessThanOrEqual(60);
    for (const page of [root, pricing, terms, privacy]) {
      expect(String(page.description).length).toBeLessThanOrEqual(160);
    }
  });

  it("sets a self canonical on the legal pages", () => {
    expect(terms.alternates?.canonical).toBe("/terms");
    expect(privacy.alternates?.canonical).toBe("/privacy");
  });

  it("leaves the canonical out of pricing so its child routes do not inherit it", () => {
    expect(pricing.alternates).toBeUndefined();
  });

  it("carries the Search Console verification code on the root layout", () => {
    expect(root.verification?.google).toMatch(/^[A-Za-z0-9_-]{30,}$/);
  });
});
