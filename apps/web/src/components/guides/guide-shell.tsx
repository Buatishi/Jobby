import Link from "next/link";
import type { ReactNode } from "react";

// Marco de las guías: página de lectura sin la navegación de la home, que apunta a anclas
// (#cuando, #funciones) que no existen fuera de ella.
export function GuideShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-white text-foreground">
      <header className="border-b border-brand-line">
        <div className="mx-auto flex h-[68px] max-w-3xl items-center justify-between gap-4 px-5 sm:px-8">
          <Link
            className="flex items-center gap-2 text-[22px] font-bold tracking-tight"
            href="/"
          >
            <span
              aria-hidden="true"
              className="flex h-[30px] w-[30px] items-center justify-center rounded-[10px] bg-brand-bright text-[17px]"
            >
              J
            </span>
            Jobby
          </Link>
          <nav
            aria-label="Guías"
            className="flex items-center gap-4 text-sm font-medium"
          >
            <Link
              className="text-neutral-600 transition-colors hover:text-brand-ink"
              href="/guias"
            >
              Guías
            </Link>
            <Link
              className="rounded-full bg-brand-bright px-4 py-2 font-semibold text-brand-ink transition-opacity hover:opacity-90"
              href="/register"
            >
              Empezar gratis
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-5 py-12 sm:px-8">{children}</main>

      <footer className="border-t border-brand-line">
        <div className="mx-auto max-w-3xl px-5 py-8 text-sm text-neutral-600 sm:px-8">
          <p>
            Contenido orientativo. Cada empresa y cada sistema de selección usa sus propios
            criterios, y ninguna guía garantiza una entrevista ni una contratación.
          </p>
          <nav aria-label="Legal" className="mt-4 flex gap-4 font-medium">
            <Link className="hover:text-brand-ink" href="/terms">
              Términos
            </Link>
            <Link className="hover:text-brand-ink" href="/privacy">
              Privacidad
            </Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
