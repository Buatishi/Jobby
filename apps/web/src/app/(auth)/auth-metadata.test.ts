import { describe, expect, it, vi } from "vitest";

// `next/font` solo existe dentro del compilador de Next; el layout raíz lo llama al importarse.
vi.mock("next/font/google", () => ({
  Montserrat: () => ({ variable: "font-sans-brand" })
}));

import { metadata as forgotPassword } from "@/src/app/(auth)/forgot-password/layout";
import { metadata as login } from "@/src/app/(auth)/login/layout";
import { metadata as register } from "@/src/app/(auth)/register/layout";
import { metadata as resetPassword } from "@/src/app/(auth)/reset-password/layout";
import sitemap from "@/src/app/sitemap";
import { metadata as root } from "@/src/app/layout";
import { NOINDEX_ROBOTS, SITE_URL } from "@/lib/seo/site";

const authPages = {
  "/login": login,
  "/register": register,
  "/forgot-password": forgotPassword,
  "/reset-password": resetPassword
};

describe("auth pages metadata", () => {
  it("keeps every access screen out of search results but lets its links count", () => {
    for (const [path, page] of Object.entries(authPages)) {
      expect(page.robots, path).toEqual(NOINDEX_ROBOTS);
    }
    expect(NOINDEX_ROBOTS).toEqual({ index: false, follow: true });
  });

  it("gives each one its own title, different from the home title", () => {
    const titles = Object.values(authPages).map((page) => String(page.title));

    expect(new Set(titles).size).toBe(titles.length);
    for (const title of titles) {
      expect(title).toContain("Jobby");
      expect(title).not.toBe(String(root.title));
    }
  });

  it("does not list any of them in the sitemap", () => {
    const urls = sitemap().map((entry) => entry.url);

    for (const path of Object.keys(authPages)) {
      expect(urls).not.toContain(`${SITE_URL}${path}`);
    }
  });

  it("leaves the home indexable", () => {
    expect(root.robots).toBeUndefined();
  });
});
