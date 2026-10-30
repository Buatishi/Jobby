import type { Metadata } from "next";

import { NOINDEX_ROBOTS } from "@/lib/seo/site";

// La página es de cliente y no puede exportar metadatos: este layout los aporta.
export const metadata: Metadata = {
  title: "Recuperar contraseña — Jobby",
  robots: NOINDEX_ROBOTS
};

export default function ForgotPasswordLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <>{children}</>;
}
