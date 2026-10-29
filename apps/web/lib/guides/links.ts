// Enlaces del pie de la home a cada guía. Viven aparte de `guides.ts` para no meter el texto
// completo de las guías en el JavaScript de la home: el pie es un componente de cliente.
// Las guías son solo en español, así que la etiqueta no se traduce, igual que sus títulos.
// `guides.test.ts` comprueba que cada guía tenga su enlace y que no sobre ninguno.
export const GUIDE_LINKS = [
  { slug: "que-es-un-ats", label: "Qué es un ATS" },
  { slug: "que-es-el-match-score", label: "Qué es el match score" },
  {
    slug: "como-adaptar-tu-cv-a-una-oferta",
    label: "Cómo adaptar tu CV a una oferta"
  },
  { slug: "palabras-clave-del-cv", label: "Palabras clave del CV" },
  { slug: "cv-compatible-con-ats", label: "CV compatible con ATS" },
  { slug: "analizar-cv-con-ia", label: "Analizar tu CV con IA" },
  { slug: "optimizar-cv-con-ia", label: "Optimizar el CV con IA" },
  { slug: "habilidades-para-poner-en-el-cv", label: "Habilidades para el CV" }
] as const;
