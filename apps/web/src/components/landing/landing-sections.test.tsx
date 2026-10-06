import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "@/lib/i18n/provider";
import { Features } from "@/src/components/landing/features";
import { JobNetwork } from "@/src/components/landing/job-network";
import { Plans } from "@/src/components/landing/plans";
import { Promises } from "@/src/components/landing/promises";
import { StatusPill } from "@/src/components/landing/shared";
import { WhenToUse } from "@/src/components/landing/when-to-use";

function render(node: React.ReactNode) {
  return renderToStaticMarkup(<I18nProvider>{node}</I18nProvider>);
}

describe("landing sections", () => {
  it("lists the five features and marks only the Interview Kit as premium", () => {
    const html = render(<Features />);

    expect(html.match(/<article/g)).toHaveLength(5);
    expect(html.match(/>Premium</g)).toHaveLength(1);
    expect(html).toContain("3 por mes gratis");
  });

  it("opens on the first moment with an accessible tablist", () => {
    const html = render(<WhenToUse />);

    expect(html).toContain('role="tablist"');
    expect(html.match(/role="tab"/g)).toHaveLength(4);
    expect(html).toContain('aria-selected="true"');
    expect(html).toContain("Mirá tu match antes de gastar una postulación");
  });

  it("describes the network for screen readers with the sample scores", () => {
    const html = render(<JobNetwork />);

    expect(html).toContain("86, 78, 71, 54, 38");
    expect(html).toContain("Datos de ejemplo");
  });

  it("shows the real plan limits in both plans", () => {
    const html = render(<Plans />);

    expect(html).toContain("10 análisis de puestos por mes");
    expect(html).toContain("CV Optimizer: 3 por mes");
    expect(html).toContain("CV Optimizer con IA avanzada: 30 por mes");
    expect(html).toContain('href="/register"');
  });

  it("states the privacy and no-invention promises", () => {
    const html = render(<Promises />);

    expect(html).toContain("nunca el contenido de tu CV");
    expect(html).toContain("Sin inventar experiencia");
  });

  it("colors status pills from the shared score tones", () => {
    const html = render(<StatusPill tone="bad">Falta</StatusPill>);

    expect(html).toContain("#FCE4E2");
  });
});
