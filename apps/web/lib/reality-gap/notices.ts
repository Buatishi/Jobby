import type {
  RealityGapDocument,
  RealityGapReport
} from "@/lib/reality-gap/types";

export type RealityGapNotice = {
  id: string;
  text: string;
  href?: string;
  actionLabel?: string;
};

type Documents = Pick<RealityGapReport, "cv" | "linkedin">;

const PROFILE_HREF = "/profile";

function documentNotice(
  document: RealityGapDocument | null,
  names: { missing: RealityGapNotice; reading: string; failed: string },
  id: string
): RealityGapNotice | null {
  if (document === null) {
    return names.missing;
  }
  if (document.status === "done") {
    return null;
  }
  if (document.status === "failed") {
    return {
      id: `${id}-failed`,
      text: names.failed,
      href: PROFILE_HREF,
      actionLabel: "Ir a Mi perfil"
    };
  }
  return { id: `${id}-reading`, text: names.reading };
}

// Lo que impide comparar o lo vuelve menos exacto, en el orden en que la persona lo arregla.
export function getNotices(report: Documents): RealityGapNotice[] {
  const notices: RealityGapNotice[] = [];

  const cv = documentNotice(
    report.cv,
    {
      missing: {
        id: "cv-missing",
        text: "Todavía no subiste tu CV, así que no hay con qué comparar.",
        href: PROFILE_HREF,
        actionLabel: "Subir CV"
      },
      reading: "Todavía estamos leyendo tu CV. Volvé en unos minutos.",
      failed: "No pudimos leer tu CV. Volvé a subirlo desde Mi perfil."
    },
    "cv"
  );
  if (cv) {
    notices.push(cv);
  }

  const linkedin = documentNotice(
    report.linkedin,
    {
      missing: {
        id: "linkedin-missing",
        text: "Falta el PDF de tu LinkedIn: sin él no podemos comparar lo que decís en el CV con lo que mostrás ahí.",
        href: PROFILE_HREF,
        actionLabel: "Subir PDF de LinkedIn"
      },
      reading: "Todavía estamos leyendo el PDF de tu LinkedIn. Volvé en unos minutos.",
      failed:
        "No pudimos leer el PDF de tu LinkedIn. Volvé a subirlo desde Mi perfil."
    },
    "linkedin"
  );
  if (linkedin) {
    notices.push(linkedin);
  }

  if (report.cv?.status === "done" && report.cv.skills_source === "saved") {
    notices.push({
      id: "cv-saved-marks",
      text: "Tu CV se leyó antes de esta mejora, así que usamos lo que ya teníamos guardado de él. Volvé a subirlo para compararlo con lo que dice hoy.",
      href: PROFILE_HREF,
      actionLabel: "Subir CV"
    });
  }

  return notices;
}

export function formatDocumentDate(
  iso: string | null,
  timeZone?: string
): string | null {
  if (!iso) {
    return null;
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toLocaleDateString("es-AR", {
    day: "numeric",
    month: "short",
    timeZone
  });
}

function describeDocument(
  label: string,
  document: RealityGapDocument,
  timeZone?: string
): string {
  const date = formatDocumentDate(document.uploaded_at, timeZone);
  const file = document.filename ? ` «${document.filename}»` : "";
  return `${label}${file}${date ? ` (${date})` : ""}`;
}

// Con qué archivos se comparó, para que la persona sepa de cuándo es lo que ve.
export function describeDocuments(
  report: Documents,
  timeZone?: string
): string | null {
  if (report.cv?.status !== "done" || report.linkedin?.status !== "done") {
    return null;
  }
  const cv = describeDocument("tu CV", report.cv, timeZone);
  const linkedin = describeDocument("el PDF de tu LinkedIn", report.linkedin, timeZone);
  return `Comparado con ${cv} y ${linkedin}. Si cambiaste algo, volvé a subir el archivo.`;
}
