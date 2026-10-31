import type { ReactNode } from "react";

import {
  experienceBullets,
  formatMonthYear,
  formatPeriod,
  skillCells
} from "@/lib/cv/cv-layout";
import type { PrintableCV } from "@/lib/cv/printable-cv";

const SECTION = "mt-[13px] break-inside-avoid-page";
const HEADING =
  "border-b border-black pb-[1px] text-[10.5pt] font-bold uppercase leading-tight";
const BULLET =
  "relative pl-[11px] before:absolute before:left-[2px] before:content-['•']";

function DatedLine({ children, date }: { children: ReactNode; date: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <p>{children}</p>
      {date ? <p className="shrink-0 font-bold">{date}</p> : null}
    </div>
  );
}

// Una columna de texto real, títulos de sección estándar y una grilla de habilidades
// que el lector de PDF sigue leyendo en orden: la estructura del CV modelo del autor
// (Decisión 26), con los datos de quien lo descarga.
export function PrintableCVDocument({ cv }: { cv: PrintableCV }) {
  const contactItems = [cv.contact.phone, cv.contact.email, cv.contact.linkedin_url].filter(
    Boolean
  );
  const cells = skillCells(cv.skills, cv.languages);
  const studies = [
    ...cv.educations.map((education) => ({
      title: education.field_of_study || education.degree_level || "",
      detail: education.institution,
      date: formatPeriod(
        education.started_at,
        education.ended_at,
        Boolean(education.is_ongoing),
        "Actualidad"
      )
    })),
    ...cv.certifications.map((certification) => ({
      title: certification.name,
      detail: certification.issuer ?? "",
      date: formatMonthYear(certification.issued_at)
    }))
  ];

  return (
    <article
      className="mx-auto w-full max-w-[794px] bg-white px-[15mm] py-[11mm] text-[9pt] leading-[1.35] text-black print:max-w-none print:bg-transparent print:p-0"
      style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
    >
      <header className="text-center">
        <h1 className="text-[18pt] font-bold uppercase leading-tight">
          {cv.contact.full_name || "Tu nombre"}
        </h1>
        {contactItems.length > 0 ? (
          <p className="mt-[3px] flex flex-wrap justify-center gap-x-4 text-[8.7pt]">
            {contactItems.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </p>
        ) : null}
        {cv.contact.location ? (
          <p className="text-[8.7pt]">{cv.contact.location}</p>
        ) : null}
      </header>

      {cv.headline || cv.summary ? (
        <section className={SECTION}>
          {cv.headline ? <h2 className={HEADING}>{cv.headline}</h2> : null}
          {cv.summary ? (
            <p className="mt-[6px] text-justify">{cv.summary}</p>
          ) : null}
        </section>
      ) : null}

      {cells.length > 0 ? (
        <section className={SECTION}>
          <h2 className={HEADING}>HABILIDADES Y COMPETENCIAS</h2>
          <ul className="mt-[6px] grid grid-cols-3 gap-x-3 gap-y-[3px]">
            {cells.map((cell) => (
              <li className={BULLET} key={cell}>
                {cell}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {cv.experiences.length > 0 ? (
        <section className="mt-[13px]">
          <h2 className={HEADING}>EXPERIENCIA PROFESIONAL</h2>
          {cv.experiences.map((experience) => {
            const bullets = experienceBullets(experience);
            return (
              <div
                className="mt-[7px] break-inside-avoid"
                key={`${experience.company}-${experience.title}-${experience.started_at}`}
              >
                {experience.company ? (
                  <p className="text-[9.5pt] font-bold uppercase">{experience.company}</p>
                ) : null}
                <DatedLine
                  date={formatPeriod(
                    experience.started_at,
                    experience.ended_at,
                    experience.is_current,
                    "Presente"
                  )}
                >
                  <span className="font-bold italic">{experience.title}</span>
                </DatedLine>
                {bullets.length > 0 ? (
                  <ul className="mt-[1px] space-y-[1px]">
                    {bullets.map((bullet) => (
                      <li className={BULLET} key={bullet}>
                        {bullet}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            );
          })}
        </section>
      ) : null}

      {studies.length > 0 ? (
        <section className="mt-[13px]">
          <h2 className={HEADING}>EDUCACIÓN</h2>
          {studies.map((study) => (
            <div
              className="mt-[6px] break-inside-avoid"
              key={`${study.title}-${study.detail}-${study.date}`}
            >
              <DatedLine date={study.date}>
                <span className="font-bold">{study.title}</span>
              </DatedLine>
              {study.detail ? <p>{study.detail}</p> : null}
            </div>
          ))}
        </section>
      ) : null}
    </article>
  );
}
