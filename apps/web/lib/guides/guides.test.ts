import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import {
  ATS_FORMAT_PENALTIES,
  ATS_KEYWORD_POINTS,
  CV_OPTIMIZATIONS_PER_MONTH,
  FREE_JOB_ANALYSES_PER_MONTH,
  FULL_RELEVANCE_PERCENT,
  GAP_THRESHOLD_PERCENT,
  MATCH_SCORE_WEIGHTS
} from "@/lib/guides/facts";
import { GUIDES, getGuide } from "@/lib/guides/guides";
import { GUIDE_LINKS } from "@/lib/guides/links";
import type { Guide } from "@/lib/guides/types";

function readService(relativePath: string) {
  return readFileSync(
    fileURLToPath(
      new URL(
        `../../../../services/api/app/services/${relativePath}`,
        import.meta.url
      )
    ),
    "utf8"
  );
}

function guideText(guide: Guide) {
  const parts = [guide.title, guide.intro];
  for (const section of guide.sections) {
    parts.push(section.heading);
    for (const block of section.blocks) {
      parts.push(block.type === "paragraph" ? block.text : block.items.join(" "));
    }
  }
  return parts.join(" ");
}

function wordCount(text: string) {
  return text.split(/\s+/).filter(Boolean).length;
}

describe("guides content", () => {
  it("has unique, url-safe slugs", () => {
    const slugs = GUIDES.map((guide) => guide.slug);

    expect(new Set(slugs).size).toBe(slugs.length);
    for (const slug of slugs) {
      expect(slug).toMatch(/^[a-z0-9]+(-[a-z0-9]+)*$/);
    }
  });

  it("has one footer link per guide, in the same order", () => {
    expect(GUIDE_LINKS.map((link) => link.slug)).toEqual(
      GUIDES.map((guide) => guide.slug)
    );
  });

  it("finds a guide by slug and returns nothing for an unknown one", () => {
    expect(getGuide(GUIDES[0].slug)).toBe(GUIDES[0]);
    expect(getGuide("no-existe")).toBeUndefined();
  });

  it.each(GUIDES.map((guide) => [guide.slug, guide] as const))(
    "%s: title and description fit the results page",
    (_slug, guide) => {
      expect(guide.seoTitle.length).toBeLessThanOrEqual(60);
      expect(guide.seoTitle).toContain("Jobby");
      expect(guide.description.length).toBeGreaterThanOrEqual(70);
      expect(guide.description.length).toBeLessThanOrEqual(160);
    }
  );

  it("gives every guide its own title and description", () => {
    expect(new Set(GUIDES.map((guide) => guide.seoTitle)).size).toBe(GUIDES.length);
    expect(new Set(GUIDES.map((guide) => guide.description)).size).toBe(
      GUIDES.length
    );
  });

  it.each(GUIDES.map((guide) => [guide.slug, guide] as const))(
    "%s: has enough text to be useful and no empty section",
    (_slug, guide) => {
      expect(wordCount(guideText(guide))).toBeGreaterThanOrEqual(450);
      expect(guide.sections.length).toBeGreaterThanOrEqual(4);
      for (const section of guide.sections) {
        expect(section.blocks.length).toBeGreaterThan(0);
      }
    }
  );

  it.each(GUIDES.map((guide) => [guide.slug, guide] as const))(
    "%s: only links to other guides that exist",
    (_slug, guide) => {
      expect(guide.related.length).toBeGreaterThan(0);
      for (const slug of guide.related) {
        expect(slug).not.toBe(guide.slug);
        expect(getGuide(slug)).toBeDefined();
      }
    }
  );

  it("promises no result", () => {
    for (const guide of GUIDES) {
      expect(guideText(guide)).not.toMatch(
        /garantiz|te aseguramos|conseguirás|conseguiras/i
      );
    }
  });

  it("quotes no percentage that is not a product figure", () => {
    const allowed = new Set<number>([
      100,
      FULL_RELEVANCE_PERCENT,
      GAP_THRESHOLD_PERCENT,
      MATCH_SCORE_WEIGHTS[0].percent + MATCH_SCORE_WEIGHTS[1].percent,
      ...MATCH_SCORE_WEIGHTS.map((weight) => weight.percent)
    ]);

    for (const guide of GUIDES) {
      for (const match of guideText(guide).matchAll(/(\d+)\s?%/g)) {
        expect(allowed.has(Number(match[1])), `${guide.slug}: ${match[0]}`).toBe(
          true
        );
      }
    }
  });
});

