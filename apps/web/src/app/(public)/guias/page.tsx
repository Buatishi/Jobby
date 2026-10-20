import type { Metadata } from "next";
import Link from "next/link";

import { GUIDES } from "@/lib/guides/guides";
import { buildShareMetadata } from "@/lib/seo/share";
import { GuideShell } from "@/src/components/guides/guide-shell";

const title = "Guías para tu CV y tus postulaciones | Jobby";
const description =
  "Guías de Jobby sobre ATS, match score, palabras clave y habilidades, y cómo analizar, adaptar y optimizar tu CV con IA para cada oferta.";

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: "/guias" },
  ...buildShareMetadata({ title, description, path: "/guias" })
};

export default function GuidesIndexPage() {
  return (
    <GuideShell>
      <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
        Guías para tu CV y tus postulaciones
      </h1>
      <p className="mt-4 text-lg leading-8 text-neutral-700">
        Cómo lee tu CV un sistema de selección, cómo se calcula el match score y cómo adaptar tu
        perfil a cada oferta, explicado paso a paso.
      </p>

      <ul className="mt-10 space-y-4">
        {GUIDES.map((guide) => (
          <li key={guide.slug}>
            <Link
              className="block rounded-2xl border border-brand-line p-6 transition-colors hover:bg-brand-green-light"
              href={`/guias/${guide.slug}`}
            >
              <h2 className="text-xl font-bold tracking-tight">{guide.title}</h2>
              <p className="mt-2 leading-7 text-neutral-700">{guide.description}</p>
            </Link>
          </li>
        ))}
      </ul>
    </GuideShell>
  );
}
