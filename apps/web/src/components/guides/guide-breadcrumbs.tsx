import Link from "next/link";

import {
  buildBreadcrumbStructuredData,
  serializeJsonLd,
  type BreadcrumbStep
} from "@/lib/seo/structured-data";

// Migas de pan de las guías. La lista visible y el marcado para el buscador salen del mismo
// arreglo, así no pueden decir cosas distintas. El último paso es la página actual: no es un
// enlace.
export function GuideBreadcrumbs({ steps }: { steps: BreadcrumbStep[] }) {
  return (
    <>
      <script
        dangerouslySetInnerHTML={{
          __html: serializeJsonLd(buildBreadcrumbStructuredData(steps))
        }}
        type="application/ld+json"
      />
      <nav aria-label="Migas de pan">
        <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
          {steps.map((step, index) => (
            <li className="flex items-center gap-2" key={step.path}>
              {index > 0 ? (
                <span aria-hidden="true" className="text-neutral-400">
                  ›
                </span>
              ) : null}
              {index === steps.length - 1 ? (
                <span aria-current="page" className="font-medium text-neutral-600">
                  {step.name}
                </span>
              ) : (
                <Link
                  className="font-medium text-brand-green hover:underline"
                  href={step.path}
                >
                  {step.name}
                </Link>
              )}
            </li>
          ))}
        </ol>
      </nav>
    </>
  );
}
