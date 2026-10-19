import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { middleware } from "@/src/middleware";

const aiSearchAgents = [
  "Mozilla/5.0 (compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)",
  "Mozilla/5.0 (compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
  "Mozilla/5.0 AppleWebKit/537.36 (compatible; ChatGPT-User/1.0; +https://openai.com/bot)"
];

const trainingAgents = [
  "Mozilla/5.0 (compatible; GPTBot/1.2; +https://openai.com/gptbot)",
  "CCBot/2.0 (https://commoncrawl.org/faq/)"
];

const privatePaths = [
  "/admin",
  "/api/backend/health",
  "/dashboard",
  "/profile",
  "/jobs/123",
  "/ats/abc",
  "/reality-gap",
  "/interview-kits/new",
  "/wizard/step-1",
  "/billing"
];

function call(path: string, userAgent: string) {
  return middleware(
    new NextRequest(`https://jobbyweb.vercel.app${path}`, {
      headers: { "user-agent": userAgent }
    })
  );
}

describe("middleware and the AI search crawlers", () => {
  it.each(aiSearchAgents)("answers 403 on every private route to %s", (agent) => {
    for (const path of privatePaths) {
      const response = call(path, agent);

      expect(response.status, path).toBe(403);
      expect(response.headers.get("x-robots-tag")).toContain("noindex");
    }
  });

  it.each(trainingAgents)("answers 403 on private routes to %s", (agent) => {
    expect(call("/dashboard", agent).status).toBe(403);
  });

  it("marks private routes noindex for a normal browser without blocking it", () => {
    const response = call("/dashboard", "Mozilla/5.0 Chrome/130.0");

    expect(response.status).toBe(200);
    expect(response.headers.get("x-robots-tag")).toContain("noindex");
  });

  it.each(aiSearchAgents)("lets %s through on the public pages", (agent) => {
    for (const path of ["/", "/pricing", "/terms", "/privacy"]) {
      const response = call(path, agent);

      expect(response.status, path).toBe(200);
      expect(response.headers.get("x-robots-tag")).toBeNull();
    }
  });
});
