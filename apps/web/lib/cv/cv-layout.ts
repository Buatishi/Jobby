// Piezas del CV descargable que no son de diseño: fechas, viñetas y la grilla de
// habilidades. Viven acá para probarse sin renderizar (Decisión 26).

const MONTHS = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre"
];

/**
 * «2026-07-01» es «Julio 2026» y «2020» queda «2020». El lector de CV guarda la fecha
 * como el CV la escribe («Julio 2026»): si no es una fecha ISO, se deja tal cual.
 */
export function formatMonthYear(value: string | null | undefined): string {
  const text = (value ?? "").trim();
  const match = /^(\d{4})(?:-(\d{2})(?:-\d{2})?)?(?:T.*)?$/.exec(text);
  if (!match) {
    return text;
  }
  const [, year, month] = match;
  const index = month ? Number(month) - 1 : -1;
  return index >= 0 && index < MONTHS.length ? `${MONTHS[index]} ${year}` : year;
}

/** «Julio 2026 - Presente»; con una sola fecha, solo esa. */
export function formatPeriod(
  started: string | null | undefined,
  ended: string | null | undefined,
  ongoing: boolean,
  ongoingLabel: string
): string {
  const start = formatMonthYear(started);
  const end = ongoing ? ongoingLabel : formatMonthYear(ended);
  return start && end ? `${start} - ${end}` : start || end;
}

// Abreviaturas que terminan en punto sin cerrar la oración: «Jr. Developer».
const ENDS_WITH_ABBREVIATION = /\b(?:jr|sr|ssr|ing|lic|dr|dra|sra|etc|ej|vs|inc)\.$/i;

/**
 * El lector del CV junta las viñetas de una experiencia en un solo párrafo. Se
 * separan por renglón y, dentro del renglón, donde una oración termina y empieza otra
 * con mayúscula, sin cortar después de una abreviatura.
 */
export function splitSentences(text: string): string[] {
  const sentences: string[] = [];
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.replace(/^[\s•·*–-]+/, "").trim();
    if (!line) {
      continue;
    }
    const merged: string[] = [];
    for (const part of line.split(/(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÜÑ¿¡])/)) {
      const last = merged.at(-1);
      if (last !== undefined && ENDS_WITH_ABBREVIATION.test(last)) {
        merged[merged.length - 1] = `${last} ${part}`;
      } else {
        merged.push(part);
      }
    }
    sentences.push(...merged);
  }
  return sentences;
}

/** Una viñeta por oración de la descripción, y después cada logro cargado. */
export function experienceBullets(experience: {
  description: string | null;
  achievements: string[];
}): string[] {
  return [
    ...splitSentences(experience.description ?? ""),
    ...experience.achievements.map((item) => item.trim()).filter(Boolean)
  ];
}

// Tres columnas por cuatro filas: más de eso se agrupa con « / » para que la grilla
// no empuje la experiencia a una segunda página.
export const MAX_SKILL_CELLS = 12;

/**
 * Celdas de «Habilidades y competencias»: una por habilidad, con los idiomas en la
 * última («Español Nativo / Inglés B2»), como en el modelo de CV.
 */
export function skillCells(
  skills: string[],
  languages: Array<{ name: string; level: string | null }>
): string[] {
  const languageCell = languages
    .filter((language) => language.name.trim())
    .map((language) =>
      language.level ? `${language.name} ${language.level}` : language.name
    )
    .join(" / ");
  const names = skills.map((skill) => skill.trim()).filter(Boolean);
  const room = Math.max(1, MAX_SKILL_CELLS - (languageCell ? 1 : 0));
  const size = Math.max(1, Math.ceil(names.length / room));

  const cells: string[] = [];
  for (let index = 0; index < names.length; index += size) {
    cells.push(names.slice(index, index + size).join(" / "));
  }
  if (languageCell) {
    cells.push(languageCell);
  }
  return cells;
}
