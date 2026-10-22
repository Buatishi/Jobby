import { describe, expect, it, vi } from "vitest";

import {
  MAX_PDF_BYTES,
  registerPdf,
  validatePdf,
  type UploadDeps
} from "@/lib/documents/upload";

function pdf(name = "CV.pdf", size = 2048): File {
  return new File([new Uint8Array(size)], name, { type: "application/pdf" });
}

function makeDeps(overrides: Partial<UploadDeps> = {}): UploadDeps {
  return {
    userId: vi.fn(async () => "auth-user-1"),
    uploadFile: vi.fn(async () => undefined),
    registerDocument: vi.fn(async () => ({ id: "doc-1", task_id: "task-1" })),
    waitForTask: vi.fn(async () => ({ status: "done" })),
    newId: () => "uuid-1",
    ...overrides
  };
}

describe("validatePdf", () => {
  it("accepts a normal PDF", () => {
    expect(validatePdf({ type: "application/pdf", size: 120_000 })).toBeNull();
  });

  it("rejects what is not a PDF, empty files and files over 10MB", () => {
    expect(validatePdf({ type: "image/png", size: 100 })).toMatch(/PDF/);
    expect(validatePdf({ type: "application/pdf", size: 0 })).toMatch(/vacío/);
    expect(
      validatePdf({ type: "application/pdf", size: MAX_PDF_BYTES + 1 })
    ).toMatch(/10MB/);
  });
});

describe("registerPdf", () => {
  it("stores the file in the person's folder and registers it with the given fields", async () => {
    const deps = makeDeps();

    const { document, taskId } = await registerPdf(pdf("CV.pdf", 2048), deps, {
      profile_id: "profile-1",
      type: "cv"
    });

    expect(deps.uploadFile).toHaveBeenCalledWith(
      "auth-user-1/uuid-1-CV.pdf",
      expect.any(File)
    );
    expect(deps.registerDocument).toHaveBeenCalledWith({
      profile_id: "profile-1",
      type: "cv",
      storage_path: "auth-user-1/uuid-1-CV.pdf",
      original_filename: "CV.pdf",
      mime_type: "application/pdf",
      file_size: 2048
    });
    expect(document.id).toBe("doc-1");
    expect(taskId).toBe("task-1");
  });

  it("reports the stages in order", async () => {
    const stages: string[] = [];

    await registerPdf(pdf(), makeDeps(), { type: "cv" }, (stage) => stages.push(stage));

    expect(stages).toEqual(["uploading", "registering"]);
  });

  it("does not upload anything when the file is not valid", async () => {
    const deps = makeDeps();
    const notPdf = new File(["x"], "foto.png", { type: "image/png" });

    await expect(registerPdf(notPdf, deps, { type: "cv" })).rejects.toThrow(/PDF/);

    expect(deps.uploadFile).not.toHaveBeenCalled();
    expect(deps.registerDocument).not.toHaveBeenCalled();
  });

  it("does not register a file that failed to upload", async () => {
    const deps = makeDeps({
      uploadFile: vi.fn(async () => {
        throw new Error("Storage caído");
      })
    });

    await expect(registerPdf(pdf(), deps, { type: "cv" })).rejects.toThrow("Storage caído");
    expect(deps.registerDocument).not.toHaveBeenCalled();
  });

  it("fails when the server does not return the reading task", async () => {
    const deps = makeDeps({ registerDocument: vi.fn(async () => ({ id: "doc-1" })) });

    await expect(registerPdf(pdf(), deps, { type: "cv" })).rejects.toThrow(
      /tarea de lectura/
    );
  });
});
