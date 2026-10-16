import { describe, expect, it, vi } from "vitest";

import {
  describeLinkedInDocument,
  LINKEDIN_URL_ERROR,
  MAX_LINKEDIN_PDF_BYTES,
  parseLinkedInProfileUrl,
  uploadLinkedInPdf,
  validateLinkedInPdf,
  type LinkedInUploadDeps
} from "@/lib/linkedin/linkedin";

describe("parseLinkedInProfileUrl", () => {
  it.each([
    ["https://www.linkedin.com/in/juan-perez", "https://www.linkedin.com/in/juan-perez"],
    ["https://linkedin.com/in/juan-perez/", "https://linkedin.com/in/juan-perez/"],
    ["http://ar.linkedin.com/in/juan-perez", "http://ar.linkedin.com/in/juan-perez"],
    ["  https://www.linkedin.com/in/juan-perez  ", "https://www.linkedin.com/in/juan-perez"]
  ])("accepts %s", (input, expected) => {
    expect(parseLinkedInProfileUrl(input)).toEqual({ ok: true, value: expected });
  });

  it("adds https when the person pastes it without a scheme", () => {
    expect(parseLinkedInProfileUrl("linkedin.com/in/juan-perez")).toEqual({
      ok: true,
      value: "https://linkedin.com/in/juan-perez"
    });
    expect(parseLinkedInProfileUrl("www.linkedin.com/in/juan-perez")).toEqual({
      ok: true,
      value: "https://www.linkedin.com/in/juan-perez"
    });
  });

  it("treats an empty field as clearing the link", () => {
    expect(parseLinkedInProfileUrl("")).toEqual({ ok: true, value: null });
    expect(parseLinkedInProfileUrl("   ")).toEqual({ ok: true, value: null });
  });

  it.each([
    "asdf",
    "https://example.com/in/juan-perez",
    "https://notlinkedin.com/in/juan-perez",
    "https://linkedin.com.evil.com/in/juan-perez",
    "https://www.linkedin.com/company/acme",
    "https://www.linkedin.com/in/",
    "https://www.linkedin.com/in/ab",
    "https://www.linkedin.com/feed/",
    "ftp://www.linkedin.com/in/juan-perez",
    "javascript:alert(1)"
  ])("rejects %s", (input) => {
    expect(parseLinkedInProfileUrl(input)).toEqual({
      ok: false,
      error: LINKEDIN_URL_ERROR
    });
  });

  it("rejects an address longer than the API accepts", () => {
    const long = `https://www.linkedin.com/in/${"a".repeat(2100)}`;

    expect(parseLinkedInProfileUrl(long).ok).toBe(false);
  });
});

describe("validateLinkedInPdf", () => {
  it("accepts a normal PDF", () => {
    expect(validateLinkedInPdf({ type: "application/pdf", size: 120_000 })).toBeNull();
  });

  it("rejects what is not a PDF, empty files and files over 10MB", () => {
    expect(validateLinkedInPdf({ type: "image/png", size: 100 })).toMatch(/PDF/);
    expect(validateLinkedInPdf({ type: "application/pdf", size: 0 })).toMatch(/vacío/);
    expect(
      validateLinkedInPdf({
        type: "application/pdf",
        size: MAX_LINKEDIN_PDF_BYTES + 1
      })
    ).toMatch(/10MB/);
  });
});

