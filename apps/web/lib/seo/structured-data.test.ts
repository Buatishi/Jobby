import { describe, expect, it } from "vitest";

import {
  SITE_ALTERNATE_NAMES,
  SITE_NAME,
  SITE_SAME_AS,
  SITE_URL
} from "@/lib/seo/site";
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

  it("names the site and the app with the spellings people search for", () => {
    const nodes = buildHomeStructuredData();

    for (const type of ["WebSite", "WebApplication"]) {
      const node = nodes.find((item) => item["@type"] === type);

      expect(node?.alternateName, type).toEqual(["Jobby web", "JobbyWeb"]);
    }
  });

  it("keeps every alternate name different from the main name and from the others", () => {
    expect(new Set(SITE_ALTERNATE_NAMES).size).toBe(SITE_ALTERNATE_NAMES.length);
    expect(SITE_ALTERNATE_NAMES).not.toContain(SITE_NAME);
    // El dominio lleva el nombre junto y en minúsculas: una de las variantes tiene que coincidir.
    const host = new URL(SITE_URL).hostname.split(".")[0];
    expect(SITE_ALTERNATE_NAMES.map((name) => name.toLowerCase())).toContain(host);
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