describe("guide figures match the backend code", () => {
  it("uses the weights of the match score formula", () => {
    const source = readService("match_engine/formula.py");
    const inCode = new Map<string, number>();
    for (const match of source.matchAll(/scores\["(\w+)"\]\s*\*\s*(0\.\d+)/g)) {
      inCode.set(match[1], Math.round(Number(match[2]) * 100));
    }

    expect(inCode.size).toBe(MATCH_SCORE_WEIGHTS.length);
    for (const weight of MATCH_SCORE_WEIGHTS) {
      expect(inCode.get(weight.key), weight.key).toBe(weight.percent);
    }
    expect(MATCH_SCORE_WEIGHTS.reduce((sum, weight) => sum + weight.percent, 0)).toBe(
      100
    );
  });

  it("uses the threshold that marks a component as a gap", () => {
    const source = readService("match_engine/formula.py");
    const thresholds = [...source.matchAll(/(?:skills|seniority)_score < (0\.\d+)/g)].map(
      (match) => Math.round(Number(match[1]) * 100)
    );

    expect(thresholds).toEqual([GAP_THRESHOLD_PERCENT, GAP_THRESHOLD_PERCENT]);
  });

  it("uses the share of required skills that makes a job count as the person's area", () => {
    const source = readService("match_engine/s_relevance.py");
    const match = source.match(/FULL_RELEVANCE_AT = (0\.\d+)/);

    expect(Math.round(Number(match?.[1]) * 100)).toBe(FULL_RELEVANCE_PERCENT);
  });

  it("uses the ATS format penalties", () => {
    const source = readService("ats_analyzer/format_checker.py");
    const inCode = new Map<string, number>();
    for (const match of source.matchAll(
      /FormatIssue\(\s*"(\w+)",\s*"[^"]*",\s*(\d+),?\s*\)/g
    )) {
      inCode.set(match[1], Number(match[2]));
    }

    for (const [code, penalty] of Object.entries(ATS_FORMAT_PENALTIES)) {
      expect(inCode.get(code), code).toBe(penalty);
    }
  });

  it("uses the points of each keyword match", () => {
    const source = readService("ats_analyzer/scoring.py");
    const match = source.match(
      /literal_hits \* ([\d.]+) \+ semantic_hits \* ([\d.]+)/
    );

    expect(Number(match?.[1])).toBe(ATS_KEYWORD_POINTS.literal);
    expect(Number(match?.[2])).toBe(ATS_KEYWORD_POINTS.semantic);
  });

  it("uses the monthly limits of each plan", () => {
    const source = readService("rate_limits.py");
    const jobs = source.match(
      /RateLimitKind\.JOBS:\s*return RateLimitRule\(limit=None if premium else (\d+),\s*period="month"/
    );
    const optimizations = source.match(
      /RateLimitKind\.CV_OPTIMIZATION:\s*return RateLimitRule\(limit=(\d+) if premium else (\d+),\s*period="month"/
    );

    expect(Number(jobs?.[1])).toBe(FREE_JOB_ANALYSES_PER_MONTH);
    expect(Number(optimizations?.[2])).toBe(CV_OPTIMIZATIONS_PER_MONTH.free);
    expect(Number(optimizations?.[1])).toBe(CV_OPTIMIZATIONS_PER_MONTH.premium);
  });

  it("writes the figures the newer guides cite", () => {
    const checklist = guideText(getGuide("cv-compatible-con-ats")!);
    expect(checklist).toContain(`${ATS_FORMAT_PENALTIES.TABLES} si el CV tiene tablas`);
    expect(checklist).toContain(
      `${ATS_FORMAT_PENALTIES.NON_STANDARD_HEADERS} si algún título`
    );

    const analysis = guideText(getGuide("analizar-cv-con-ia")!);
    expect(analysis).toContain(
      `${FREE_JOB_ANALYSES_PER_MONTH} análisis de puestos por mes`
    );

    const optimizer = guideText(getGuide("optimizar-cv-con-ia")!);
    expect(optimizer).toContain(
      `${CV_OPTIMIZATIONS_PER_MONTH.free} optimizaciones por mes`
    );
    expect(optimizer).toContain(`el premium, ${CV_OPTIMIZATIONS_PER_MONTH.premium}`);

    const skills = guideText(getGuide("habilidades-para-poner-en-el-cv")!);
    expect(skills).toContain(
      `${MATCH_SCORE_WEIGHTS[0].label} (${MATCH_SCORE_WEIGHTS[0].percent} %)`
    );
    expect(skills).toContain(`pesan ${MATCH_SCORE_WEIGHTS[5].percent} %`);
  });

  it("writes the figures it cites in the guide text", () => {
    const matchScore = guideText(getGuide("que-es-el-match-score")!);
    for (const weight of MATCH_SCORE_WEIGHTS) {
      expect(matchScore).toContain(`${weight.label} (${weight.percent} %)`);
    }

    const ats = guideText(getGuide("que-es-un-ats")!);
    expect(ats).toContain(`${ATS_FORMAT_PENALTIES.TABLES} si el CV tiene tablas`);
    expect(ats).toContain(
      `${ATS_FORMAT_PENALTIES.NON_STANDARD_HEADERS} si algún título`
    );
    expect(ats).toContain("suma 0,5");
  });

  it("describes the ATS report with the marks the page really shows", () => {
    const page = readFileSync(
      fileURLToPath(
        new URL("../../src/app/(app)/ats/[id]/page.tsx", import.meta.url)
      ),
      "utf8"
    );
    for (const mark of ["✓", "~", "✗"]) {
      expect(page).toContain(`return "${mark}"`);
    }

    const analysis = guideText(getGuide("analizar-cv-con-ia")!);
    expect(analysis).toContain("presente (✓), parecida (~) o faltante (✗)");
    // «Cumple / Parcial / Falta» es el ejemplo de la landing, no lo que muestra el reporte.
    for (const guide of GUIDES) {
      expect(guideText(guide)).not.toContain("cumplís en parte");
    }
  });
});
