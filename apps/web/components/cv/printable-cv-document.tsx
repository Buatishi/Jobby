import { formatPeriod, type PrintableCV } from "@/lib/cv/printable-cv";

// Una columna, texto real y títulos estándar: es el formato que mejor leen los ATS.
// Se parece a los CV de referencia en orden, jerarquía y espaciado, pero sin columnas,
// imágenes ni tablas: lo que `penalty_after_download` (API) da por hecho de este
// documento. Los títulos son los de `STANDARD_HEADERS`; por eso el resumen no tiene el
// suyo («Perfil» restaría 5 puntos al volver a subir este PDF).
const SECTION = "mt-4 border-t border-black pt-3";
const TITLE = "mb-2 text-center text-[10.5pt] font-bold uppercase tracking-[0.04em]";
const ENTRY_ROW = "flex items-baseline justify-between gap-4";
// El espacio antes del punto no se parte: si el renglón se corta, el punto queda al
// final de una línea y no al principio de la siguiente.
const LIST_SEPARATOR = "\u00a0· ";

function Title({ children }: { children: string }) {
  return <h2 className={TITLE}>{children}</h2>;
}

export function PrintableCVDocument({ cv }: { cv: PrintableCV }) {
  const contactLine = [
    cv.contact.email,
    cv.contact.phone,
    cv.contact.location,
    cv.contact.linkedin_url
  ].filter(Boolean);

  return (
    <article className="mx-auto max-w-[800px] bg-white p-10 font-sans text-[10pt] leading-snug text-black">
      <header className="text-center">
        <h1 className="text-[22pt] font-semibold uppercase leading-tight tracking-[0.06em]">
          {cv.contact.full_name || "Tu nombre"}
        </h1>
        {cv.headline ? <p className="mt-1 text-[11pt]">{cv.headline}</p> : null}
        {contactLine.length > 0 ? (
          <p className="mt-1 text-[9pt]">{contactLine.join(" · ")}</p>
        ) : null}
      </header>

      {cv.summary ? (
        <section className="mt-4 border-t border-black pt-3">
          <p>{cv.summary}</p>
        </section>
      ) : null}

      {cv.skills.length > 0 ? (
        <section className={SECTION}>
          <Title>Habilidades</Title>
          <p className="text-center [text-wrap:balance]">{cv.skills.join(LIST_SEPARATOR)}</p>
        </section>
      ) : null}

      {cv.experiences.length > 0 ? (
        <section className={SECTION}>
          <Title>Experiencia</Title>
          {cv.experiences.map((experience) => {
            const period = formatPeriod(
              experience.started_at,
              experience.ended_at,
              experience.is_current
            );
            const name = experience.company || experience.title;
            return (
              <div
                className="mt-3 break-inside-avoid first:mt-0"
                key={`${experience.company}-${experience.title}-${experience.started_at}`}
              >
                <div className={ENTRY_ROW}>
                  <p className="font-bold">{name}</p>
                  {period ? <p className="shrink-0 font-bold">{period}</p> : null}
                </div>
                {/* Regular y no negrita: un cargo en mayúsculas y negrita se leería como
                    título de sección al volver a subir este PDF. */}
                {experience.company && experience.title ? (
                  <p>{experience.title}</p>
                ) : null}
                {experience.description ? (
                  <p className="mt-1">{experience.description}</p>
                ) : null}
                {experience.achievements.length > 0 ? (
                  <ul className="mt-1 list-disc pl-5">
                    {experience.achievements.map((achievement) => (
                      <li key={achievement}>{achievement}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            );
          })}
        </section>
      ) : null}

      {cv.educations.length > 0 ? (
        <section className={SECTION}>
          <Title>Educación</Title>
          {cv.educations.map((education) => {
            const period = formatPeriod(
              education.started_at,
              education.ended_at,
              education.is_ongoing
            );
            const name = education.field_of_study || education.degree_level;
            return (
              <div
                className="mt-2 break-inside-avoid first:mt-0"
                key={`${education.institution}-${education.field_of_study}`}
              >
                <div className={ENTRY_ROW}>
                  <p className="font-bold">{name || education.institution}</p>
                  {period ? <p className="shrink-0 font-bold">{period}</p> : null}
                </div>
                {name && education.institution ? <p>{education.institution}</p> : null}
              </div>
            );
          })}
        </section>
      ) : null}

      {cv.languages.length > 0 ? (
        <section className={SECTION}>
          <Title>Idiomas</Title>
          <p className="text-center [text-wrap:balance]">
            {cv.languages
              .map((language) =>
                language.level ? `${language.name} (${language.level})` : language.name
              )
              .join(LIST_SEPARATOR)}
          </p>
        </section>
      ) : null}

      {cv.certifications.length > 0 ? (
        <section className={SECTION}>
          <Title>Certificaciones</Title>
          {cv.certifications.map((certification) => (
            <p className="mt-1 first:mt-0" key={certification.name}>
              {certification.issuer
                ? `${certification.name} — ${certification.issuer}`
                : certification.name}
            </p>
          ))}
        </section>
      ) : null}
    </article>
  );
}
