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
  intro: string;
  sections: GuideSection[];
  // Slugs de otras guías para enlazar al final.
  related: string[];
};
