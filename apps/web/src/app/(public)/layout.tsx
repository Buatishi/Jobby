import { Analytics } from "@vercel/analytics/next";

// Se mide de dónde llega la gente que no tiene cuenta (inicio, precios y guías). El panel,
// los puestos y los reportes no se miden: ahí hay datos de la persona.
export default function PublicLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <>
      {children}
      <Analytics />
    </>
  );
}
