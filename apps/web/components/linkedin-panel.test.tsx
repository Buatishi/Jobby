import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({ apiClient: vi.fn(), apiStream: vi.fn() }));

import { LinkedInPanel } from "@/components/linkedin-panel";
import { dictionaries } from "@/lib/i18n/dictionaries";
import { I18nProvider } from "@/lib/i18n/provider";

function render() {
  return renderToStaticMarkup(
    <I18nProvider>
      <LinkedInPanel />
    </I18nProvider>
  );
}

describe("LinkedInPanel", () => {
  it("says the PDF is the one LinkedIn downloads and that it is not the CV", () => {
    const html = render();

    expect(html).toContain("PDF de tu perfil de LinkedIn");
    expect(html).toContain("Guardar en PDF");
    expect(html).toContain("No es tu CV");
    expect(html).toContain("«Tu CV»");
  });

  it("keeps the PDF picker working like before", () => {
    const html = render();

    expect(html).toContain('accept="application/pdf"');
    expect(html).toContain("Subir PDF");
  });

  it("says the same in English", () => {
    const en = dictionaries.en.app as Record<string, string>;

    expect(en.linkedinPdfLabel).toMatch(/LinkedIn/);
    expect(en.linkedinPdfNotCv).toMatch(/not your CV/i);
    expect(en.linkedinPdfNotCv).toMatch(/Save to PDF/);
    expect(en.linkedinPdfNotCv).toContain("“Your CV”");
  });
});
