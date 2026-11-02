import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  DeclareKeywords,
  optimizeRequestBody,
  type MissingKeyword
} from "@/src/app/(app)/ats/[id]/declare-keywords";

const missing: MissingKeyword[] = [
  { keyword: "CI/CD" },
  { keyword: "Django", priority: "required" },
  { keyword: "AI", priority: "nice" }
];

function render(selected: string[] = [], disabled = false) {
  return renderToStaticMarkup(
    <DeclareKeywords
      disabled={disabled}
      missing={missing}
      onToggle={() => undefined}
      selected={selected}
    />
  );
}

describe("DeclareKeywords", () => {
  it("says what is missing and why it was not written", () => {
    const html = render();

    expect(html).toContain("Qué falta para que el puntaje suba");
    expect(html).toContain("no figuran en tu CV ni en tu LinkedIn");
    expect(html).toContain("no hay con qué saber que las conocés");
    for (const item of missing) {
      expect(html).toContain(item.keyword);
    }
  });

  it("lets the person confirm the ones they know, never as experience", () => {
    const html = render();

    expect(html.match(/type="checkbox"/g)).toHaveLength(3);
    expect(html).toContain("Marcá solo las que podés defender en una entrevista");
    expect(html).toContain("nunca como experiencia");
    expect(html).toContain("Cada optimización cuenta en tu cupo del mes");
  });

  it("marks the ones already chosen and none otherwise", () => {
    expect(render().match(/checked=""/g)).toBeNull();
    expect(render(["Django", "AI"]).match(/checked=""/g)).toHaveLength(2);
  });

  it("flags the nice to have ones the posting calls optional", () => {
    expect(render()).toContain("Deseable");
  });

  it("disables the boxes while optimizing", () => {
    expect(render([], true).match(/disabled=""/g)).toHaveLength(3);
  });

  it("shows nothing when no keyword is missing", () => {
    expect(
      renderToStaticMarkup(
        <DeclareKeywords missing={[]} onToggle={() => undefined} selected={[]} />
      )
    ).toBe("");
  });
});

describe("optimizeRequestBody", () => {
  it("sends the chosen keywords with the job", () => {
    expect(optimizeRequestBody("job-1", ["Django", "CI/CD"], missing)).toEqual({
      job_id: "job-1",
      confirmed_keywords: ["Django", "CI/CD"]
    });
  });

  it("sends an empty list when nothing was chosen", () => {
    expect(optimizeRequestBody("job-1", [], missing)).toEqual({
      job_id: "job-1",
      confirmed_keywords: []
    });
  });

  it("drops a keyword the report no longer lists as missing", () => {
    expect(optimizeRequestBody("job-1", ["Django", "Kubernetes"], missing)).toEqual({
      job_id: "job-1",
      confirmed_keywords: ["Django"]
    });
  });
});
