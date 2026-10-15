import type { Metadata } from "next";

// La página es de cliente y no puede exportar metadatos: este layout los aporta.
// Sin canonical: las rutas hijas (success, cancel, unavailable) lo heredarían.
export const metadata: Metadata = {
  title: "Planes y precios — Jobby",
  description:
    "Planes de Jobby: empezá gratis y pasá a premium cuando necesites más análisis de tu CV."
};

export default function PricingLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <>{children}</>;
}
