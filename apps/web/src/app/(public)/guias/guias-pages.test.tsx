import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { GUIDES, getGuide } from "@/lib/guides/guides";
import { SITE_URL } from "@/lib/seo/site";
import GuidePage, {
  dynamicParams,
  generateMetadata,
  generateStaticParams
} from "@/src/app/(public)/guias/[slug]/page";
import GuidesIndexPage, {
  metadata as indexMetadata
} from "@/src/app/(public)/guias/page";

async function renderGuide(slug: string) {
  return renderToStaticMarkup(await GuidePage({ params: Promise.resolve({ slug }) }));
}

describe("guides index", () => {
  const html = renderToStaticMarkup(<GuidesIndexPage />);

  it("links to every guide", () => {
    for (const guide of GUIDES) {
      expect(html).toContain(`href="/guias/${guide.slug}"`);
      expect(html).toContain(guide.title);
    }
  });

  it("has a single h1 and a self canonical", () => {
    expect(html.match(/<h1/g)).toHaveLength(1);
    expect(indexMetadata.alternates?.canonical).toBe("/guias");
    expect(String(indexMetadata.title)).toContain("Jobby");
  });

  it("shares its own address and title, not the home's", () => {
    expect(indexMetadata.openGraph).toMatchObject({
      url: `${SITE_URL}/guias`,
      title: indexMetadata.title,
      siteName: "Jobby",
      images: ["/og-image.png"]
    });
    expect(indexMetadata.twitter).toMatchObject({
      title: indexMetadata.title,
      images: ["/og-image.png"]
    });
  });
});

describe("guide pages", () => {
  it("prerenders exactly the known guides and 404s anything else", async () => {
    expect(dynamicParams).toBe(false);
    expect(generateStaticParams()).toEqual(
      GUIDES.map((guide) => ({ slug: guide.slug }))
    );
    await expect(renderGuide("no-existe")).rejects.toMatchObject({
      digest: expect.stringContaining("404")
    });
  });

  it.each(GUIDES.map((guide) => guide.slug))(
    "%s: ships its text in the server markup",
    async (slug) => {
      const guide = getGuide(slug)!;
      const html = await renderGuide(slug);

      expect(html.match(/<h1/g)).toHaveLength(1);
      expect(html).toContain(guide.title);
      for (const section of guide.sections) {
        expect(html).toContain(section.heading);
      }
    }
  );

  it.each(GUIDES.map((guide) => guide.slug))(
    "%s: links back to the index, to its related guides and to sign up",
    async (slug) => {
      const guide = getGuide(slug)!;
      const html = await renderGuide(slug);

      expect(html).toContain('href="/guias"');
      expect(html).toContain('href="/register"');
      for (const related of guide.related) {
        expect(html).toContain(`href="/guias/${related}"`);
      }
    }
  );

  it.each(GUIDES.map((guide) => guide.slug))(
    "%s: sets its own canonical, title and share card",
    async (slug) => {
      const guide = getGuide(slug)!;
      const metadata = await generateMetadata({ params: Promise.resolve({ slug }) });

      expect(metadata.title).toBe(guide.seoTitle);
      expect(metadata.description).toBe(guide.description);
      expect(metadata.alternates?.canonical).toBe(`/guias/${slug}`);
      expect(metadata.openGraph).toMatchObject({
        url: `${SITE_URL}/guias/${slug}`,
        siteName: "Jobby",
        images: ["/og-image.png"]
      });
      expect(metadata.twitter).toMatchObject({ images: ["/og-image.png"] });
    }
  );

  it("returns no metadata for an unknown guide", async () => {
    expect(
      await generateMetadata({ params: Promise.resolve({ slug: "no-existe" }) })
    ).toEqual({});
  });

  it("prints the match score weights the formula uses", async () => {
    const html = await renderGuide("que-es-el-match-score");

    for (const label of ["Habilidades", "Seniority", "Empresa", "Educación", "Idiomas"]) {
      expect(html).toContain(label);
    }
    expect(html).toContain("35 %");
    expect(html).toContain("25 %");
  });
});
