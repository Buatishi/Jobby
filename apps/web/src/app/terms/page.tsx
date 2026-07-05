"use client";

import Link from "next/link";

import { LanguageToggle } from "@/components/language-toggle";
import { useI18n } from "@/lib/i18n/provider";

const content = {
  es: {
    eyebrow: "Base legal inicial",
    title: "Términos y Condiciones",
    intro:
      "Estos términos son una base informativa inicial para el uso de Jobby. No constituyen asesoramiento legal definitivo y deberían ser revisados por un profesional antes de operar comercialmente a escala.",
    sections: [
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
    ],
    notice:
      "Al crear una cuenta aceptás usar Jobby de buena fe, no interferir con la seguridad del servicio y no intentar acceder a datos de otros usuarios. Si no estás de acuerdo con estos términos, no uses la plataforma."
  },
  en: {
    eyebrow: "Initial legal baseline",
    title: "Terms and Conditions",
    intro:
      "These terms are an initial informational baseline for using Jobby. They are not final legal advice and should be reviewed by a qualified professional before commercial operation at scale.",
    sections: [
      {
        title: "Permitted use",
        body:
          "Jobby helps you analyze job compatibility, optimize applications, and prepare for interviews. You may not use the platform for abuse, scraping, reverse engineering, spam, fraud, impersonation, or bulk data extraction."
      },
      {
        title: "Account and user responsibility",
        body:
          "You are responsible for the information you upload, including CVs, professional data, links, and job descriptions. You must keep your credentials secure and notify us if you detect unauthorized use."
      },
      {
        title: "AI use and limitations",
        body:
          "Reports are generated with AI systems and may contain errors, omissions, or imperfect interpretations. Jobby does not guarantee interviews, job offers, compensation improvements, or specific employment outcomes."
      },
      {
        title: "Subscriptions and payments",
        body:
          "Premium features may require a subscription or payment through external providers such as Lemon Squeezy. Prices, benefits, renewals, and cancellations are shown before confirming a purchase."
      },
      {
        title: "Intellectual property",
        body:
          "The platform, brand, design, software, and owned content belong to Jobby or its licensors. You retain your rights over the data and documents you upload."
      },
      {
        title: "Changes and contact",
        body:
          "We may update the service or these terms to improve the product, meet legal requirements, or strengthen security. For questions, contact us at contacto@jobby.ai."
      }
    ],
    notice:
      "By creating an account, you agree to use Jobby in good faith, avoid interfering with service security, and not attempt to access other users' data. If you do not agree with these terms, do not use the platform."
  }
};

export default function TermsPage() {
  const { language } = useI18n();
  const copy = content[language];

  return (
    <main className="min-h-screen bg-white text-foreground">
      <div className="mx-auto max-w-3xl px-6 py-12 sm:py-16">
        <div className="flex items-center justify-between gap-4">
          <Link
            className="text-xl font-black tracking-tight text-brand-green"
            href="/"
          >
            Jobby
          </Link>
          <LanguageToggle compact />
        </div>

        <div className="mt-10">
          <p className="text-sm font-bold uppercase tracking-[0.18em] text-brand-green">
            {copy.eyebrow}
          </p>
          <h1 className="mt-3 text-4xl font-black tracking-tight">
            {copy.title}
          </h1>
          <p className="mt-4 text-sm leading-7 text-muted-foreground">
            {copy.intro}
          </p>
        </div>

        <div className="mt-10 space-y-8">
          {copy.sections.map((section) => (
            <section key={section.title}>
              <h2 className="text-xl font-bold">{section.title}</h2>
              <p className="mt-3 text-sm leading-7 text-muted-foreground">
                {section.body}
              </p>
            </section>
          ))}
        </div>

        <div className="mt-12 rounded-2xl border border-neutral-100 bg-bg-dashboard p-5 text-sm leading-7 text-muted-foreground">
          {copy.notice}
        </div>
      </div>
    </main>
  );
}
