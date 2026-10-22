import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "@/lib/i18n/provider";
import { SITE_CONTACT_EMAIL } from "@/lib/seo/site";
import PrivacyPage from "@/src/app/privacy/page";
import TermsPage from "@/src/app/terms/page";

const webRoot = fileURLToPath(new URL("../../", import.meta.url));

function render(node: React.ReactNode) {
  return renderToStaticMarkup(<I18nProvider>{node}</I18nProvider>);
}

function sourceFiles(directory: string): string[] {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);
    if (statSync(path).isDirectory()) {
      return name === "node_modules" || name === ".next" ? [] : sourceFiles(path);
    }
    return /\.(tsx?|txt|md|json)$/.test(name) ? [path] : [];
  });
}

describe("contact address", () => {
  it("is a real mailbox of the project", () => {
    expect(SITE_CONTACT_EMAIL).toBe("developjobby@gmail.com");
  });

  it("shows the contact in the terms and in the privacy policy", () => {
    expect(render(<TermsPage />)).toContain(SITE_CONTACT_EMAIL);
    expect(render(<PrivacyPage />)).toContain(SITE_CONTACT_EMAIL);
  });

  it("is the one llms.txt gives to AI crawlers", () => {
    const llms = readFileSync(join(webRoot, "public", "llms.txt"), "utf8");

    expect(llms).toContain(`Contact: ${SITE_CONTACT_EMAIL}`);
  });

  // El buzón de dominio propio que figuraba antes nunca existió: no puede volver a la web.
  it("never mentions the old jobby.ai mailbox anywhere in the web app", () => {
    const oldDomain = ["@jobby", ".ai"].join("");
    const offenders = ["src", "lib", "components", "public"]
      .flatMap((folder) => sourceFiles(join(webRoot, folder)))
      .filter((file) => readFileSync(file, "utf8").includes(oldDomain));

    expect(offenders).toEqual([]);
  });
});
