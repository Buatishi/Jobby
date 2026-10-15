import type { Metadata } from "next";

import {
  buildHomeStructuredData,
  serializeJsonLd
} from "@/lib/seo/structured-data";
import { Closing } from "@/src/components/landing/closing";
import { CompareCard } from "@/src/components/landing/compare-card";
import { Features } from "@/src/components/landing/features";
import { Hero } from "@/src/components/landing/hero";
import { JobNetwork } from "@/src/components/landing/job-network";
import { LandingNav } from "@/src/components/landing/landing-nav";
import { ManifestoStats } from "@/src/components/landing/manifesto-stats";
import { Plans } from "@/src/components/landing/plans";
import { Promises } from "@/src/components/landing/promises";
import { RevealStatement } from "@/src/components/landing/reveal-statement";
import { RolesMarquee } from "@/src/components/landing/roles-marquee";
import { WhenToUse } from "@/src/components/landing/when-to-use";

// Canónica propia: los enlaces compartidos con ?utm_* no deben contar como páginas aparte.
export const metadata: Metadata = {
  alternates: { canonical: "/" }
};

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-white text-foreground">
      <script
        dangerouslySetInnerHTML={{
          __html: serializeJsonLd(buildHomeStructuredData())
        }}
        type="application/ld+json"
      />
      <LandingNav />
      <Hero />
      <RolesMarquee />
      <RevealStatement />
      <CompareCard />
      <WhenToUse />
      <Features />
      <JobNetwork />
      <Promises />
      <ManifestoStats />
      <Plans />
      <Closing />
    </main>
  );
}
