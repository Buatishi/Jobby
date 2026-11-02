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
  /** La experiencia del CV a la que se refiere una sección `experiences` (la API la resuelve). */
  target_company?: string;
  target_title?: string;
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
  const target = [section.target_company, section.target_title]
    .map((part) => squash(part ?? ""))
    .filter(Boolean)
    .join(" — ");
  const preview = target || squash(section.original_excerpt || section.rewritten_text);
  if (!preview) {
    return section.section_name;
  }
  const short = preview.length > 56 ? `${preview.slice(0, 56).trimEnd()}…` : preview;
  return `${section.section_name} «${short}»`;
}

type Experience = PrintableCV["experiences"][number];

// «Marzo 2026», «Jan 2024»: una fecha escrita con el mes.
const MONTH_START =
  /^(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre|january|february|march|april|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec|ene|abr|ago|dic)( \d{4})?$/;

// Una parte de «cargo | empresa | fechas | viñetas» que es el encabezado y no una viñeta.
function isHeaderPart(part: string, experience: Experience): boolean {
  const key = looseKey(part);
  if (!key || /^\d{4}([-/]\d{1,2})?(\s|$)/.test(part.trim())) {
    return true;
  }
  if (MONTH_START.test(key)) {
    return true;
  }
  if (/\b(presente|actual|actualidad|present)\b/i.test(part)) {
    return true;
  }
  const words = key.split(" ").length;
  return [experience.title, experience.company].some((reference) => {
    const referenceKey = looseKey(reference);
    if (!referenceKey) {
      return false;
    }
    // Un tramo del cargo o la empresa, o ellos con poco más (el año, «a»): no una viñeta.
    return (
      key === referenceKey ||
      (key.length >= 3 && referenceKey.includes(key)) ||
      (key.includes(referenceKey) && words <= referenceKey.split(" ").length + 2)
    );
  });
}

// La IA suele devolver el texto nuevo como un registro: «cargo | empresa | fechas |
// viñeta; viñeta». Se saca el encabezado y quedan las viñetas, una por renglón.
function experienceBulletsFrom(text: string, experience: Experience): string[] {
  let body = text;
  if (text.includes("|")) {
    const parts = text.split("|").map((part) => part.trim());
    let start = 0;
    while (start < parts.length && isHeaderPart(parts[start], experience)) {
      start += 1;
    }
    body = parts.slice(start).join("\n");
    // Con el encabezado afuera, «a; b; c» son tres viñetas.
    const pieces = body.split(/;\s+/).filter((piece) => piece.trim().length >= 15);
    if (!body.includes("\n") && pieces.length >= 2) {
      body = pieces.join("\n");
    }
  }
  return rewrittenBullets(body);
}

function findTarget(cv: PrintableCV, section: OptimizedSection): Experience | null {
  const titleKey = looseKey(section.target_title ?? "");
  const companyKey = looseKey(section.target_company ?? "");
  if (!titleKey && !companyKey) {
    return null;
  }
  const related = (key: string, other: string) =>
    Boolean(key) && Boolean(other) && (other.includes(key) || key.includes(other));
  const candidates = cv.experiences.filter((experience) => {
    const title = looseKey(experience.title);
    const company = looseKey(experience.company);
    const sameTitle = titleKey ? related(titleKey, title) : true;
    const sameCompany = companyKey && company ? related(companyKey, company) : true;
    return sameTitle && sameCompany && (Boolean(titleKey && title) || Boolean(companyKey && company));
  });
  const exact = candidates.filter(
    (experience) =>
      looseKey(experience.title) === titleKey &&
      looseKey(experience.company) === companyKey
  );
  const pool = exact.length > 0 ? exact : candidates;
  return pool.length === 1 ? pool[0] : null;
}

// null: la sección no dice a qué experiencia se refiere; false: se refiere a una pero
// no hay viñetas que poner (no se toca nada).
function placeByTarget(cv: PrintableCV, section: OptimizedSection): boolean | null {
  const target = findTarget(cv, section);
  if (target === null) {
    return null;
  }
  const bullets = experienceBulletsFrom(section.rewritten_text, target);
  if (bullets.length === 0) {
    return false;
  }
  target.achievements = bullets;
  target.description = null;
  return true;
}

function placeSection(cv: PrintableCV, section: OptimizedSection): boolean {
  const { original_excerpt: excerpt, rewritten_text: rewritten } = section;

  if (section.section_name === "experiences") {
    const byTarget = placeByTarget(cv, section);
    if (byTarget !== null) {
      return byTarget;
    }
  }

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
