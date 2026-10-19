import type { Metadata } from "next";

import { SITE_NAME, SITE_URL } from "@/lib/seo/site";

// `openGraph` y `twitter` de una página reemplazan a los del layout raíz en vez de mezclarse:
// sin esto una página heredaría el título y la URL de la home. Llevan la imagen y el sitio
// completos para que la tarjeta al compartir no quede sin ellos.
export function buildShareMetadata({
  title,
  description,
  path,
  type = "website"
}: {
  title: string;
  description: string;
  path: string;
  type?: "website" | "article";
}): Pick<Metadata, "openGraph" | "twitter"> {
  return {
    openGraph: {
      title,
      description,
      url: `${SITE_URL}${path}`,
      siteName: SITE_NAME,
      type,
      images: ["/og-image.png"]
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: ["/og-image.png"]
    }
  };
}
