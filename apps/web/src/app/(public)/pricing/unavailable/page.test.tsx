import { describe, expect, it } from "vitest";

import { metadata } from "@/src/app/(public)/pricing/unavailable/page";

describe("checkout unavailable page", () => {
  it("is not meant to be found by search engines", () => {
    expect(metadata.robots).toEqual({ index: false, follow: false });
  });
});
