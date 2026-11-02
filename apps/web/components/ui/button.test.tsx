import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { Button, buttonVariants } from "@/components/ui/button";

describe("buttonVariants", () => {
  it("animates only the properties a button changes, never `all`", () => {
    const classes = buttonVariants();

    expect(classes).not.toContain("transition-all");
    expect(classes).toContain(
      "transition-[color,background-color,border-color,opacity,box-shadow,transform]"
    );
  });
});

describe("Button", () => {
  it("stops the loading spinner when the user prefers reduced motion", () => {
    const html = renderToStaticMarkup(<Button isLoading>Guardar</Button>);

    expect(html).toContain("animate-spin");
    expect(html).toContain("motion-reduce:animate-none");
  });

  it("shows no spinner when it is not loading", () => {
    const html = renderToStaticMarkup(<Button>Guardar</Button>);

    expect(html).not.toContain("animate-spin");
  });
});
