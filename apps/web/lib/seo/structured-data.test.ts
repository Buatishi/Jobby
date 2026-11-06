import { describe, expect, it } from "vitest";

import { GUIDES } from "@/lib/guides/guides";
import {
  SITE_ALTERNATE_NAMES,
  SITE_NAME,
  SITE_SAME_AS,
  SITE_URL
} from "@/lib/seo/site";
import {
  buildArticleStructuredData,
  buildBreadcrumbStructuredData,
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

describe("breadcrumb structured data", () => {
  const steps = [
    { name: "Jobby", path: "/" },
    { name: "Guías", path: "/guias" },
    { name: "Qué es un ATS", path: "/guias/que-es-un-ats" }
  ];

  it("lists each step in order with its absolute address", () => {
    const [list] = buildBreadcrumbStructuredData(steps);

    expect(list["@context"]).toBe("https://schema.org");
    expect(list["@type"]).toBe("BreadcrumbList");
    expect(list.itemListElement).toEqual([
      { "@type": "ListItem", position: 1, name: "Jobby", item: SITE_URL },
      { "@type": "ListItem", position: 2, name: "Guías", item: `${SITE_URL}/guias` },
      {
        "@type": "ListItem",
        position: 3,
        name: "Qué es un ATS",
        item: `${SITE_URL}/guias/que-es-un-ats`
      }
    ]);
  });

  it("writes the root without a trailing slash, like the site url and the sitemap", () => {
    const [list] = buildBreadcrumbStructuredData([{ name: "Jobby", path: "/" }]);
    const [root] = list.itemListElement as { item: string }[];

    expect(root.item).toBe(SITE_URL);
    expect(root.item.endsWith("/")).toBe(false);
  });

  it("serializes to JSON that round-trips", () => {
    const nodes = buildBreadcrumbStructuredData(steps);

    expect(JSON.parse(serializeJsonLd(nodes))).toEqual(nodes);
  });
});

describe("article structured data", () => {
  const article = {
    headline: "Qué es un ATS y cómo lee tu CV",
    description: "Qué es un ATS.",
    path: "/guias/que-es-un-ats",
    publishedAt: "2026-10-18",
    updatedAt: "2026-11-02"
  };

  it("describes the guide with its address, headline and the days the page shows", () => {
    const [node] = buildArticleStructuredData(article);

    expect(node["@context"]).toBe("https://schema.org");
    expect(node["@type"]).toBe("Article");
    expect(node.headline).toBe(article.headline);
    expect(node.description).toBe(article.description);
    expect(node.inLanguage).toBe("es");
    expect(node.datePublished).toBe("2026-10-18");
    expect(node.dateModified).toBe("2026-11-02");
    expect(node.mainEntityOfPage).toEqual({
      "@type": "WebPage",
      "@id": `${SITE_URL}/guias/que-es-un-ats`
    });
    expect(node.image).toBe(`${SITE_URL}/og-image.png`);
  });

  it("credits the organization, not a person the page cannot name", () => {
    const [node] = buildArticleStructuredData(article);
    const organization = { "@type": "Organization", name: SITE_NAME, url: SITE_URL };

    expect(node.author).toEqual(organization);
    expect(node.publisher).toEqual(organization);
  });

  it("keeps the headline within the 110 characters search engines read", () => {
    for (const guide of GUIDES) {
      expect(guide.title.length, guide.slug).toBeLessThanOrEqual(110);
    }
  });

  it("does not claim ratings or reviews, and round-trips as JSON", () => {
    const nodes = buildArticleStructuredData(article);

    expect(serializeJsonLd(nodes)).not.toContain("aggregateRating");
    expect(JSON.parse(serializeJsonLd(nodes))).toEqual(nodes);
  });
});
