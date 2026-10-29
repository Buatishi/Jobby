import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it, vi } from "vitest";

// `next/og` solo se usa al generar la imagen: acá se importa para leer `size`.
vi.mock("next/og", () => ({ ImageResponse: class {} }));

import { size } from "@/src/app/icon";

// Google recomienda un favicon cuadrado de más de 48 px.
const GOOGLE_MIN_SIDE = 48;

function readFavicon() {
  return readFileSync(fileURLToPath(new URL("./favicon.ico", import.meta.url)));
}

// Cada entrada del directorio ICO guarda ancho y alto en un byte: 0 significa 256.
function iconSizes(file: Buffer) {
  const count = file.readUInt16LE(4);
  return Array.from({ length: count }, (_, index) => {
    const entry = 6 + index * 16;
    return { width: file[entry] || 256, height: file[entry + 1] || 256 };
  });
}

describe("favicon", () => {
  it("serves a real ICO file at /favicon.ico", () => {
    const file = readFavicon();

    expect(file.readUInt16LE(0)).toBe(0);
    expect(file.readUInt16LE(2)).toBe(1);
    expect(file.readUInt16LE(4)).toBeGreaterThan(0);
  });

  it("holds square images from tab size up to more than 48 px", () => {
    const sizes = iconSizes(readFavicon());

    for (const { width, height } of sizes) {
      expect(width).toBe(height);
    }
    expect(Math.min(...sizes.map(({ width }) => width))).toBeLessThanOrEqual(16);
    expect(Math.max(...sizes.map(({ width }) => width))).toBeGreaterThan(
      GOOGLE_MIN_SIDE
    );
  });

  it("lists the biggest image first, because Next copies that size into <link sizes>", () => {
    const sizes = iconSizes(readFavicon()).map(({ width }) => width);

    expect(sizes[0]).toBe(Math.max(...sizes));
  });

  it("generates the declared icon larger than 48 px and square", () => {
    expect(size.width).toBe(size.height);
    expect(size.width).toBeGreaterThan(GOOGLE_MIN_SIDE);
  });
});
