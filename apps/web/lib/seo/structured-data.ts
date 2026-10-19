import { SITE_NAME, SITE_SAME_AS, SITE_URL } from "@/lib/seo/site";

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
      alternateName: [`${SITE_NAME} web`],
      url: SITE_URL,
      inLanguage: "es"
    },
    {
      "@context": "https://schema.org",
      "@type": "WebApplication",
      name: SITE_NAME,
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

// `<` se escapa para que ningún valor pueda cerrar la etiqueta <script> donde se inserta.
export function serializeJsonLd(nodes: JsonLdNode[]): string {
  return JSON.stringify(nodes).replace(/</g, "\\u003c");
}
