// Cifras del producto que las guías citan. Viven acá y no dentro del texto para que
// `guides.test.ts` las compare con el código del backend: si la fórmula cambia y la guía
// no, el test falla en vez de publicar un número viejo.

// `services/api/app/services/match_engine/formula.py` (`_weighted_score`).
export const MATCH_SCORE_WEIGHTS = [
  {
    key: "skills",
    label: "Habilidades",
    percent: 35,
    detail:
      "cuántas de las habilidades que pide el puesto están en tu perfil. Cuentan las coincidencias exactas, las variantes conocidas y las de significado parecido."
  },
  {
    key: "seniority",
    label: "Seniority",
    percent: 25,
    detail:
      "tu nivel buscado (junior, semi senior, senior y más) frente al que pide el puesto. Tener el nivel pedido o uno mayor casi no resta; estar por debajo resta más cuanto más lejos."
  },
  {
    key: "company",
    label: "Empresa",
    percent: 15,
    detail:
      "qué tan bien encajás con la empresa: las tecnologías del puesto frente a las tuyas y la modalidad de trabajo, remoto, híbrido o presencial."
  },
  {
    key: "education",
    label: "Educación",
    percent: 10,
    detail:
      "tus estudios, su nivel y su relación con el puesto, más las certificaciones y los estudios en curso."
  },
  {
    key: "languages",
    label: "Idiomas",
    percent: 10,
    detail: "los idiomas y el nivel que pide el puesto frente a los tuyos."
  },
  {
    key: "soft",
    label: "Habilidades blandas",
    percent: 5,
    detail:
      "las que se detectan en la descripción y en los logros de tu experiencia, como liderazgo o comunicación, frente a las que pide el puesto."
  }
] as const;

// `s_relevance.py` (`FULL_RELEVANCE_AT`): con esta fracción de las habilidades pedidas en el
// perfil, el puesto cuenta como del área de la persona y el puntaje no se atenúa.
export const FULL_RELEVANCE_PERCENT = 25;

// `formula.py` (`_gap_origin`): por debajo de este valor un componente se marca como brecha.
export const GAP_THRESHOLD_PERCENT = 70;

// `ats_analyzer/scoring.py` (`WEIGHT_*`): proporción de cada parte del contenido del puntaje ATS.
export const ATS_CONTENT_WEIGHTS = {
  skills: 60,
  experience: 20,
  education: 10,
  languages: 10
} as const;

// `ats_analyzer/scoring.py` (`FORMAT_POINTS` y `CONTENT_POINTS`): del total de 100, el formato del
// archivo vale 10 y el contenido, 90. El formato es una estimación propia del riesgo de lectura,
// una convención de Jobby y no el puntaje de ningún ATS real.
export const ATS_FORMAT_POINTS = 10;
export const ATS_CONTENT_POINTS = 90;

// `ats_analyzer/format_checker.py` (`PENALTY_*`): cuántos de los 10 puntos de formato resta cada aviso.
export const ATS_FORMAT_PENALTIES = {
  columns: 4,
  images: 3,
  tables: 3
} as const;

const contentShare = (weight: number) => (weight * ATS_CONTENT_POINTS) / 100;

// Lo que vale cada parte cuando el puesto pide todo: 54, 18, 9 y 9 del contenido y 10 del formato.
export const ATS_SCORE_WEIGHTS = {
  skills: contentShare(ATS_CONTENT_WEIGHTS.skills),
  experience: contentShare(ATS_CONTENT_WEIGHTS.experience),
  education: contentShare(ATS_CONTENT_WEIGHTS.education),
  languages: contentShare(ATS_CONTENT_WEIGHTS.languages),
  format: ATS_FORMAT_POINTS
};

// `ats_analyzer/scoring.py` (`LITERAL_POINTS` y `SEMANTIC_POINTS`): lo que suma cada palabra clave.
export const ATS_KEYWORD_POINTS = { literal: 1, semantic: 0.5 } as const;

// `ats_analyzer/scoring.py` (`NICE_TO_HAVE_WEIGHT`): cuánto pesa, frente a una obligatoria,
// una palabra clave que el aviso presenta como deseable.
export const ATS_NICE_TO_HAVE_WEIGHT = 0.5;

// `services/api/app/services/rate_limits.py` (`_rule`): análisis de puestos del plan gratis por
// mes y optimizaciones de CV por mes de cada plan.
export const FREE_JOB_ANALYSES_PER_MONTH = 10;
export const CV_OPTIMIZATIONS_PER_MONTH = { free: 3, premium: 30 } as const;

export function formatPercent(value: number): string {
  return `${value} %`;
}

// «0,5» con coma decimal, como se escribe en español.
export function formatPoints(value: number): string {
  return String(value).replace(".", ",");
}
