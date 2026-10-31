import { splitSentences } from "@/lib/cv/cv-layout";

export type PrintableCVContact = {
  full_name: string;
  email: string;
  phone: string;
  location: string;
  linkedin_url: string;
};

export type PrintableCV = {
  contact: PrintableCVContact;
  headline: string | null;
  summary: string | null;
  skills: string[];
  experiences: Array<{
    company: string;
    title: string;
    started_at: string | null;
    ended_at: string | null;
    is_current: boolean;
    description: string | null;
    achievements: string[];
  }>;
  educations: Array<{
    institution: string;
    field_of_study: string | null;
    degree_level: string | null;
    // Opcionales: una API desplegada antes que la web no los manda.
    started_at?: string | null;
    ended_at?: string | null;
    is_ongoing?: boolean;
  }>;
  languages: Array<{ name: string; level: string | null }>;
  certifications: Array<{
    name: string;
    issuer: string | null;
    issued_at?: string | null;
  }>;
};

export type OptimizedSection = {
  section_name: string;
  original_excerpt: string;
  rewritten_text: string;
  unverified_keywords?: string[];
};

function squash(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

// Reemplaza el fragmento si aparece en el texto, sin importar saltos de línea ni
// espacios dobles. Devuelve null si no lo encuentra.
function replaceExcerpt(
  text: string | null,
  excerpt: string,
  replacement: string
): string | null {
  if (!text) {
    return null;
  }
  const flatText = squash(text);
  const flatExcerpt = squash(excerpt);
  if (!flatExcerpt || !flatText.includes(flatExcerpt)) {
    return null;
  }
  return flatText.replace(flatExcerpt, squash(replacement));
}

export function splitSkills(text: string): string[] {
  return text
    .split(/[,;\n•·|]/)
    .map((item) => item.trim().replace(/\.$/, ""))
    .filter(Boolean);
}

// Un fragmento tan corto puede estar en cualquier experiencia: no alcanza para decidir
// cuál se reescribe.
const MIN_EXCERPT_LENGTH = 20;
// Casi todo el fragmento tiene que ser lo que ya dicen las viñetas que se reemplazan.
const MIN_EXCERPT_COVERAGE = 0.8;

// Compara textos sin depender de acentos, mayúsculas, signos ni marcas de viñeta.
function looseKey(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

function rewrittenBullets(text: string): string[] {
  const pieces = text
    .split(/[\r\n]+|[•●▪◦]/)
    .map((piece) => piece.replace(/^[\s*–—·-]+/, "").trim())
    .filter(Boolean);
  return pieces.length === 1 ? splitSentences(pieces[0]) : pieces;
}

// El lector guarda una viñeta por logro y la IA suele copiar como «fragmento» varias
// seguidas: ninguna las contiene sola. Si el fragmento es, casi entero, lo que dicen
// la descripción y/o varias viñetas de UNA experiencia, esas viñetas se reemplazan por
// el texto nuevo. Lo que el fragmento no cubre se deja como está.
function placeAcrossBullets(
  experience: PrintableCV["experiences"][number],
  excerpt: string,
  rewritten: string
): boolean {
  const excerptKey = looseKey(excerpt);
  if (excerptKey.length < MIN_EXCERPT_LENGTH) {
    return false;
  }

  const descriptionKey = looseKey(experience.description ?? "");
  const coversDescription =
    descriptionKey !== "" && excerptKey.includes(descriptionKey);
  const covered = experience.achievements.flatMap((achievement, index) => {
    const key = looseKey(achievement);
    return key !== "" && excerptKey.includes(key) ? [{ index, length: key.length }] : [];
  });
  if (!coversDescription && covered.length === 0) {
    return false;
  }

  const coveredLength = covered.reduce(
    (total, item) => total + item.length + 1,
    coversDescription ? descriptionKey.length + 1 : 0
  );
  const bullets = rewrittenBullets(rewritten);
  if (bullets.length === 0 || coveredLength < excerptKey.length * MIN_EXCERPT_COVERAGE) {
    return false;
  }

  const coveredIndexes = new Set(covered.map((item) => item.index));
  const firstCovered = covered[0]?.index;
  const kept: string[] = [];
  for (const [index, achievement] of experience.achievements.entries()) {
    if (index === firstCovered) {
      kept.push(...bullets);
    }
    if (!coveredIndexes.has(index)) {
      kept.push(achievement);
    }
  }
  // Solo la descripción estaba cubierta: las viñetas nuevas ocupan su lugar, arriba.
  experience.achievements = firstCovered === undefined ? [...bullets, ...kept] : kept;
  if (coversDescription) {
    experience.description = null;
  }
  return true;
}

// Una experiencia por línea: sin esto, dos secciones «experiences» no se distinguen.
export function describeSection(section: OptimizedSection): string {
  if (section.section_name === "summary" || section.section_name === "skills") {
    return section.section_name;
  }
  const preview = squash(section.original_excerpt || section.rewritten_text);
  if (!preview) {
    return section.section_name;
  }
  const short = preview.length > 56 ? `${preview.slice(0, 56).trimEnd()}…` : preview;
  return `${section.section_name} «${short}»`;
}

function placeSection(cv: PrintableCV, section: OptimizedSection): boolean {
  const { original_excerpt: excerpt, rewritten_text: rewritten } = section;

  const summary = replaceExcerpt(cv.summary, excerpt, rewritten);
  if (summary !== null) {
    cv.summary = summary;
    return true;
  }

  for (const experience of cv.experiences) {
    const description = replaceExcerpt(experience.description, excerpt, rewritten);
    if (description !== null) {
      experience.description = description;
      return true;
    }
    for (const [index, achievement] of experience.achievements.entries()) {
      const replaced = replaceExcerpt(achievement, excerpt, rewritten);
      if (replaced !== null) {
        experience.achievements[index] = replaced;
        return true;
      }
    }
  }

  for (const experience of cv.experiences) {
    if (placeAcrossBullets(experience, excerpt, rewritten)) {
      return true;
    }
  }

  // Sin el fragmento literal, el resumen y las habilidades se reemplazan enteros:
  // son una sola pieza en el CV. Una experiencia no: se podría pisar otra.
  if (section.section_name === "summary") {
    cv.summary = squash(rewritten);
    return true;
  }
  if (section.section_name === "skills") {
    cv.skills = splitSkills(rewritten);
    return true;
  }
  return false;
}

export function applyOptimizedSections(
  cv: PrintableCV,
  sections: OptimizedSection[]
): { cv: PrintableCV; unplaced: OptimizedSection[] } {
  const result: PrintableCV = structuredClone(cv);
  const unplaced = sections.filter((section) => !placeSection(result, section));
  return { cv: result, unplaced };
}
