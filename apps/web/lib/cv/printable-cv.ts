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
