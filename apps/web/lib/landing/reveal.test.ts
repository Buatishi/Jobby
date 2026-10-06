import { describe, expect, it } from "vitest";

import { litWords, revealProgress } from "@/lib/landing/reveal";

describe("revealProgress", () => {
  it("is 0 while the block is still below the start line", () => {
    expect(revealProgress(900, 200, 800)).toBe(0);
  });

  it("is 1 once the block went past the end of the range", () => {
    expect(revealProgress(-400, 200, 800)).toBe(1);
  });

  it("grows while the block moves up", () => {
    const early = revealProgress(600, 200, 800);
    const late = revealProgress(300, 200, 800);

    expect(early).toBeGreaterThan(0);
    expect(late).toBeGreaterThan(early);
  });
});

describe("litWords", () => {
  it("lights none at the start and all at the end", () => {
    expect(litWords(0, 20)).toBe(0);
    expect(litWords(1, 20)).toBe(20);
  });

  it("clamps out-of-range progress", () => {
    expect(litWords(-1, 10)).toBe(0);
    expect(litWords(2, 10)).toBe(10);
  });
});
