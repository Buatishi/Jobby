import { describe, expect, it } from "vitest";

import { GET } from "./route";

const PNG_SIGNATURE = [0x89, 0x50, 0x4e, 0x47];

describe("og-image route", () => {
  it("renders a complete PNG", async () => {
    // Satori exige display flex en todo <div> cuyo contenido no sea solo texto. Sin eso
    // la respuesta salía con 200 pero vacía y las vistas previas de los links no tenían imagen.
    const response = GET();
    const body = new Uint8Array(await response.arrayBuffer());

    expect(response.headers.get("content-type")).toBe("image/png");
    expect(Array.from(body.slice(0, 4))).toEqual(PNG_SIGNATURE);
    expect(body.byteLength).toBeGreaterThan(10_000);
  });
});
