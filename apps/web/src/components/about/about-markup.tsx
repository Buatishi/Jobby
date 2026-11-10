import {
  buildAboutPageStructuredData,
  buildFaqStructuredData,
  serializeJsonLd,
  type AboutPageInput,
  type FaqItem
} from "@/lib/seo/structured-data";

// Marcado `AboutPage` y `FAQPage` de «Qué es Jobby». Sale de los mismos datos que la página
// muestra, y `serializeJsonLd` escapa `<` para que ningún valor cierre la etiqueta <script>.
export function AboutMarkup({ about, faq }: { about: AboutPageInput; faq: FaqItem[] }) {
  return (
    <>
      <script
        dangerouslySetInnerHTML={{
          __html: serializeJsonLd(buildAboutPageStructuredData(about))
        }}
        type="application/ld+json"
      />
      <script
        dangerouslySetInnerHTML={{ __html: serializeJsonLd(buildFaqStructuredData(faq)) }}
        type="application/ld+json"
      />
    </>
  );
}
