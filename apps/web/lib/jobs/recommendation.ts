export type Recommendation = {
  title?: string;
  description?: string;
  priority?: "low" | "medium" | "high";
};

export type RecommendationView = {
  heading: string;
  body: string | null;
};

/**
 * Saca las marcas de markdown que la IA deja en el texto. Es tolerante a marcas sueltas:
 * el backend guarda cada línea sin los `*` iniciales, así que suele quedar solo el `**` de cierre.
 */
function stripMarkdown(text: string): string {
  return text
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/^\s*(?:#{1,6}|>)\s+/, "")
    .replace(/[*`]+/g, "")
    .replace(/__+/g, "")
    .replace(/(^|\W)_([^_\s](?:[^_]*[^_\s])?)_(?!\w)/g, "$1$2")
    .replace(/\s+/g, " ")
    .trim();
}

// Solo corta en ":" seguido de espacio o al final, para no partir URLs ni horas (10:30).
function splitAtColon(text: string): RecommendationView {
  const colon = /:(?:\s+|$)/.exec(text);
  if (!colon || colon.index === 0) {
    return { heading: text, body: null };
  }
  return {
    heading: text.slice(0, colon.index).trim(),
    body: text.slice(colon.index + colon[0].length).trim() || null
  };
}

/**
 * Arma lo que se muestra de una recomendación. El backend guarda `title` como los primeros
 * 80 caracteres de `description`, así que ese título solo sirve si no es un recorte del cuerpo;
 * si lo es, el encabezado sale del texto completo, antes de los dos puntos.
 */
export function toRecommendationView(
  recommendation: Recommendation
): RecommendationView | null {
  const title = (recommendation.title ?? "").trim();
  const description = (recommendation.description ?? "").trim();

  if (title && description && !description.startsWith(title)) {
    const heading = stripMarkdown(title);
    if (heading) {
      return { heading, body: stripMarkdown(description) || null };
    }
  }

  const view = splitAtColon(stripMarkdown(description || title));
  return view.heading ? view : null;
}
