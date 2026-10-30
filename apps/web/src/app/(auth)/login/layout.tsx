import type { Metadata } from "next";

import { NOINDEX_ROBOTS } from "@/lib/seo/site";

// La página es de cliente y no puede exportar metadatos: este layout los aporta. Sin título propio
// heredaba el de la home y Bing la mostraba primera para «jobbyweb».
export const metadata: Metadata = {
  title: "Iniciar sesión — Jobby",
  robots: NOINDEX_ROBOTS
};

export default function LoginLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <>{children}</>;
}
