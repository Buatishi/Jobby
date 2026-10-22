import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({ apiClient: vi.fn(), apiStream: vi.fn() }));

import { CvPanel, CvPanelView, type CvPanelViewProps } from "@/components/cv-panel";
import { I18nProvider } from "@/lib/i18n/provider";

function view(overrides: Partial<CvPanelViewProps> = {}) {
  const props: CvPanelViewProps = {
    file: null,
    busy: false,
    stageText: null,
    current: null,
    notice: null,
    error: null,
    onFileChange: () => undefined,
    onUpload: () => undefined,
    ...overrides
  };
  return renderToStaticMarkup(
    <I18nProvider>
      <CvPanelView {...props} />
    </I18nProvider>
  );
}

describe("CvPanel", () => {
  it("renders as the card where the CV goes, and says what the file is for", () => {
    const html = renderToStaticMarkup(
      <I18nProvider>
        <CvPanel />
      </I18nProvider>
    );

    expect(html).toContain("Tu CV");
    expect(html).toContain("se manda a las empresas");
  });
});

describe("CvPanelView", () => {
  it("accepts only PDFs and starts with the upload button disabled", () => {
    const html = view();

    expect(html).toContain('accept="application/pdf"');
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>(?:<[^>]*>)*Subir CV/);
  });

  it("warns that a new file replaces the old one, without claiming one exists", () => {
    const html = view();

    expect(html).toContain("reemplaza");
    expect(html).not.toContain("Todavía no subiste");
  });

  it("enables the upload once a file is picked and shows its name", () => {
    const html = view({
      file: new File(["x"], "Mi CV 2026.pdf", { type: "application/pdf" })
    });

    expect(html).toContain("Mi CV 2026.pdf");
    expect(html).not.toMatch(/<button[^>]*disabled=""[^>]*>(?:<[^>]*>)*Subir CV/);
  });

  it("locks the picker and the button while the CV is being uploaded or read", () => {
    const html = view({
      file: new File(["x"], "Mi CV.pdf", { type: "application/pdf" }),
      busy: true,
      stageText: "Leyendo tu CV..."
    });

    expect(html).toMatch(/<input[^>]*disabled=""[^>]*type="file"/);
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>.*Procesando/);
    expect(html).toContain("Leyendo tu CV...");
  });

  it("shows the main CV that was just uploaded, with its name and date", () => {
    const html = view({
      current: { filename: "CV Bautista Giraud.pdf", uploadedAt: "2026-10-21T15:00:00+00:00" },
      notice: "CV subido y leído."
    });

    expect(html).toContain("CV Bautista Giraud.pdf");
    expect(html).toContain("2026");
    expect(html).toContain("CV subido y leído.");
  });

  it("shows the main CV without a date when the server did not send one", () => {
    const html = view({ current: { filename: "CV.pdf", uploadedAt: null } });

    expect(html).toContain("CV.pdf");
    expect(html).not.toContain("subido el");
  });

  it("announces an error as an alert", () => {
    const html = view({ error: "Límite diario de cargas de documentos alcanzado" });

    expect(html).toMatch(/role="alert"[^>]*>Límite diario de cargas de documentos alcanzado/);
  });
});
