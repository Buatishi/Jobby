import type { Metadata } from "next";

// La página es de cliente y no puede exportar metadatos: este layout los aporta.
export const metadata: Metadata = {
  title: "Política de Privacidad — Jobby",
  description:
    "Qué datos trata Jobby y para qué: CV, perfil profesional y descripciones de puestos que analizás.",
  alternates: { canonical: "/privacy" }
};

export default function PrivacyLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <>{children}</>;
}