describe("describeLinkedInDocument", () => {
  const profile = { profile_id: "p1" };

  it("invites to upload when there is no document", () => {
    expect(describeLinkedInDocument(undefined).tone).toBe("empty");
    expect(describeLinkedInDocument({ ...profile, document: null }).tone).toBe("empty");
  });

  it("says it is working while the PDF is pending or being read", () => {
    for (const status of ["pending", "processing"]) {
      expect(
        describeLinkedInDocument({ ...profile, document: { id: "d", status } }).tone
      ).toBe("working");
    }
  });

  it("shows how many saved skills the PDF named", () => {
    const summary = describeLinkedInDocument({
      ...profile,
      document: { id: "d", status: "done" },
      skills_in_linkedin: 7
    });

    expect(summary.tone).toBe("done");
    expect(summary.text).toContain("7");
  });

  it("explains a read that matched nothing", () => {
    const summary = describeLinkedInDocument({
      ...profile,
      document: { id: "d", status: "done" },
      skills_in_linkedin: 0
    });

    expect(summary.tone).toBe("done");
    expect(summary.text).toMatch(/ninguna skill/);
  });

  it("shows the error the reader left, or a generic one", () => {
    expect(
      describeLinkedInDocument({
        ...profile,
        document: { id: "d", status: "failed", error_msg: "El PDF no tiene texto." }
      })
    ).toEqual({ tone: "failed", text: "El PDF no tiene texto." });
    expect(
      describeLinkedInDocument({ ...profile, document: { id: "d", status: "failed" } })
        .text
    ).toMatch(/Probá subirlo/);
  });
});

describe("uploadLinkedInPdf", () => {
  function pdf(name = "Profile.pdf", size = 2048): File {
    return new File([new Uint8Array(size)], name, { type: "application/pdf" });
  }

  function makeDeps(overrides: Partial<LinkedInUploadDeps> = {}) {
    const deps: LinkedInUploadDeps = {
      userId: vi.fn(async () => "auth-user-1"),
      uploadFile: vi.fn(async () => undefined),
      registerDocument: vi.fn(async () => ({ task_id: "task-1" })),
      waitForTask: vi.fn(async () => ({ status: "done" })),
      newId: () => "uuid-1",
      ...overrides
    };
    return deps;
  }

  it("stores the file in the person's folder and registers it as linkedin", async () => {
    const deps = makeDeps();

    await uploadLinkedInPdf(pdf("Profile.pdf", 2048), "profile-1", deps);

    expect(deps.uploadFile).toHaveBeenCalledWith(
      "auth-user-1/uuid-1-Profile.pdf",
      expect.any(File)
    );
    expect(deps.registerDocument).toHaveBeenCalledWith({
      profile_id: "profile-1",
      type: "linkedin",
      is_primary: false,
      storage_path: "auth-user-1/uuid-1-Profile.pdf",
      original_filename: "Profile.pdf",
      mime_type: "application/pdf",
      file_size: 2048
    });
    expect(deps.waitForTask).toHaveBeenCalledWith("task-1");
  });

  it("never claims a CV slot or the primary CV", async () => {
    const deps = makeDeps();

    await uploadLinkedInPdf(pdf(), "profile-1", deps);

    const body = vi.mocked(deps.registerDocument).mock.calls[0]?.[0] ?? {};
    expect(body).not.toHaveProperty("cv_slot");
    expect(body.is_primary).toBe(false);
  });

  it("does not upload anything when the file is not valid", async () => {
    const deps = makeDeps();
    const notPdf = new File(["x"], "foto.png", { type: "image/png" });

    await expect(uploadLinkedInPdf(notPdf, "profile-1", deps)).rejects.toThrow(/PDF/);

    expect(deps.uploadFile).not.toHaveBeenCalled();
    expect(deps.registerDocument).not.toHaveBeenCalled();
  });

  it("fails when the server does not return the reading task", async () => {
    const deps = makeDeps({ registerDocument: vi.fn(async () => ({})) });

    await expect(uploadLinkedInPdf(pdf(), "profile-1", deps)).rejects.toThrow(
      /tarea de lectura/
    );
    expect(deps.waitForTask).not.toHaveBeenCalled();
  });

  it("fails with the reader's message when the task failed", async () => {
    const deps = makeDeps({
      waitForTask: vi.fn(async () => ({ status: "failed", error: "Sin texto legible." }))
    });

    await expect(uploadLinkedInPdf(pdf(), "profile-1", deps)).rejects.toThrow(
      "Sin texto legible."
    );
  });

  it("does not fail when the stream ends before saying done", async () => {
    // La tarjeta vuelve a pedir el estado y muestra «leyendo» o el resultado.
    const deps = makeDeps({ waitForTask: vi.fn(async () => ({ status: "pending" })) });

    await expect(uploadLinkedInPdf(pdf(), "profile-1", deps)).resolves.toBeUndefined();
  });
});
