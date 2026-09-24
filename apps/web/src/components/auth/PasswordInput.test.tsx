import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PasswordInput } from "@/src/components/auth/PasswordInput";
import { I18nProvider } from "@/lib/i18n/provider";

function render(props: Parameters<typeof PasswordInput>[0] = {}) {
  return renderToStaticMarkup(
    <I18nProvider>
      <PasswordInput id="password" {...props} />
    </I18nProvider>
  );
}

describe("PasswordInput", () => {
  it("starts hidden, with a button to show the password", () => {
    const html = render();

    expect(html).toContain('type="password"');
    expect(html).toContain('aria-label="Mostrar contraseña"');
    expect(html).toContain('aria-pressed="false"');
    expect(html).toContain('aria-controls="password"');
  });

  it("leaves room for the button and keeps the field props", () => {
    const html = render({
      autoComplete: "current-password",
      className: "h-12 w-full",
      minLength: 6
    });

    expect(html).toContain('class="h-12 w-full pr-11"');
    expect(html).toContain('autoComplete="current-password"');
    expect(html).toContain('minLength="6"');
  });

  it("does not warn about Caps Lock before any key is pressed", () => {
    expect(render()).not.toContain("Bloq Mayús");
  });

  it("disables the button together with the field", () => {
    expect(render({ disabled: true })).toMatch(/<button[^>]*disabled=""/);
  });
});
