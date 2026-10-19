import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const publicDir = new URL("../../public/", import.meta.url);

function readPublic(name: string) {
  return readFileSync(fileURLToPath(new URL(name, publicDir)), "utf8");
}

type Group = { agents: string[]; disallow: string[]; allow: string[] };

// Lector mínimo de robots.txt: agrupa las reglas por bloque de `User-agent`.
function parseRobots(text: string): Group[] {
  const groups: Group[] = [];
  let current: Group | null = null;
  let collectingAgents = false;

  for (const raw of text.split(/\r?\n/)) {
    const line = raw.split("#")[0].trim();
    if (!line) continue;
    const [field, ...rest] = line.split(":");
    const value = rest.join(":").trim();
    const key = field.trim().toLowerCase();

    if (key === "user-agent") {
      if (!current || !collectingAgents) {
        current = { agents: [], disallow: [], allow: [] };
        groups.push(current);
      }
      current.agents.push(value.toLowerCase());
      collectingAgents = true;
    } else if (current && (key === "disallow" || key === "allow")) {
      current[key].push(value);
      collectingAgents = false;
    }
  }
  return groups;
}

const robots = parseRobots(readPublic("robots.txt"));

function groupFor(agent: string) {
  return robots.find((group) => group.agents.includes(agent.toLowerCase()));
}

// Rastreadores de entrenamiento y de extracción: siguen bloqueados en todo el sitio.
const blockedEverywhere = [
  "GPTBot",
  "ClaudeBot",
  "Claude-User",
  "Google-Extended",
  "Amazonbot",
  "Bytespider",
  "CCBot",
  "Applebot-Extended",
  "Meta-ExternalAgent",
  "YouBot",
  "Anthropic-ai"
];

// Búsqueda de IA y consultas a pedido de una persona: leen las páginas públicas.
const aiSearchAgents = ["OAI-SearchBot", "PerplexityBot", "ChatGPT-User"];

describe("robots.txt for AI crawlers", () => {
  it.each(blockedEverywhere)("keeps %s blocked on the whole site", (agent) => {
    expect(groupFor(agent)?.disallow).toContain("/");
  });

  it.each(aiSearchAgents)(
    "gives %s no group of its own, so it follows the * rules",
    (agent) => {
      expect(groupFor(agent)).toBeUndefined();
    }
  );

  it("lets everyone read the public pages and keeps the private routes out", () => {
    const everyone = groupFor("*");

    expect(everyone?.allow).toContain("/");
    expect(everyone?.disallow).not.toContain("/");
    expect(everyone?.disallow).toEqual(
      expect.arrayContaining([
        "/dashboard",
        "/profile",
        "/jobs",
        "/ats",
        "/reality-gap",
        "/interview-kits",
        "/wizard",
        "/billing",
        "/api/"
      ])
    );
  });

  it("points to the sitemap", () => {
    expect(readPublic("robots.txt")).toMatch(
      /^Sitemap: https:\/\/jobbyweb\.vercel\.app\/sitemap\.xml$/m
    );
  });
});

describe("llms.txt", () => {
  // Los renglones se parten a mano: se compara con los espacios colapsados.
  const llms = readPublic("llms.txt").replace(/\s+/g, " ");

  it.each(aiSearchAgents)("names %s as allowed on public pages", (agent) => {
    expect(llms).toContain(agent);
  });

  it("still forbids training and bulk extraction", () => {
    expect(llms.toLowerCase()).toContain("model training");
    expect(llms.toLowerCase()).toContain("bulk extraction");
  });

  it("keeps the private routes and user content off limits", () => {
    expect(llms.toLowerCase()).toContain("authenticated user content");
  });
});
