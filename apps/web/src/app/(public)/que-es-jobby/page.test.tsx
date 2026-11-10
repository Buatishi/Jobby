import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ABOUT_PAGE } from "@/lib/about/about";
import { SITE_URL } from "@/lib/seo/site";
import AboutPage, { metadata } from "@/src/app/(public)/que-es-jobby/page";

type Node = {
  "@type": string;
  name?: string;
  url?: string;
  mainEntity?: { name: string; acceptedAnswer: { text: string } }[];
  itemListElement?: { position: number; name: string; item: string }[];
};

function render() {
  return renderToStaticMarkup(<AboutPage />);
}

// Lee el marcado del buscador del HTML: es lo que recibe.
function markup(html: string): Node[] {
  return [
    ...html.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/g)
  ].flatMap((match) => JSON.parse(match[1].replace(/\\u003c/g, "<")) as Node[]);
}

describe("«Qué es Jobby» page", () => {
  it("has a single h1 that names the product", () => {
    const html = render();

    expect(html.match(/<h1[ >]/g)).toHaveLength(1);
    expect(html).toContain(ABOUT_PAGE.title);
  });

  it("shows every question with its answer", () => {
    const html = render();

    for (const { question, answer } of ABOUT_PAGE.faq) {
      expect(html, question).toContain(question);
      expect(html, answer).toContain(answer.replace(/&/g, "&amp;"));
    }
  });

  it("gives the search engine the same questions and answers the page shows", () => {
    const faq = markup(render()).filter((node) => node["@type"] === "FAQPage");

    expect(faq).toHaveLength(1);
    expect(
      faq[0].mainEntity?.map((item) => [item.name, item.acceptedAnswer.text])
    ).toEqual(ABOUT_PAGE.faq.map((item) => [item.question, item.answer]));
  });

  it("declares the page as an about page of the product, with its address", () => {
    const about = markup(render()).filter((node) => node["@type"] === "AboutPage");

    expect(about).toHaveLength(1);
    expect(about[0].url).toBe(`${SITE_URL}/que-es-jobby`);
    expect(about[0].name).toBe(ABOUT_PAGE.title);
  });

  it("has breadcrumbs Jobby › Qué es Jobby, in the page and in the markup", () => {
    const html = render();
    const crumbs = markup(html).filter((node) => node["@type"] === "BreadcrumbList");

    expect(crumbs).toHaveLength(1);
    expect(crumbs[0].itemListElement?.map((step) => [step.name, step.item])).toEqual([
      ["Jobby", SITE_URL],
      ["Qué es Jobby", `${SITE_URL}/que-es-jobby`]
    ]);
    expect(html).toContain('<nav aria-label="Migas de pan">');
  });

  it("offers the account and links the guides and the pricing", () => {
    const html = render();

    expect(html).toContain('href="/register"');
    expect(html).toContain('href="/pricing"');
    expect(html).toContain('href="/guias/que-es-el-match-score"');
  });

  it("has its own title, description and canonical, and can be indexed", () => {
    expect(metadata.title).toBe(ABOUT_PAGE.seoTitle);
    expect(metadata.description).toBe(ABOUT_PAGE.description);
    expect(metadata.alternates?.canonical).toBe("/que-es-jobby");
    expect(metadata.robots).toBeUndefined();
    expect(metadata.openGraph?.url).toBe(`${SITE_URL}/que-es-jobby`);
  });
});
