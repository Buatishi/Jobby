import { describe, expect, it, vi } from "vitest";

import {
  formatCvDate,
  PRIMARY_CV_SLOT,
  toSkillDrafts,
  uploadPrimaryCv
} from "@/lib/cv/upload";
import type { UploadDeps } from "@/lib/documents/upload";

function pdf(name = "CV Bautista.pdf", size = 2048): File {
  return new File([new Uint8Array(size)], name, { type: "application/pdf" });
}

function makeDeps(overrides: Partial<UploadDeps> = {}): UploadDeps {
  return {
    userId: vi.fn(async () => "auth-user-1"),
    uploadFile: vi.fn(async () => undefined),
    registerDocument: vi.fn(async () => ({
      id: "doc-1",
      task_id: "task-1",
      original_filename: "CV Bautista.pdf",
      created_at: "2026-10-21T15:00:00+00:00"
    })),
    waitForTask: vi.fn(async () => ({
      status: "done",
      result: { skills: [{ name: "Python", category: "technical", level: null }] }
    })),
    newId: () => "uuid-1",
    ...overrides
  };
}

describe("uploadPrimaryCv", () => {
  it("registers the file as the primary CV in slot 1, never as a LinkedIn PDF", async () => {
    const deps = makeDeps();

    await uploadPrimaryCv(pdf(), "profile-1", deps);

    expect(PRIMARY_CV_SLOT).toBe(1);
    expect(deps.registerDocument).toHaveBeenCalledWith({
      profile_id: "profile-1",
      type: "cv",
      cv_slot: 1,
      is_primary: true,
      storage_path: "auth-user-1/uuid-1-CV Bautista.pdf",
      original_filename: "CV Bautista.pdf",
      mime_type: "application/pdf",
      file_size: 2048
    });
    expect(deps.waitForTask).toHaveBeenCalledWith("task-1", undefined);
  });

  it("returns the document the server saved and what the reader found", async () => {
    const uploaded = await uploadPrimaryCv(pdf(), "profile-1", makeDeps());

    expect(uploaded).toEqual({
      documentId: "doc-1",
      taskId: "task-1",
      filename: "CV Bautista.pdf",
      uploadedAt: "2026-10-21T15:00:00+00:00",
      status: "done",
      result: { skills: [{ name: "Python", category: "technical", level: null }] }
    });
  });

  it("falls back to the picked file's name when the server does not echo it", async () => {
    const deps = makeDeps({
      registerDocument: vi.fn(async () => ({ id: "doc-1", task_id: "task-1" }))
    });

    const uploaded = await uploadPrimaryCv(pdf("Otro.pdf"), "profile-1", deps);

    expect(uploaded.filename).toBe("Otro.pdf");
    expect(uploaded.uploadedAt).toBeNull();
  });

  it("reports upload, registration and reading in that order", async () => {
    const stages: string[] = [];

    await uploadPrimaryCv(pdf(), "profile-1", makeDeps(), {
      onStage: (stage) => stages.push(stage)
    });

    expect(stages).toEqual(["uploading", "registering", "reading"]);
  });

  it("tells the caller as soon as the document is registered, before the reading ends", async () => {
    const events: string[] = [];
    const deps = makeDeps({
      waitForTask: vi.fn(async () => {
        events.push("waiting");
        return { status: "done" };
      })
    });

    await uploadPrimaryCv(pdf(), "profile-1", deps, {
      onRegistered: ({ documentId, taskId }) => events.push(`registered ${documentId} ${taskId}`)
    });

    expect(events).toEqual(["registered doc-1 task-1", "waiting"]);
  });

  it("passes the reader's progress to the caller", async () => {
    const seen: string[] = [];
    const deps = makeDeps({
      waitForTask: vi.fn(async (_taskId, onUpdate) => {
        onUpdate?.({ status: "processing" });
        onUpdate?.({ status: "done" });
        return { status: "done" };
      })
    });

    await uploadPrimaryCv(pdf(), "profile-1", deps, {
      onTaskUpdate: (task) => seen.push(task.status)
    });

    expect(seen).toEqual(["processing", "done"]);
  });

  it("does not upload anything when the file is not a PDF", async () => {
    const deps = makeDeps();
    const notPdf = new File(["x"], "foto.png", { type: "image/png" });

    await expect(uploadPrimaryCv(notPdf, "profile-1", deps)).rejects.toThrow(/PDF/);

    expect(deps.uploadFile).not.toHaveBeenCalled();
    expect(deps.registerDocument).not.toHaveBeenCalled();
  });

  it("fails with the reader's message when the reading failed", async () => {
    const deps = makeDeps({
      waitForTask: vi.fn(async () => ({ status: "failed", error: "Sin texto legible." }))
    });

    await expect(uploadPrimaryCv(pdf(), "profile-1", deps)).rejects.toThrow(
      "Sin texto legible."
    );
  });

  it("fails with a generic message when the reader left none", async () => {
    const deps = makeDeps({ waitForTask: vi.fn(async () => ({ status: "failed" })) });

    await expect(uploadPrimaryCv(pdf(), "profile-1", deps)).rejects.toThrow(
      /No se pudo procesar el CV/
    );
  });

  it("does not fail when the stream ends before saying done", async () => {
    // El CV quedó registrado y se sigue leyendo: la tarjeta lo avisa, no es un error.
    const deps = makeDeps({
      waitForTask: vi.fn(async () => ({ status: "processing" }))
    });

    const uploaded = await uploadPrimaryCv(pdf(), "profile-1", deps);

    expect(uploaded.status).toBe("processing");
    expect(uploaded.result).toBeNull();
  });

  it("lets the API's daily-limit error through without touching anything else", async () => {
    const deps = makeDeps({
      registerDocument: vi.fn(async () => {
        throw new Error("Límite diario de cargas de documentos alcanzado");
      })
    });

    await expect(uploadPrimaryCv(pdf(), "profile-1", deps)).rejects.toThrow(
      /Límite diario/
    );
    expect(deps.waitForTask).not.toHaveBeenCalled();
  });
});

describe("toSkillDrafts", () => {
  it("turns what the reader found into unconfirmed drafts for the wizard", () => {
    expect(
      toSkillDrafts({
        skills: [{ name: "Python", category: "technical" }, { name: "SQL", level: "senior" }]
      })
    ).toEqual([
      {
        id: "Python-0",
        name: "Python",
        category: "technical",
        level: null,
        source: "CV",
        confirmed: false,
        rejected: false
      },
      {
        id: "SQL-1",
        name: "SQL",
        category: null,
        level: "senior",
        source: "CV",
        confirmed: false,
        rejected: false
      }
    ]);
  });

  it("returns nothing when there is no result", () => {
    expect(toSkillDrafts(null)).toEqual([]);
    expect(toSkillDrafts({})).toEqual([]);
  });
});

describe("formatCvDate", () => {
  it("formats the upload date in the person's language", () => {
    const es = formatCvDate("2026-10-21T15:00:00+00:00", "es");
    const en = formatCvDate("2026-10-21T15:00:00+00:00", "en");

    expect(es).toMatch(/2026/);
    expect(es.toLowerCase()).toMatch(/oct/);
    expect(en).toMatch(/2026/);
    expect(en.toLowerCase()).toMatch(/oct/);
    expect(es).not.toBe(en);
  });

  it("returns an empty text for a value that is not a date", () => {
    expect(formatCvDate("no es una fecha", "es")).toBe("");
  });
});
