import type { Metadata } from "next";
import Link from "next/link";

import { ABOUT_PAGE, ABOUT_SLUG, ABOUT_UPDATED_AT } from "@/lib/about/about";
import { formatGuideDate } from "@/lib/guides/dates";
import { buildShareMetadata } from "@/lib/seo/share";
import { AboutMarkup } from "@/src/components/about/about-markup";
import { GuideBlocks } from "@/src/components/guides/guide-blocks";
import { GuideBreadcrumbs } from "@/src/components/guides/guide-breadcrumbs";
import { GuideShell } from "@/src/components/guides/guide-shell";

const path = `/${ABOUT_SLUG}`;

export const metadata: Metadata = {
  title: ABOUT_PAGE.seoTitle,
  description: ABOUT_PAGE.description,
  alternates: { canonical: path },
  ...buildShareMetadata({
    title: ABOUT_PAGE.seoTitle,
    description: ABOUT_PAGE.description,
    path
  })
};

// Qué es Jobby: una descripción completa y citable del producto. Usa el marco de las guías.
export default function AboutPage() {
  return (
    <GuideShell>
      <GuideBreadcrumbs
        steps={[
          { name: "Jobby", path: "/" },
          { name: "Qué es Jobby", path }
        ]}
      />
      <AboutMarkup
        about={{
          name: ABOUT_PAGE.title,
          description: ABOUT_PAGE.description,
          path,
          updatedAt: ABOUT_UPDATED_AT
        }}
        faq={ABOUT_PAGE.faq}
      />
      <article>
        <h1 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
          {ABOUT_PAGE.title}
        </h1>
        <p className="mt-3 text-sm font-medium text-neutral-600">
          Actualizada el{" "}
          <time dateTime={ABOUT_UPDATED_AT}>{formatGuideDate(ABOUT_UPDATED_AT)}</time>
        </p>
        <p className="mt-4 text-lg leading-8 text-neutral-700">{ABOUT_PAGE.intro}</p>

        {ABOUT_PAGE.sections.map((section) => (
          <section key={section.heading}>
            <h2 className="mt-10 text-2xl font-bold tracking-tight">{section.heading}</h2>
            <GuideBlocks blocks={section.blocks} />
          </section>
        ))}

        <section>
          <h2 className="mt-10 text-2xl font-bold tracking-tight">Preguntas frecuentes</h2>
          {ABOUT_PAGE.faq.map((item) => (
            <div key={item.question}>
              <h3 className="mt-6 text-lg font-semibold tracking-tight">{item.question}</h3>
              <p className="mt-2 leading-7 text-neutral-700">{item.answer}</p>
            </div>
          ))}
        </section>
      </article>

      <aside className="mt-12 rounded-2xl bg-brand-green-light p-6">
        <h2 className="text-xl font-bold tracking-tight">Probá tu CV contra un puesto real</h2>
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

      <nav aria-label="Seguí leyendo" className="mt-12">
        <h2 className="text-xl font-bold tracking-tight">Seguí leyendo</h2>
        <ul className="mt-4 space-y-3">
          {ABOUT_PAGE.links.map((item) => (
            <li key={item.path}>
              <Link className="font-semibold text-brand-green hover:underline" href={item.path}>
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </GuideShell>
  );
}
