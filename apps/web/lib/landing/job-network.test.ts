import { describe, expect, it } from "vitest";

import {
  NETWORK_CENTER,
  NETWORK_VIEWBOX,
  arcPath,
  networkNodes,
  ringDash
} from "@/lib/landing/job-network";

describe("job network", () => {
  it("keeps every node inside the viewbox", () => {
    for (const node of networkNodes) {
      expect(node.x).toBeGreaterThan(0);
      expect(node.x).toBeLessThan(NETWORK_VIEWBOX.width);
      expect(node.y).toBeGreaterThan(0);
      expect(node.y).toBeLessThan(NETWORK_CENTER.y);
    }
  });

  it("uses scores between 0 and 100", () => {
    for (const node of networkNodes) {
      expect(node.score).toBeGreaterThanOrEqual(0);
      expect(node.score).toBeLessThanOrEqual(100);
    }
  });

  it("draws each arc from the CV to its job", () => {
    const [node] = networkNodes;
    const path = arcPath(node);

    expect(path.startsWith(`M${NETWORK_CENTER.x} ${NETWORK_CENTER.y - 38}`)).toBe(true);
    expect(path.endsWith(`${node.x} ${node.y + 38}`)).toBe(true);
  });
});

describe("ringDash", () => {
  it("fills half the circumference at 50", () => {
    const [filled, total] = ringDash(50).split(" ").map(Number);

    expect(filled).toBeCloseTo(total / 2, 0);
  });

  it("clamps scores out of range", () => {
    const [none] = ringDash(-10).split(" ").map(Number);
    const [all, total] = ringDash(140).split(" ").map(Number);

    expect(none).toBe(0);
    expect(all).toBe(total);
  });
});
