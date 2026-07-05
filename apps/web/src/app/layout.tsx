import type { Metadata, Viewport } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

import { I18nProvider } from "@/lib/i18n/provider";

const geistSans = Geist({
  subsets: ["latin"],
  variable: "--font-geist-sans"
});

export const metadata: Metadata = {
  metadataBase: new URL("https://jobbyweb.vercel.app"),
  title: "Jobby — Sabé cuánto matcheás antes de aplicar",
  description:
    "Análisis de compatibilidad laboral con IA para comparar tu CV contra puestos reales, detectar gaps y preparar mejores postulaciones.",
  openGraph: {
    title: "Jobby — Sabé cuánto matcheás antes de aplicar",
    description:
      "Subí tu CV, pegá un puesto y recibí match score, ATS, gaps reales y recomendaciones accionables.",
    images: ["/og-image.png"],
    siteName: "Jobby",
    type: "website",
    url: "https://jobbyweb.vercel.app"
  },
  twitter: {
    card: "summary_large_image",
    title: "Jobby — Sabé cuánto matcheás antes de aplicar",
    description:
      "Match score, ATS y preparación laboral con IA antes de postularte.",
    images: ["/og-image.png"]
  }
};

export const viewport: Viewport = {
  colorScheme: "light",
  themeColor: "#ffffff"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html className="light" lang="es" suppressHydrationWarning>
      <body className={`${geistSans.variable} font-sans`}>
        <I18nProvider>{children}</I18nProvider>
      </body>
    </html>
  );
}
