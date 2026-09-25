"use client";

import "./globals.css";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";

type GlobalErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

// Reemplaza al layout raíz cuando falla él mismo: no hay proveedor de idioma, va en español.
export default function GlobalError({ error, reset }: GlobalErrorProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html lang="es">
      <body className="font-sans">
        <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center px-4 text-center">
          <h1 className="text-2xl font-semibold">Jobby no pudo cargar</h1>
          <p className="mt-3 text-muted-foreground">
            Puede ser una falla momentánea: probá de nuevo en unos segundos.
          </p>
          <Button className="mt-6" onClick={reset} type="button">
            Reintentar
          </Button>
        </main>
      </body>
    </html>
  );
}
