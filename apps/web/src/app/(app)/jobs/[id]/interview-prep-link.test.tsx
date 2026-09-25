import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { InterviewPrepLink } from "@/src/app/(app)/jobs/[id]/interview-prep-link";

describe("InterviewPrepLink", () => {
  it("takes premium users to the interview kit form", () => {
    const html = renderToStaticMarkup(<InterviewPrepLink plan="premium" />);

    expect(html).toContain('href="/interview-kits/new"');
    expect(html).toContain("Preparar entrevista para este puesto");
  });

  it("is not offered on the free plan or while the plan loads", () => {
    expect(renderToStaticMarkup(<InterviewPrepLink plan="free" />)).toBe("");
    expect(renderToStaticMarkup(<InterviewPrepLink plan={null} />)).toBe("");
  });
});
