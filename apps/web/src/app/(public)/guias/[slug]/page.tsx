import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { GUIDES, getGuide } from "@/lib/guides/guides";
import { buildShareMetadata } from "@/lib/seo/share";
import { GuideBlocks } from "@/src/components/guides/guide-blocks";
import { GuideShell } from "@/src/components/guides/guide-shell";

type GuidePageProps = { params: Promise<{ slug: string }> };

// Solo existen las guías de `GUIDES`: cualquier otro slug es un 404, no una página vacía.
export const dynamicParams = false;

export function generateStaticParams() {
  return GUIDES.map((guide) => ({ slug: guide.slug }));
}

export async function generateMetadata({
  params
}: GuidePageProps): Promise<Metadata> {
  const { slug } = await params;
  const guide = getGuide(slug);
  if (!guide) return {};

  const path = `/guias/${guide.slug}`;
  return {
    title: guide.seoTitle,
    description: guide.description,
    alternates: { canonical: path },
    ...buildShareMetadata({
      title: guide.seoTitle,
      description: guide.description,
      path,
      type: "article"
    })
  };
}

export default async function GuidePage({ params }: GuidePageProps) {
  const { slug } = await params;
  const guide = getGuide(slug);
  if (!guide) notFound();

  const related = guide.related
    .map((relatedSlug) => getGuide(relatedSlug))
    .filter((item) => item !== undefined);

  return (
    <GuideShell>
      <Link
        className="text-sm font-medium text-brand-green hover:underline"
        href="/guias"
      >
        ← Todas las guías
      </Link>
      <article>
        <h1 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
          {guide.title}
        </h1>
        <p className="mt-4 text-lg leading-8 text-neutral-700">{guide.intro}</p>

        {guide.sections.map((section) => (
          <section key={section.heading}>
            <h2 className="mt-10 text-2xl font-bold tracking-tight">
              {section.heading}
            </h2>
            <GuideBlocks blocks={section.blocks} />
          </section>
        ))}
      </article>

      <aside className="mt-12 rounded-2xl bg-brand-green-light p-6">
        <h2 className="text-xl font-bold tracking-tight">
          Probá tu CV contra un puesto real
        </h2>
        <p className="mt-2 leading-7 text-neutral-700">
          Cargá tu CV, pegá una oferta y mirá tu match score, las habilidades que faltan y el
          análisis ATS.
        </p>
        <Link
          className="mt-4 inline-block rounded-full bg-brand-bright px-5 py-2.5 text-sm font-semibold text-brand-ink transition-opacity hover:opacity-90"
          href="/register"
        >
          Empezar gratis
        </Link>
      </aside>

      {related.length > 0 ? (
        <nav aria-label="Guías relacionadas" className="mt-12">
          <h2 className="text-xl font-bold tracking-tight">Seguí leyendo</h2>
          <ul className="mt-4 space-y-3">
            {related.map((item) => (
              <li key={item.slug}>
                <Link
                  className="font-semibold text-brand-green hover:underline"
                  href={`/guias/${item.slug}`}
                >
                  {item.title}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}
    </GuideShell>
  );
}
