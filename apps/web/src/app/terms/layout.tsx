import type { Metadata } from "next";

// La página es de cliente y no puede exportar metadatos: este layout los aporta.
export const metadata: Metadata = {
  title: "Términos y Condiciones — Jobby",
  description:
    "Términos de uso de Jobby, la plataforma que compara tu CV con puestos reales.",
  alternates: { canonical: "/terms" }
};

export default function TermsLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <>{children}</>;
}
