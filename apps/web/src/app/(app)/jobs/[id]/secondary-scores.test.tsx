import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { dictionaries } from "@/lib/i18n/dictionaries";
import { I18nProvider } from "@/lib/i18n/provider";
import { SecondaryScores } from "@/src/app/(app)/jobs/[id]/secondary-scores";

function render(potential: number | null, representation: number | null) {
  return renderToStaticMarkup(
    <I18nProvider>
      <SecondaryScores potential={potential} representation={representation} />
    </I18nProvider>
  );
}

describe("SecondaryScores", () => {
  it("keeps both labels and their values", () => {
    const html = render(72, 100);

    expect(html).toContain("Potential Score");
    expect(html).toContain("<strong>72</strong>");
    expect(html).toContain("Representation Score");
    expect(html).toContain("<strong>100</strong>");
  });

  it("explains that the potential is the score with the skills component at 100", () => {
    expect(render(72, 100)).toContain("Tu puntaje si el componente de skills fuera 100");
  });

  it("explains that the representation is about the CV, not the fit with the job", () => {
    const html = render(72, 100);

    expect(html).toContain("Porcentaje de tus skills confirmadas que figuran en tu CV");
    expect(html).toContain("No mide el encaje con el puesto");
  });

  it("has the same explanations in English", () => {
    const en = dictionaries.en.app as Record<string, string>;

    expect(en.potentialScoreHint).toContain("skills component were 100");
    expect(en.representationScoreHint).toContain("appear in your CV");
    expect(en.representationScoreHint).toContain("does not measure fit with the job");
  });

  it("falls back to zero when the report has no value yet", () => {
    const html = render(null, null);

    expect(html.match(/<strong>0<\/strong>/g)).toHaveLength(2);
  });
});
