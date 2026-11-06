import type { MetadataRoute } from "next";

import { GUIDES } from "@/lib/guides/guides";
import { SITE_URL } from "@/lib/seo/site";

// `lastModified` solo en las guías, y con la fecha de su último cambio de contenido
// (`updatedAt`). Con `new Date()` valdría la del build para todas las URLs aunque no hayan
// cambiado, y los buscadores descartan una fecha que no es fiable: las demás páginas no tienen
// una fecha de contenido registrada, así que no llevan ninguna.
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: SITE_URL,
      changeFrequency: "weekly",
      priority: 1
    },
    {
      url: `${SITE_URL}/pricing`,
      changeFrequency: "monthly",
      priority: 0.8
    },
    {
      url: `${SITE_URL}/guias`,
      changeFrequency: "monthly",
      priority: 0.7
    },
    ...GUIDES.map((guide) => ({
      url: `${SITE_URL}/guias/${guide.slug}`,
      lastModified: guide.updatedAt,
      changeFrequency: "monthly" as const,
      priority: 0.6
    })),
    {
      url: `${SITE_URL}/terms`,
      changeFrequency: "yearly",
      priority: 0.4
    },
    {
      url: `${SITE_URL}/privacy`,
      changeFrequency: "yearly",
      priority: 0.4
    }
  ];
}
