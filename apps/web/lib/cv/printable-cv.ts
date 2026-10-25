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
    started_at: string | null;
    ended_at: string | null;
    is_ongoing: boolean;
  }>;
  languages: Array<{ name: string; level: string | null }>;
  certifications: Array<{ name: string; issuer: string | null }>;
};

export type OptimizedSection = {
  section_name: string;
  original_excerpt: string;
  rewritten_text: string;
  unverified_keywords?: string[];
};

const MONTHS = [
  "Ene",
  "Feb",
  "Mar",
  "Abr",
  "May",
  "Jun",
  "Jul",
  "Ago",
  "Sep",
  "Oct",
  "Nov",
  "Dic"
];

// Se lee el texto y no se pasa por Date: «2021-03-01» en una zona con UTC negativo
// sería febrero. Lo que no es una fecha conocida se imprime tal cual lo escribió la
// persona; vacío, no se imprime.
function formatDate(value: string | null): string {
  const text = value?.trim() ?? "";
  const parts = text.match(/^(\d{4})(?:-(\d{2}))?(?:-\d{2})?$/);
  if (!parts) {
    return text;
  }
  const month = parts[2] ? Number(parts[2]) : 0;
  if (month >= 1 && month <= 12) {
    return `${MONTHS[month - 1]} ${parts[1]}`;
  }
  return parts[2] ? text : parts[1];
}

/** «Mar 2021 – Ago 2021», «Jun 2025 – Actualidad»; vacío si no hay fechas. */
export function formatPeriod(
  started: string | null,
  ended: string | null,
  isCurrent: boolean
): string {
  const start = formatDate(started);
  const end = isCurrent ? "Actualidad" : formatDate(ended);
  return start && end ? `${start} – ${end}` : start || end;
}

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
