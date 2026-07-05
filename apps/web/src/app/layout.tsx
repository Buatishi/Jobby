import type { Metadata, Viewport } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

import { I18nProvider } from "@/lib/i18n/provider";

const geistSans = Geist({
  subsets: ["latin"],
  variable: "--font-geist-sans"
});

export const metadata: Metadata = {
  title: "Jobby",
  description: "AI-assisted job matching for candidates and teams."
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
