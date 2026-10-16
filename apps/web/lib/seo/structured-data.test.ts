import { describe, expect, it } from "vitest";

import { SITE_URL } from "@/lib/seo/site";
import {
  buildHomeStructuredData,
  serializeJsonLd
} from "@/lib/seo/structured-data";

describe("home structured data", () => {
  it("describes the site and the app with the public url", () => {
    const nodes = buildHomeStructuredData();

    expect(nodes.map((node) => node["@type"])).toEqual([
      "WebSite",
      "WebApplication"
    ]);
    for (const node of nodes) {
      expect(node["@context"]).toBe("https://schema.org");
      expect(node.url).toBe(SITE_URL);
      expect(node.name).toBe("Jobby");
    }
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
