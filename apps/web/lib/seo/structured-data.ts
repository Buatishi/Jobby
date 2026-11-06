import {
  SITE_ALTERNATE_NAMES,
  SITE_NAME,
  SITE_SAME_AS,
  SITE_URL
} from "@/lib/seo/site";

export type JsonLdNode = Record<string, unknown>;

// Datos estructurados de la home. Solo afirma lo que el producto ya muestra: sin
// valoraciones ni reseñas, que serían datos inventados. La organización lleva solo nombre,
// URL y `sameAs`: no hay logo propio ni datos de contacto públicos que declarar.
export function buildHomeStructuredData(): JsonLdNode[] {
  return [
    {
      "@context": "https://schema.org",
      "@type": "WebSite",
      name: SITE_NAME,
      alternateName: SITE_ALTERNATE_NAMES,
      url: SITE_URL,
      inLanguage: "es"
    },
    {
      "@context": "https://schema.org",
      "@type": "WebApplication",
      name: SITE_NAME,
      alternateName: SITE_ALTERNATE_NAMES,
      url: SITE_URL,
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      inLanguage: ["es", "en"],
      description:
        "Compara tu CV con un puesto real y calcula el match score, la compatibilidad ATS y los gaps antes de postularte.",
      offers: {
        "@type": "Offer",
        description: "Plan gratuito",
        price: "0",
        priceCurrency: "USD"
      }
    },
    {
      "@context": "https://schema.org",
      "@type": "Organization",
      name: SITE_NAME,
      url: SITE_URL,
      sameAs: SITE_SAME_AS
    }
  ];
}

export type BreadcrumbStep = { name: string; path: string };

// Ruta de una página dentro del sitio (Jobby › Guías › título) para el buscador. El marcado
// tiene que coincidir con las migas que la persona ve: por eso `GuideBreadcrumbs` pinta la
// lista y genera esto desde el mismo arreglo. La raíz se escribe sin barra final, igual que
// `SITE_URL` y el sitemap.
export function buildBreadcrumbStructuredData(
  steps: BreadcrumbStep[]
): JsonLdNode[] {
  return [
    {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: steps.map((step, index) => ({
        "@type": "ListItem",
        position: index + 1,
        name: step.name,
        item: step.path === "/" ? SITE_URL : `${SITE_URL}${step.path}`
      }))
    }
  ];
}

export type ArticleInput = {
  headline: string;
  description: string;
  path: string;
  // AAAA-MM-DD, las mismas que la página muestra.
  publishedAt: string;
  updatedAt: string;
};

// Marcado `Article` de una guía. Autor y editor son la organización: no hay una persona que la
// página pueda declarar como autora sin inventarlo. Las fechas son las visibles en la página.
export function buildArticleStructuredData(article: ArticleInput): JsonLdNode[] {
  const organization = { "@type": "Organization", name: SITE_NAME, url: SITE_URL };

  return [
    {
      "@context": "https://schema.org",
      "@type": "Article",
      headline: article.headline,
      description: article.description,
      inLanguage: "es",
      datePublished: article.publishedAt,
      dateModified: article.updatedAt,
      mainEntityOfPage: { "@type": "WebPage", "@id": `${SITE_URL}${article.path}` },
      image: `${SITE_URL}/og-image.png`,
      author: organization,
      publisher: organization
    }
  ];
}

// `<` se escapa para que ningún valor pueda cerrar la etiqueta <script> donde se inserta.
export function serializeJsonLd(nodes: JsonLdNode[]): string {
  return JSON.stringify(nodes).replace(/</g, "\\u003c");
}
