import { describe, expect, it } from "vitest";

import {
  contentSecurityPolicy,
  securityHeaders
} from "@/lib/security/headers";

function headerValue(key: string): string | undefined {
  return securityHeaders.find((header) => header.key === key)?.value;
}

describe("contentSecurityPolicy", () => {
  it("only allows what the app loads from its own origin by default", () => {
    expect(contentSecurityPolicy).toContain("default-src 'self'");
    expect(contentSecurityPolicy).toContain("object-src 'none'");
    expect(contentSecurityPolicy).toContain("base-uri 'self'");
    expect(contentSecurityPolicy).toContain("form-action 'self'");
  });

  it("matches the frame protection the app already has", () => {
    expect(contentSecurityPolicy).toContain("frame-ancestors 'self'");
    expect(headerValue("X-Frame-Options")).toBe("SAMEORIGIN");
  });

  it("allows the services the browser talks to and nothing else", () => {
    expect(contentSecurityPolicy).toContain("https://*.supabase.co");
    expect(contentSecurityPolicy).toContain("wss://*.supabase.co");
    expect(contentSecurityPolicy).toContain("sentry.io");
    expect(contentSecurityPolicy).not.toContain("*.*");
  });

  it("never allows eval", () => {
    expect(contentSecurityPolicy).not.toContain("unsafe-eval");
  });
});

describe("securityHeaders", () => {
  it("starts in report-only mode so a wrong rule cannot break the site", () => {
    expect(headerValue("Content-Security-Policy-Report-Only")).toBe(
      contentSecurityPolicy
    );
    expect(headerValue("Content-Security-Policy")).toBeUndefined();
  });

  it("turns off the browser features the app does not use", () => {
    const policy = headerValue("Permissions-Policy") ?? "";

    for (const feature of ["camera", "microphone", "geolocation", "payment"]) {
      expect(policy).toContain(`${feature}=()`);
    }
  });

  it("keeps the headers it already had", () => {
    expect(headerValue("X-Content-Type-Options")).toBe("nosniff");
    expect(headerValue("Referrer-Policy")).toBe("strict-origin-when-cross-origin");
  });
});
