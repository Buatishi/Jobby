import { describe, expect, it } from "vitest";

import {
  describeDocuments,
  formatDocumentDate,
  getNotices
} from "@/lib/reality-gap/notices";
import type { RealityGapDocument } from "@/lib/reality-gap/types";

const document = (
  overrides: Partial<RealityGapDocument> = {}
): RealityGapDocument => ({
  filename: "cv.pdf",
  uploaded_at: "2026-11-02T14:55:20+00:00",
  status: "done",
  skills_source: "document",
  ...overrides
});

describe("getNotices", () => {
  it("has nothing to say when both documents were read with their own lists", () => {
    expect(getNotices({ cv: document(), linkedin: document() })).toEqual([]);
  });

  it("asks for the CV when there is none", () => {
    const [notice] = getNotices({ cv: null, linkedin: document() });

    expect(notice.id).toBe("cv-missing");
    expect(notice.href).toBe("/profile");
    expect(notice.actionLabel).toBe("Subir CV");
  });

  it("asks for the LinkedIn PDF and says why it matters", () => {
    const notices = getNotices({ cv: document(), linkedin: null });

    expect(notices.map((notice) => notice.id)).toEqual(["linkedin-missing"]);
    expect(notices[0].text).toContain("sin él no podemos comparar");
    expect(notices[0].href).toBe("/profile");
  });

  it("lists the CV before LinkedIn when both are missing", () => {
    const ids = getNotices({ cv: null, linkedin: null }).map((n) => n.id);

    expect(ids).toEqual(["cv-missing", "linkedin-missing"]);
  });

  it.each(["pending", "processing"])(
    "tells the person to wait while the CV is %s, with no action",
    (status) => {
      const [notice] = getNotices({
        cv: document({ status, skills_source: null }),
        linkedin: document()
      });

      expect(notice.id).toBe("cv-reading");
      expect(notice.href).toBeUndefined();
    }
  );

  it("tells the person to upload again when a document could not be read", () => {
    const notices = getNotices({
      cv: document({ status: "failed", skills_source: null }),
      linkedin: document({ status: "failed", skills_source: null })
    });

    expect(notices.map((notice) => notice.id)).toEqual([
      "cv-failed",
      "linkedin-failed"
    ]);
    expect(notices.every((notice) => notice.href === "/profile")).toBe(true);
  });

  it("warns about a CV read before it kept its own list of skills", () => {
    const notices = getNotices({
      cv: document({ skills_source: "saved" }),
      linkedin: document()
    });

    expect(notices.map((notice) => notice.id)).toEqual(["cv-saved-marks"]);
  });

  it("does not warn about the saved marks of a CV that was not read", () => {
    const notices = getNotices({
      cv: document({ status: "failed", skills_source: "saved" }),
      linkedin: document()
    });

    expect(notices.map((notice) => notice.id)).toEqual(["cv-failed"]);
  });
});

describe("formatDocumentDate", () => {
  it("writes the day and the month in Spanish", () => {
    const text = formatDocumentDate("2026-11-02T14:55:20+00:00", "UTC");

    expect(text).toContain("2");
    expect(text?.toLowerCase()).toContain("nov");
  });

  it.each([null, "", "no es una fecha"])("returns null for %j", (value) => {
    expect(formatDocumentDate(value)).toBeNull();
  });
});

describe("describeDocuments", () => {
  it("names both files and their dates", () => {
    const text = describeDocuments(
      {
        cv: document(),
        linkedin: document({
          filename: "Profile.pdf",
          uploaded_at: "2026-10-31T22:50:32+00:00"
        })
      },
      "UTC"
    );

    expect(text).toContain("«cv.pdf»");
    expect(text).toContain("«Profile.pdf»");
    expect(text).toContain("volvé a subir el archivo");
  });

  it("copes with a missing file name or date", () => {
    const text = describeDocuments({
      cv: document({ filename: null, uploaded_at: null }),
      linkedin: document({ filename: null, uploaded_at: null })
    });

    expect(text).toBe(
      "Comparado con tu CV y el PDF de tu LinkedIn. Si cambiaste algo, volvé a subir el archivo."
    );
  });

  it("says nothing when a document is missing or was not read", () => {
    expect(describeDocuments({ cv: null, linkedin: document() })).toBeNull();
    expect(
      describeDocuments({ cv: document(), linkedin: document({ status: "failed" }) })
    ).toBeNull();
  });
});
