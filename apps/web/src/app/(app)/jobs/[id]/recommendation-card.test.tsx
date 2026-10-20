import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { RecommendationCard } from "./recommendation-card";

const line =
  'Sumá "API REST" y "Git" como skills nombradas**: incluí proyectos donde hayas construido o consumido APIs y trabajado con Git en equipo.';

describe("RecommendationCard", () => {
  it("shows the heading once, the body below and no markdown marks", () => {
    const html = renderToStaticMarkup(
      <RecommendationCard
        recommendation={{
          title: line.slice(0, 80),
          description: line,
          priority: "high"
        }}
      />
    );

    expect(html).not.toContain("*");
    expect(html).toContain("Sumá &quot;API REST&quot; y &quot;Git&quot; como skills nombradas");
    expect(html).toContain("incluí proyectos donde hayas construido");
    expect(html).not.toContain("donde hayas co<");
    expect(html.match(/skills nombradas/g)).toHaveLength(1);
    expect(html).toContain("high");
  });

  it("renders only the heading when there is no body", () => {
    const html = renderToStaticMarkup(
      <RecommendationCard
        recommendation={{ title: "Agregá React al CV", description: "Agregá React al CV" }}
      />
    );

    expect(html.match(/Agregá React al CV/g)).toHaveLength(1);
    expect(html).toContain("medium");
  });

  it("renders nothing for an empty recommendation", () => {
    expect(renderToStaticMarkup(<RecommendationCard recommendation={{}} />)).toBe("");
  });
});
