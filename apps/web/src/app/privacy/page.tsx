"use client";

import Link from "next/link";

import { LanguageToggle } from "@/components/language-toggle";
import { useI18n } from "@/lib/i18n/provider";

const content = {
  es: {
    eyebrow: "Base legal inicial",
    title: "Política de Privacidad",
    intro:
      "Esta política explica de forma simple qué datos puede tratar Jobby y para qué. No es asesoramiento legal definitivo; debe revisarse con un profesional antes de usarla como documento final.",
    sections: [
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
    ],
    notice:
      "No vendemos tu CV ni tus datos profesionales como base de datos pública. Los usamos para prestar el servicio, proteger la plataforma y cumplir obligaciones técnicas o legales aplicables."
  },
  en: {
    eyebrow: "Initial legal baseline",
    title: "Privacy Policy",
    intro:
      "This policy explains, in simple terms, what data Jobby may process and why. It is not final legal advice and should be reviewed by a qualified professional before being used as a final document.",
    sections: [
      {
        title: "Data we collect",
        body:
          "We may collect email, name, account data, CVs, skills, work experience, education, languages, certifications, professional links, LinkedIn information you share with us, and job descriptions you analyze."
      },
      {
        title: "How we use your data",
        body:
          "We use your data to create your professional profile, calculate match scores, detect gaps, generate ATS reports, prepare interview kits, and improve recommendation accuracy."
      },
      {
        title: "AI use and external providers",
        body:
          "We may process content with providers for AI, infrastructure, authentication, storage, email, analytics, and payments. Where applicable, payments may be handled by Lemon Squeezy."
      },
      {
        title: "Storage and security",
        body:
          "We apply reasonable security, authentication, and access controls. Even so, no internet-connected system can guarantee absolute security."
      },
      {
        title: "Cookies and localStorage",
        body:
          "We may use cookies, session tokens, and localStorage to keep you signed in, remember preferences such as language, and save onboarding progress."
      },
      {
        title: "Your rights",
        body:
          "You may request access, correction, or deletion of your data. Account deletion attempts to remove documents, associated records, and linked data according to the system's technical capabilities."
      },
      {
        title: "Contact",
        body:
          "For privacy questions or data deletion requests, contact us at contacto@jobby.ai. This policy is an initial baseline that should be reviewed by legal counsel."
      }
    ],
    notice:
      "We do not sell your CV or professional data as a public database. We use it to provide the service, protect the platform, and comply with applicable technical or legal obligations."
  }
};

export default function PrivacyPage() {
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
