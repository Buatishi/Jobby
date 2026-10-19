import { describe, expect, it } from "vitest";

import { SITE_SAME_AS, SITE_URL } from "@/lib/seo/site";
import {
  buildHomeStructuredData,
  serializeJsonLd
} from "@/lib/seo/structured-data";

describe("home structured data", () => {
  it("describes the site, the app and the organization with the public url", () => {
    const nodes = buildHomeStructuredData();

    expect(nodes.map((node) => node["@type"])).toEqual([
      "WebSite",
      "WebApplication",
      "Organization"
    ]);
    for (const node of nodes) {
      expect(node["@context"]).toBe("https://schema.org");
      expect(node.url).toBe(SITE_URL);
      expect(node.name).toBe("Jobby");
    }
  });

  it("links the organization to its public profiles through sameAs", () => {
    const organization = buildHomeStructuredData().find(
      (node) => node["@type"] === "Organization"
    );

    expect(organization?.sameAs).toEqual(SITE_SAME_AS);
    expect(SITE_SAME_AS.length).toBeGreaterThan(0);
    for (const url of SITE_SAME_AS) {
      expect(url).toMatch(/^https:\/\/[^\s]+$/);
    }
  });

  it("only states what the site can back up about the organization", () => {
    const organization = buildHomeStructuredData().find(
      (node) => node["@type"] === "Organization"
    );

    expect(Object.keys(organization ?? {}).sort()).toEqual([
      "@context",
      "@type",
      "name",
      "sameAs",
      "url"
    ]);
  });

  it("does not claim ratings or reviews that do not exist", () => {
    const serialized = serializeJsonLd(buildHomeStructuredData());

    expect(serialized).not.toContain("aggregateRating");
    expect(serialized).not.toContain("review");
  });

  it("serializes to JSON that round-trips", () => {
    const nodes = buildHomeStructuredData();

    expect(JSON.parse(serializeJsonLd(nodes))).toEqual(nodes);
  });

  it("escapes the characters that could close the script tag", () => {
    const serialized = serializeJsonLd([{ name: "</script><b>" }]);

    expect(serialized).not.toContain("<");
    expect(JSON.parse(serialized)).toEqual([{ name: "</script><b>" }]);
  });
});
