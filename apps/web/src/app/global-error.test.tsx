import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import GlobalError from "@/src/app/global-error";

describe("GlobalError", () => {
  it("renders its own document with a retry and no internal details", () => {
    const html = renderToStaticMarkup(
      <GlobalError
        error={new Error("detalle interno del layout")}
        reset={() => undefined}
      />
    );

    expect(html).toContain('<html lang="es">');
    expect(html).toContain("Reintentar");
    expect(html).not.toContain("detalle interno");
  });
});
