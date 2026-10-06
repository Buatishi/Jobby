import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type { DashboardSummary } from "@/lib/dashboard/summary";

vi.mock("next/navigation", () => ({ usePathname: () => "/dashboard" }));

import { DashboardView } from "@/components/dashboard/dashboard-client";
import { I18nProvider } from "@/lib/i18n/provider";

const summary: DashboardSummary = {
  full_name: "Persona de Prueba",
  employability_score: 78,
  completeness_pct: 72,
  missing_tip: "Sumá tus herramientas principales",
  latest_matches: [
    { id: "m1", company: "Empresa de ejemplo", role: "Backend Developer", score: 86 },
    { id: "m2", company: "Estudio de ejemplo", role: "Data Engineer", score: 54 }
  ]
};

function render(props: { summary?: DashboardSummary; error?: string | null; isLoading?: boolean }) {
  return renderToStaticMarkup(
    <I18nProvider>
      <DashboardView
        error={props.error ?? null}
        isLoading={props.isLoading ?? false}
        summary={props.summary}
      />
    </I18nProvider>
  );
}

describe("DashboardView", () => {
  it("greets the person by first name and shows the profile tip", () => {
    const html = render({ summary });

    expect(html).toContain("Persona");
    expect(html).not.toContain("Persona de Prueba");
    expect(html).toContain("Sumá tus herramientas principales");
  });

  it("links each match to its report and shows its score ring", () => {
    const html = render({ summary });

    expect(html).toContain('href="/jobs/m1"');
    expect(html).toContain('href="/jobs/m2"');
    expect(html).toContain("Backend Developer");
    expect(html).toContain('aria-label="86/100"');
    expect(html).toContain('aria-label="54/100"');
  });

  it("offers to complete the profile only below 80 percent", () => {
    expect(render({ summary })).toContain('href="/wizard/step-1"');
    expect(
      render({ summary: { ...summary, completeness_pct: 90 } })
    ).not.toContain('href="/wizard/step-1"');
  });

  it("shows the empty state without matches", () => {
    const html = render({ summary: { ...summary, latest_matches: [] } });

    expect(html).not.toContain('href="/jobs/');
    expect(html).toContain("lucide-briefcase");
  });

  it("shows the error without hiding the page", () => {
    const html = render({ summary, error: "No pudimos cargar el resumen" });

    expect(html).toContain("No pudimos cargar el resumen");
    expect(html).toContain('id="analizar"');
  });
});
