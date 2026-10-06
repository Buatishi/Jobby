import { describe, expect, it } from "vitest";

import {
  getScoreColor,
  getScoreColorOnDark,
  scoreColorOnDarkGreen,
  scoreColors
} from "@/lib/utils/score-colors";

describe("getScoreColor", () => {
  it.each([
    [0, scoreColors.red],
    [40, scoreColors.red],
    [41, scoreColors.yellow],
    [65, scoreColors.yellow],
    [66, scoreColors.lightGreen],
    [80, scoreColors.lightGreen],
    [81, scoreColors.darkGreen],
    [100, scoreColors.darkGreen]
  ])("colors %i with its band", (score, color) => {
    expect(getScoreColor(score)).toBe(color);
  });
});

describe("getScoreColorOnDark", () => {
  it("shows both green bands with the bright green on dark panels", () => {
    expect(getScoreColorOnDark(78)).toBe(scoreColorOnDarkGreen);
    expect(getScoreColorOnDark(86)).toBe(scoreColorOnDarkGreen);
  });

  it("keeps red and yellow as they are", () => {
    expect(getScoreColorOnDark(38)).toBe(scoreColors.red);
    expect(getScoreColorOnDark(54)).toBe(scoreColors.yellow);
  });
});
