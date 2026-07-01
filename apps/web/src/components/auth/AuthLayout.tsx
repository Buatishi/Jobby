import Link from "next/link";
import { Check } from "lucide-react";

import { MatchScoreCard } from "@/components/match-score-card";

type AuthLayoutProps = {
  children: React.ReactNode;
  headline: string;
};

const bullets = [
  "Match score real basado en tu CV",
  "Kit de entrevista personalizado",
  "Empezá gratis, sin tarjeta"
];

export function AuthLayout({ children, headline }: AuthLayoutProps) {
  return (
    <main className="grid min-h-screen bg-white md:grid-cols-[60%_40%]">
      <section className="relative overflow-hidden bg-[#0F6E56] px-6 py-8 text-white md:min-h-screen md:px-12 md:py-16 lg:px-16">
        {/* Fondo decorativo fuera del flujo: usa z-0 y no contiene texto ni controles. */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(circle_at_20%_10%,rgba(255,255,255,0.18),transparent_30%),linear-gradient(135deg,#0F6E56_0%,#064536_100%)]"
        />
        <div className="relative z-10 flex min-h-[140px] flex-col md:min-h-[calc(100vh-8rem)] md:justify-center">
          <div className="max-w-xl md:pt-20">
            <h1 className="max-w-lg text-3xl font-black leading-tight tracking-tight md:text-5xl">
              {headline}
            </h1>
            <div className="mt-8 hidden space-y-4 md:block">
              {bullets.map((bullet) => (
                <div className="flex items-center gap-3" key={bullet}>
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white/12 text-white">
                    <Check className="h-4 w-4" />
                  </span>
                  <span className="text-sm font-semibold text-white/88">{bullet}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-12 hidden w-full max-w-md rotate-[-2deg] md:block">
            <MatchScoreCard compact />
          </div>
        </div>
      </section>

      <section className="flex min-h-[calc(100vh-140px)] flex-col px-6 py-8 md:min-h-screen md:px-10 lg:px-14">
        <Link
          className="mb-10 inline-flex w-fit text-xl font-bold tracking-normal text-foreground transition hover:text-[#0F6E56]"
          href="/"
        >
          jobby
        </Link>
        <div className="flex flex-1 items-center">
          <div className="mx-auto w-full max-w-md">{children}</div>
        </div>
      </section>
    </main>
  );
}
