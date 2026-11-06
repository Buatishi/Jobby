export type GuideBlock =
  | { type: "paragraph"; text: string }
  | { type: "list"; items: string[] }
  | { type: "steps"; items: string[] };

export type GuideSection = {
  heading: string;
  blocks: GuideBlock[];
};

export type Guide = {
  slug: string;
  // Título de la página (h1).
  title: string;
  // Título para Google y la pestaña; incluye la marca y no pasa de 60 caracteres.
  seoTitle: string;
  description: string;
  // Fechas de contenido (AAAA-MM-DD), no del código: `publishedAt` es el día en que la guía
  // llegó a producción y `updatedAt` el del último cambio de su texto o de una cifra que
  // muestra. Hay que subir `updatedAt` cuando cambia alguno de los dos: alimenta la fecha
  // visible, el marcado `Article` y el `lastmod` del sitemap, y un buscador descarta una fecha
  // que no se corresponde con los cambios reales.
  publishedAt: string;
  updatedAt: string;
  intro: string;
  sections: GuideSection[];
  // Slugs de otras guías para enlazar al final.
  related: string[];
};
