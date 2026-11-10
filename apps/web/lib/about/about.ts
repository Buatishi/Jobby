import {
  ATS_CONTENT_POINTS,
  ATS_FORMAT_POINTS,
  ATS_KEYWORD_POINTS,
  CV_OPTIMIZATIONS_PER_MONTH,
  FREE_JOB_ANALYSES_PER_MONTH,
  MATCH_SCORE_WEIGHTS,
  formatPercent,
  formatPoints
} from "@/lib/guides/facts";
import type { GuideSection } from "@/lib/guides/types";

// Qué es Jobby, en un solo lugar y con las palabras con las que la gente lo pregunta. La
// página existe para que un buscador o un asistente de IA tenga una descripción clara y
// completa que citar. Las cifras salen de `lib/guides/facts.ts`, que `guides.test.ts` compara
// con el código del backend: si el producto cambia, `about.test.ts` falla en vez de publicar
// un número viejo. Hay que subir `ABOUT_UPDATED_AT` cuando cambia el texto o una cifra.
export const ABOUT_SLUG = "que-es-jobby";
export const ABOUT_UPDATED_AT = "2026-11-10";

export type AboutFaqItem = { question: string; answer: string };
export type AboutLink = { label: string; path: string };

export type AboutPageContent = {
  title: string;
  // Título para Google y la pestaña; incluye la marca y no pasa de 60 caracteres.
  seoTitle: string;
  description: string;
  intro: string;
  sections: GuideSection[];
  faq: AboutFaqItem[];
  links: AboutLink[];
};

const weightsSummary = MATCH_SCORE_WEIGHTS.map(
  (weight) => `${weight.label} (${formatPercent(weight.percent)})`
).join(", ");

