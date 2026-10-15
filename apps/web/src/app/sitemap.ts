import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/seo/site";

// Sin `lastModified`: con `new Date()` valdría la fecha del build para todas las URLs aunque
// no hayan cambiado, y los buscadores descartan una fecha que no es fiable.
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
