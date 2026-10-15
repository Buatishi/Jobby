import type { Metadata, Viewport } from "next";
import { Montserrat } from "next/font/google";
import "./globals.css";

import { ColdStartNotice } from "@/components/cold-start-notice";
import { I18nProvider } from "@/lib/i18n/provider";
import { SITE_NAME, SITE_URL } from "@/lib/seo/site";

// Fuente variable: cubre los pesos 400 a 700 y la cursiva de las cifras grandes.
const montserrat = Montserrat({
  subsets: ["latin"],
  style: ["normal", "italic"],
  variable: "--font-sans-brand",
  display: "swap"
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "Jobby — Sabé cuánto matcheás antes de aplicar",
  description:
    "Jobby compara tu CV con un puesto real usando IA: match score, compatibilidad ATS, gaps y recomendaciones para postularte mejor.",
  openGraph: {
    title: "Jobby — Sabé cuánto matcheás antes de aplicar",
    description:
      "Subí tu CV, pegá un puesto y recibí match score, ATS, gaps reales y recomendaciones accionables.",
    images: ["/og-image.png"],
    siteName: SITE_NAME,
    type: "website",
    url: SITE_URL
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
      <body className={`${montserrat.variable} font-sans`}>
        <I18nProvider>
          {children}
          <ColdStartNotice />
        </I18nProvider>
      </body>
    </html>
  );
}