export const ABOUT_PAGE: AboutPageContent = {
  title: "Qué es Jobby web",
  seoTitle: "Qué es Jobby web: analizador de CV con IA | Jobby",
  description:
    "Jobby web es un analizador de CV con IA: compara tu CV con un puesto y calcula el match score, el análisis ATS y las habilidades que te faltan.",
  intro:
    "Jobby web es una aplicación web que compara tu CV con un puesto real antes de que te postules. Calcula un match score de 0 a 100, un análisis de compatibilidad con los sistemas de seguimiento de candidatos (ATS) y las habilidades que te faltan, y te dice qué mejorar. Funciona en español y en inglés y tiene un plan gratuito.",
  sections: [
    {
      heading: "Qué hace Jobby",
      blocks: [
        {
          type: "list",
          items: [
            "Lee tu CV en PDF y arma tu perfil con tus habilidades, tu experiencia, tus estudios y tus idiomas. Vos confirmás lo que figura en él.",
            "Analiza un puesto a partir del enlace del aviso o de su texto: título, empresa, nivel, modalidad y habilidades que pide.",
            "Calcula el match score, que compara tu perfil con ese puesto en seis componentes.",
            "Arma un reporte ATS: qué palabras clave del puesto están en tu CV, cuáles aparecen con otro nombre y cuáles faltan, y cómo se lee el formato del archivo.",
            "Contrasta lo que declarás en tu perfil con lo que figura en tu CV y en el PDF de tu perfil de LinkedIn.",
            "Reescribe secciones de tu CV para un puesto sin inventar experiencia (CV Optimizer).",
            "Prepara material para la entrevista del puesto (Interview Kit, en el plan premium)."
          ]
        }
      ]
    },
    {
      heading: "Cómo funciona",
      blocks: [
        {
          type: "steps",
          items: [
            "Creás tu cuenta y subís tu CV en PDF.",
            "Jobby lo lee y arma tu perfil; revisás y confirmás tus habilidades.",
            "Pegás el enlace o el texto de un puesto.",
            "Recibís el match score con su detalle, el reporte ATS y recomendaciones para acercarte al puesto.",
            "Si querés, optimizás tu CV para ese puesto y volvés a medir."
          ]
        }
      ]
    },
    {
      heading: "Cómo se calcula el match score",
      blocks: [
        {
          type: "paragraph",
          text: `El match score va de 0 a 100 y combina seis componentes con su peso: ${weightsSummary}. Si el puesto es de un área muy distinta a la tuya, el puntaje se atenúa. Cada componente se ve por separado, así sabés dónde está la brecha.`
        },
        {
          type: "paragraph",
          text: "La guía «Qué es el match score y cómo se calcula» explica cada componente."
        }
      ]
    },
    {
      heading: "Qué mide el análisis ATS",
      blocks: [
        {
          type: "paragraph",
          text: `El puntaje ATS de Jobby va de 0 a 100: ${ATS_CONTENT_POINTS} puntos son de contenido (habilidades, experiencia, estudios e idiomas que pide el puesto) y ${ATS_FORMAT_POINTS} de formato del archivo. Una palabra clave presente suma ${formatPoints(ATS_KEYWORD_POINTS.literal)} y una de significado parecido suma ${formatPoints(ATS_KEYWORD_POINTS.semantic)}. Es una estimación de Jobby y no es el puntaje de ningún ATS real: cada empresa usa el suyo.`
        }
      ]
    },
    {
      heading: "Planes",
      blocks: [
        {
          type: "paragraph",
          text: `El plan gratuito incluye ${FREE_JOB_ANALYSES_PER_MONTH} análisis de puestos por mes, el match score completo, un análisis ATS básico, el historial de los últimos 10 puestos y ${CV_OPTIMIZATIONS_PER_MONTH.free} optimizaciones de CV por mes. El plan premium suma análisis sin límite, ${CV_OPTIMIZATIONS_PER_MONTH.premium} por mes con el CV Optimizer de IA avanzada, el Interview Kit premium y el historial completo. El estado de los pagos y los precios están en la página de planes.`
        }
      ]
    },
    {
      heading: "Qué no hace Jobby",
      blocks: [
        {
          type: "list",
          items: [
            "No garantiza una entrevista ni una contratación: cada empresa decide con sus propios criterios.",
            "No inventa experiencia ni habilidades que no figuren en tu perfil.",
            "No se postula por vos ni envía tu CV a ninguna empresa.",
            "No vende tu CV ni tus datos profesionales como una base de datos pública."
          ]
        }
      ]
    }
  ],
  faq: [
    {
      question: "¿Qué es Jobby web?",
      answer:
        "Jobby web es una aplicación web que compara tu CV con un puesto real y calcula un match score, un análisis de compatibilidad con sistemas ATS y las habilidades que te faltan, para que sepas qué mejorar antes de postularte. Funciona en español y en inglés."
    },
    {
      question: "¿Para qué sirve Jobby?",
      answer:
        "Sirve para decidir a qué puestos postularte y cómo preparar tu CV para cada uno: te muestra qué tanto encajás con el aviso, qué palabras clave te faltan y qué habilidades conviene reforzar, antes de enviar la postulación."
    },
    {
      question: "¿Cómo funciona Jobby?",
      answer:
        "Subís tu CV en PDF, Jobby arma tu perfil y vos confirmás tus habilidades. Después pegás el enlace o el texto de un puesto y recibís el match score con su detalle, el reporte ATS y recomendaciones. Si querés, optimizás tu CV para ese puesto."
    },
    {
      question: "¿Qué es el match score de Jobby?",
      answer: `Es un puntaje de 0 a 100 que mide cuánto coincide tu perfil con un puesto. Combina seis componentes con su peso: ${weightsSummary}. Cada uno se ve por separado, así identificás dónde está la brecha.`
    },
    {
      question: "¿Qué es el reporte ATS de Jobby?",
      answer:
        "Es un análisis de cómo un sistema de seguimiento de candidatos leería tu CV para un puesto: qué palabras clave están, cuáles aparecen con otro nombre y cuáles faltan, y qué tan legible es el formato. Es una estimación de Jobby y no es el puntaje de ningún ATS real."
    },
    {
      question: "¿Jobby es gratis?",
      answer: `Tiene un plan gratuito con ${FREE_JOB_ANALYSES_PER_MONTH} análisis de puestos por mes, el match score completo, un análisis ATS básico y ${CV_OPTIMIZATIONS_PER_MONTH.free} optimizaciones de CV por mes. El plan premium suma análisis sin límite, ${CV_OPTIMIZATIONS_PER_MONTH.premium} optimizaciones por mes y el Interview Kit premium. Los precios y el estado de los pagos están en la página de planes.`
    },
    {
      question: "¿Jobby inventa experiencia en mi CV?",
      answer:
        "No. El CV Optimizer reescribe secciones de tu CV para acercarlas a un puesto usando solo lo que ya figura en tu perfil: no agrega experiencia ni habilidades que no tengas. Revisá siempre el resultado antes de usarlo."
    },
    {
      question: "¿Qué pasa con mi CV y mis datos en Jobby?",
      answer:
        "Jobby usa tu CV y tus datos para crear tu perfil, calcular los puntajes y generar los reportes. No vende tu CV ni tus datos profesionales como una base de datos pública, y podés pedir el acceso, la corrección o la eliminación de tus datos. Los detalles están en la política de privacidad."
    },
    {
      question: "¿Jobby garantiza que me llamen a una entrevista?",
      answer:
        "No. Jobby no garantiza entrevistas ni contrataciones: cada empresa y cada sistema de selección usa sus propios criterios. Te ayuda a ver dónde estás parado frente a un puesto y a preparar mejor tu postulación."
    },
    {
      question: "¿En qué idiomas funciona Jobby?",
      answer:
        "La aplicación está en español y en inglés. Las guías y esta página están escritas en español."
    }
  ],
  links: [
    { label: "Planes y precios", path: "/pricing" },
    { label: "Todas las guías", path: "/guias" },
    { label: "Qué es el match score y cómo se calcula", path: "/guias/que-es-el-match-score" },
    { label: "Qué es un ATS y cómo lee tu CV", path: "/guias/que-es-un-ats" },
    { label: "Optimizar el CV con IA sin inventar experiencia", path: "/guias/optimizar-cv-con-ia" },
    { label: "Política de privacidad", path: "/privacy" }
  ]
};
