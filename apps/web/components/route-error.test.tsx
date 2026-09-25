import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { RouteError } from "@/components/route-error";
import { I18nProvider } from "@/lib/i18n/provider";

function render(home: "landing" | "dashboard") {
  const error = new Error("detalle interno: columna users.tier");
  return renderToStaticMarkup(
    <I18nProvider>
      <RouteError error={error} home={home} reset={() => undefined} />
    </I18nProvider>
  );
}

describe("RouteError", () => {
  it("offers a retry and a way out without internal details", () => {
    const html = render("dashboard");

    expect(html).toContain('role="alert"');
    expect(html).toContain("No pudimos mostrar esta sección");
    expect(html).toContain("Reintentar");
    expect(html).toContain('href="/dashboard"');
    expect(html).not.toContain("detalle interno");
  });

  it("sends people outside the app back home", () => {
    const html = render("landing");

    expect(html).toContain('href="/"');
    expect(html).toContain("Ir al inicio");
  });
});
