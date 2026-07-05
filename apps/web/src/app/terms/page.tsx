import Link from "next/link";

const sections = [
  {
    title: "Uso permitido",
    body:
      "Jobby te ayuda a analizar compatibilidad laboral, optimizar candidaturas y preparar entrevistas. No podés usar la plataforma para abuso, scraping, ingeniería inversa, spam, fraude, suplantación de identidad ni extracción masiva de datos."
  },
  {
    title: "Cuenta y responsabilidad del usuario",
    body:
      "Sos responsable de la información que cargás, incluyendo CV, datos profesionales, links y descripciones de puestos. Debés mantener tus credenciales seguras y avisarnos si detectás uso no autorizado."
  },
  {
    title: "Uso de IA y limitaciones",
    body:
      "Los reportes se generan con sistemas de IA y pueden contener errores, omisiones o interpretaciones imperfectas. Jobby no garantiza entrevistas, contrataciones, mejoras salariales ni resultados laborales específicos."
  },
  {
    title: "Suscripciones y pagos",
    body:
      "Las funciones Premium pueden requerir suscripción o pago a través de proveedores externos como Lemon Squeezy. Los precios, beneficios, renovaciones y cancelaciones se muestran antes de confirmar la compra."
  },
  {
    title: "Propiedad intelectual",
    body:
      "La plataforma, marca, diseño, software y contenidos propios pertenecen a Jobby o sus licenciantes. Conservás tus derechos sobre los datos y documentos que cargás."
  },
  {
    title: "Cambios y contacto",
    body:
      "Podemos actualizar el servicio o estos términos para mejorar el producto, cumplir requisitos legales o reforzar seguridad. Para consultas, escribinos a contacto@jobby.ai."
  }
];

export default function TermsPage() {
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
            Términos y Condiciones
          </h1>
          <p className="mt-4 text-sm leading-7 text-muted-foreground">
            Estos términos son una base informativa inicial para el uso de Jobby.
            No constituyen asesoramiento legal definitivo y deberían ser revisados
            por un profesional antes de operar comercialmente a escala.
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
          Al crear una cuenta aceptás usar Jobby de buena fe, no interferir con
          la seguridad del servicio y no intentar acceder a datos de otros
          usuarios. Si no estás de acuerdo con estos términos, no uses la
          plataforma.
        </div>
      </div>
    </main>
  );
}
