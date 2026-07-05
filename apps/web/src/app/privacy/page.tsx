import Link from "next/link";

const sections = [
  {
    title: "Datos que recopilamos",
    body:
      "Podemos recopilar email, nombre, datos de cuenta, CV, skills, experiencia laboral, educación, idiomas, certificaciones, links profesionales, información de LinkedIn que nos compartas y descripciones de puestos que analices."
  },
  {
    title: "Cómo usamos tus datos",
    body:
      "Usamos tus datos para crear tu perfil profesional, calcular match scores, detectar gaps, generar reportes ATS, preparar interview kits y mejorar la precisión de las recomendaciones."
  },
  {
    title: "Uso de IA y proveedores externos",
    body:
      "Podemos procesar contenido con proveedores de IA, infraestructura, autenticación, almacenamiento, email, analítica y pagos. Cuando corresponda, los pagos pueden ser gestionados por Lemon Squeezy."
  },
  {
    title: "Almacenamiento y seguridad",
    body:
      "Aplicamos controles razonables de seguridad, autenticación y acceso. Aun así, ningún sistema conectado a internet puede garantizar seguridad absoluta."
  },
  {
    title: "Cookies y localStorage",
    body:
      "Podemos usar cookies, tokens de sesión y localStorage para mantener tu sesión, recordar preferencias como idioma y guardar progreso de onboarding."
  },
  {
    title: "Tus derechos",
    body:
      "Podés solicitar acceso, corrección o eliminación de tus datos. La eliminación de cuenta intenta borrar documentos, registros asociados y datos vinculados según las capacidades técnicas del sistema."
  },
  {
    title: "Contacto",
    body:
      "Para consultas de privacidad o eliminación de datos, escribinos a contacto@jobby.ai. Esta política es una base inicial revisable por asesoría legal."
  }
];

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-white text-foreground">
      <div className="mx-auto max-w-3xl px-6 py-12 sm:py-16">
        <Link
          className="text-xl font-black tracking-tight text-brand-green"
          href="/"
        >
          Jobby
        </Link>
        <div className="mt-10">
          <p className="text-sm font-bold uppercase tracking-[0.18em] text-brand-green">
            Base legal inicial
          </p>
          <h1 className="mt-3 text-4xl font-black tracking-tight">
            Política de Privacidad
          </h1>
          <p className="mt-4 text-sm leading-7 text-muted-foreground">
            Esta política explica de forma simple qué datos puede tratar Jobby y
            para qué. No es asesoramiento legal definitivo; debe revisarse con un
            profesional antes de usarla como documento final.
          </p>
        </div>

        <div className="mt-10 space-y-8">
          {sections.map((section) => (
            <section key={section.title}>
              <h2 className="text-xl font-bold">{section.title}</h2>
              <p className="mt-3 text-sm leading-7 text-muted-foreground">
                {section.body}
              </p>
            </section>
          ))}
        </div>

        <div className="mt-12 rounded-2xl border border-neutral-100 bg-bg-dashboard p-5 text-sm leading-7 text-muted-foreground">
          No vendemos tu CV ni tus datos profesionales como base de datos pública.
          Los usamos para prestar el servicio, proteger la plataforma y cumplir
          obligaciones técnicas o legales aplicables.
        </div>
      </div>
    </main>
  );
}
