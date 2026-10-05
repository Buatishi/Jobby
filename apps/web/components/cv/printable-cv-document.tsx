import type { PrintableCV } from "@/lib/cv/printable-cv";

function period(started: string | null, ended: string | null, isCurrent: boolean) {
  const start = started?.slice(0, 7) ?? "";
  const end = isCurrent ? "actualidad" : (ended?.slice(0, 7) ?? "");
  if (start && end) {
    return `${start} – ${end}`;
  }
  return start || end;
}

// Una columna, texto real y títulos estándar: es el formato que mejor leen los ATS.
export function PrintableCVDocument({ cv }: { cv: PrintableCV }) {
  const contactLine = [
    cv.contact.email,
    cv.contact.phone,
    cv.contact.location,
    cv.contact.linkedin_url
  ].filter(Boolean);

  return (
    <article className="mx-auto max-w-[800px] bg-white p-10 font-sans text-[11pt] leading-snug text-black">
      <header>
        <h1 className="text-[20pt] font-bold">{cv.contact.full_name || "Tu nombre"}</h1>
        {contactLine.length > 0 ? (
          <p className="mt-1">{contactLine.join(" · ")}</p>
        ) : null}
        {cv.headline ? <p className="mt-2 font-semibold">{cv.headline}</p> : null}
      </header>

      {cv.summary ? (
        <section className="mt-5">
          <h2 className="border-b border-black text-[12pt] font-bold uppercase">
            Perfil
          </h2>
          <p className="mt-2">{cv.summary}</p>
        </section>
      ) : null}

      {cv.experiences.length > 0 ? (
        <section className="mt-5">
          <h2 className="border-b border-black text-[12pt] font-bold uppercase">
            Experiencia
          </h2>
          {cv.experiences.map((experience) => (
            <div
              className="mt-3"
              key={`${experience.company}-${experience.title}-${experience.started_at}`}
            >
              <p className="font-bold">
                {[experience.title, experience.company].filter(Boolean).join(" — ")}
              </p>
              {period(experience.started_at, experience.ended_at, experience.is_current) ? (
                <p>
                  {period(experience.started_at, experience.ended_at, experience.is_current)}
                </p>
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
          ))}
        </section>
      ) : null}

      {cv.educations.length > 0 ? (
        <section className="mt-5">
          <h2 className="border-b border-black text-[12pt] font-bold uppercase">
            Educación
          </h2>
          {cv.educations.map((education) => (
            <p
              className="mt-2"
              key={`${education.institution}-${education.field_of_study}`}
            >
              <span className="font-bold">
                {education.field_of_study || education.degree_level}
              </span>
              {education.institution ? ` — ${education.institution}` : null}
            </p>
          ))}
        </section>
      ) : null}

      {cv.skills.length > 0 ? (
        <section className="mt-5">
          <h2 className="border-b border-black text-[12pt] font-bold uppercase">
            Habilidades
          </h2>
          <p className="mt-2">{cv.skills.join(", ")}</p>
        </section>
      ) : null}

      {cv.languages.length > 0 ? (
        <section className="mt-5">
          <h2 className="border-b border-black text-[12pt] font-bold uppercase">
            Idiomas
          </h2>
          <p className="mt-2">
            {cv.languages
              .map((language) =>
                language.level ? `${language.name} (${language.level})` : language.name
              )
              .join(", ")}
          </p>
        </section>
      ) : null}

      {cv.certifications.length > 0 ? (
        <section className="mt-5">
          <h2 className="border-b border-black text-[12pt] font-bold uppercase">
            Certificaciones
          </h2>
          {cv.certifications.map((certification) => (
            <p className="mt-1" key={certification.name}>
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
