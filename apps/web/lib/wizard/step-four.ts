export type StepFourValues = {
  company: string;
  title: string;
  education: string;
  language: string;
};

export type StepFourField = keyof StepFourValues;

export const STEP_FOUR_DEFAULTS: StepFourValues = {
  company: "",
  title: "",
  education: "",
  language: ""
};

// Lo que devuelve GET /api/v1/profiles/details: de la fila más nueva a la más vieja.
export type StepFourDetails = {
  experiences?: Array<{
    id: string;
    company?: string | null;
    title?: string | null;
  }> | null;
  educations?: Array<{ id: string; institution?: string | null }> | null;
  languages?: Array<{ id: string; name?: string | null }> | null;
};

// Las filas que este paso edita: la más nueva de cada tipo, con el valor guardado.
export type StepFourSaved = {
  experience: { id: string; company: string; title: string } | null;
  education: { id: string; institution: string } | null;
  language: { id: string; name: string } | null;
};

export const STEP_FOUR_NOTHING_SAVED: StepFourSaved = {
  experience: null,
  education: null,
  language: null
};

export type StepFourSection = "experience" | "education" | "language";

export type StepFourWrite = {
  section: StepFourSection;
  method: "POST" | "PATCH";
  path: string;
  body: Record<string, unknown>;
  // Lo que queda guardado si el pedido sale bien.
  values: { company?: string; title?: string; institution?: string; name?: string };
};

export type StepFourResolution = {
  values: StepFourValues;
  saved: StepFourSaved;
  // Cuántas experiencias hay guardadas (el paso muestra y edita la más nueva).
  experienceCount: number;
  // Verdadero si algún campo vino de lo que la persona ya tenía guardado.
  prefilled: boolean;
};

const DEFAULT_LANGUAGE_LEVEL = "professional";

function text(value: string | null | undefined): string {
  return typeof value === "string" ? value : "";
}

/**
 * Valores con los que abre el paso 4: lo que ya está guardado en el perfil.
 *
 * Antes el paso abría vacío y cada vez que se lo completaba insertaba filas nuevas: la
 * misma experiencia quedaba dos o tres veces. Ahora se muestra (y después se edita) la
 * fila más nueva de cada tipo.
 */
export function resolveStepFour(
  details: StepFourDetails | null
): StepFourResolution {
  const experience = details?.experiences?.[0] ?? null;
  const education = details?.educations?.[0] ?? null;
  const language = details?.languages?.[0] ?? null;

  const saved: StepFourSaved = {
    experience: experience
      ? {
          id: experience.id,
          company: text(experience.company),
          title: text(experience.title)
        }
      : null,
    education: education
      ? { id: education.id, institution: text(education.institution) }
      : null,
    language: language ? { id: language.id, name: text(language.name) } : null
  };

  const values: StepFourValues = {
    company: saved.experience?.company ?? "",
    title: saved.experience?.title ?? "",
    education: saved.education?.institution ?? "",
    language: saved.language?.name ?? ""
  };

  return {
    values,
    saved,
    experienceCount: details?.experiences?.length ?? 0,
    prefilled: Object.values(values).some((value) => value.trim() !== "")
  };
}

/**
 * El formulario se puede escribir mientras carga lo guardado (si la API despierta de un
 * arranque en frío, tarda hasta ~40 s). Al llegar, un campo que la persona ya tocó
 * conserva lo escrito y el resto toma el valor guardado.
 */
export function mergeLoadedValues(
  current: StepFourValues,
  touched: ReadonlySet<StepFourField>,
  loaded: StepFourValues
): StepFourValues {
  const pick = (field: StepFourField) =>
    touched.has(field) ? current[field] : loaded[field];

  return {
    company: pick("company"),
    title: pick("title"),
    education: pick("education"),
    language: pick("language")
  };
}

/**
 * Pedidos que hay que hacer para guardar el formulario.
 *
 * - Fila guardada y valor distinto: se edita esa fila (PATCH), no se agrega otra.
 * - Fila guardada y valor igual: nada, así volver a pasar por el paso no repite datos.
 * - Sin fila guardada y con valor: se crea (POST).
 * - Campo vacío: nada. Vaciarlo no borra lo guardado (no hay borrado en la API).
 */
export function planStepFourWrites(
  values: StepFourValues,
  saved: StepFourSaved
): StepFourWrite[] {
  const writes: StepFourWrite[] = [];

  const company = values.company.trim();
  const title = values.title.trim();
  if (company || title) {
    if (!saved.experience) {
      writes.push({
        section: "experience",
        method: "POST",
        path: "/api/v1/profiles/experiences",
        body: { company, title, description: null, achievements: [] },
        values: { company, title }
      });
    } else if (
      company !== saved.experience.company.trim() ||
      title !== saved.experience.title.trim()
    ) {
      writes.push({
        section: "experience",
        method: "PATCH",
        path: `/api/v1/profiles/experiences/${saved.experience.id}`,
        body: { company, title },
        values: { company, title }
      });
    }
  }

  const institution = values.education.trim();
  if (institution) {
    if (!saved.education) {
      writes.push({
        section: "education",
        method: "POST",
        path: "/api/v1/profiles/educations",
        body: {
          institution,
          field_of_study: null,
          degree_level: null
        },
        values: { institution }
      });
    } else if (institution !== saved.education.institution.trim()) {
      writes.push({
        section: "education",
        method: "PATCH",
        path: `/api/v1/profiles/educations/${saved.education.id}`,
        body: { institution },
        values: { institution }
      });
    }
  }

  const name = values.language.trim();
  if (name) {
    if (!saved.language) {
      writes.push({
        section: "language",
        method: "POST",
        path: "/api/v1/profiles/languages",
        body: { name, level: DEFAULT_LANGUAGE_LEVEL },
        values: { name }
      });
    } else if (name !== saved.language.name.trim()) {
      writes.push({
        section: "language",
        method: "PATCH",
        path: `/api/v1/profiles/languages/${saved.language.id}`,
        body: { name },
        values: { name }
      });
    }
  }

  return writes;
}

/**
 * Lo guardado después de que un pedido salió bien. Importa cuando otro pedido del mismo
 * guardado falla: al reintentar, la fila que ya se creó se edita y no se agrega de nuevo.
 */
export function applyStepFourWrite(
  saved: StepFourSaved,
  write: StepFourWrite,
  createdId: string | null
): StepFourSaved {
  switch (write.section) {
    case "experience": {
      const id = saved.experience?.id ?? createdId;
      return id
        ? {
            ...saved,
            experience: {
              id,
              company: write.values.company ?? "",
              title: write.values.title ?? ""
            }
          }
        : saved;
    }
    case "education": {
      const id = saved.education?.id ?? createdId;
      return id
        ? {
            ...saved,
            education: { id, institution: write.values.institution ?? "" }
          }
        : saved;
    }
    case "language": {
      const id = saved.language?.id ?? createdId;
      return id
        ? { ...saved, language: { id, name: write.values.name ?? "" } }
        : saved;
    }
  }
}
