import {
  buildArticleStructuredData,
  serializeJsonLd,
  type ArticleInput
} from "@/lib/seo/structured-data";

// Marcado `Article` de una guía. Sale de los mismos datos que la página muestra, y
// `serializeJsonLd` escapa `<` para que ningún valor cierre la etiqueta <script>.
export function GuideArticleMarkup({ article }: { article: ArticleInput }) {
  return (
    <script
      dangerouslySetInnerHTML={{
        __html: serializeJsonLd(buildArticleStructuredData(article))
      }}
      type="application/ld+json"
    />
  );
}
