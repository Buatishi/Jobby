import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { KeywordName } from "@/src/app/(app)/ats/[id]/keyword-name";

describe("KeywordName", () => {
  it("marks a keyword the posting presents as nice to have", () => {
    const html = renderToStaticMarkup(<KeywordName keyword="Docker" priority="nice" />);

    expect(html).toContain("Docker");
    expect(html).toContain("Deseable");
  });

  it("shows a required keyword without a mark", () => {
    const html = renderToStaticMarkup(
      <KeywordName keyword="Python" priority="required" />
    );

    expect(html).toContain("Python");
    expect(html).not.toContain("Deseable");
  });

  it("treats a report from before the priority as required", () => {
    const html = renderToStaticMarkup(<KeywordName keyword="SQL" />);

    expect(html).toContain("SQL");
    expect(html).not.toContain("Deseable");
  });
});
