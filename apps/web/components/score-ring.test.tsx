import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ScoreRing, clampRingValue } from "@/components/score-ring";

describe("clampRingValue", () => {
  it("limits the value to 0-100 and ignores non-finite numbers", () => {
    expect(clampRingValue(150)).toBe(100);
    expect(clampRingValue(-3)).toBe(0);
    expect(clampRingValue(Number.NaN)).toBe(0);
    expect(clampRingValue(42)).toBe(42);
  });
});

describe("ScoreRing", () => {
  it("is announced as an image with its label", () => {
    const html = renderToStaticMarkup(
      <ScoreRing color="#2BD48A" label="Match: 78/100" trackColor="#3A3A37" value={78} />
    );

    expect(html).toContain('role="img"');
    expect(html).toContain('aria-label="Match: 78/100"');
  });

  it("renders its content over the ring", () => {
    const html = renderToStaticMarkup(
      <ScoreRing color="#2BD48A" label="78" trackColor="#3A3A37" value={78}>
        <span>78</span>
      </ScoreRing>
    );

    expect(html).toContain("<span>78</span>");
  });
});
