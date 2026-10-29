import { afterEach, describe, expect, it, vi } from "vitest";

import {
  clearWizardProgress,
  completeWizard,
  getWizardProgress,
  hasWizardProgress,
  saveWizardProgress,
  WIZARD_PROGRESS_KEY
} from "@/lib/wizard/progress";

const skill = { id: "s1", name: "Python", category: null, level: null, source: "cv" };

function stubBrowserStorage(initial: Record<string, string> = {}) {
  const values = new Map(Object.entries(initial));
  const localStorage = {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => void values.set(key, value),
    removeItem: (key: string) => void values.delete(key)
  };
  vi.stubGlobal("window", { localStorage });
  return values;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("wizard progress belongs to one account", () => {
  it("lets the same account resume where it left", () => {
    stubBrowserStorage();
    saveWizardProgress("maria", { currentStep: 3, parsedSkills: [skill] });

    const resumed = getWizardProgress("maria");

    expect(resumed.currentStep).toBe(3);
    expect(resumed.parsedSkills).toEqual([skill]);
    expect(hasWizardProgress("maria")).toBe(true);
  });

  it("never shows the progress of one account to another and discards it", () => {
    const values = stubBrowserStorage();
    saveWizardProgress("maria", { currentStep: 3, parsedSkills: [skill] });

    const seenByJuan = getWizardProgress("juan");

    expect(seenByJuan).toEqual({ currentStep: 1, completed: false });
    // No queda en el navegador esperando a que alguien más lo lea.
    expect(values.has(WIZARD_PROGRESS_KEY)).toBe(false);
  });

  it("tells the guard there is progress only for its owner", () => {
    const values = stubBrowserStorage();
    saveWizardProgress("maria", { currentStep: 2 });

    expect(hasWizardProgress("juan")).toBe(false);
    expect(values.has(WIZARD_PROGRESS_KEY)).toBe(false);
  });

  it("discards progress saved before progress had an owner", () => {
    const values = stubBrowserStorage({
      [WIZARD_PROGRESS_KEY]: JSON.stringify({
        currentStep: 3,
        completed: false,
        parsedSkills: [skill]
      })
    });

    expect(getWizardProgress("maria")).toEqual({ currentStep: 1, completed: false });
    expect(values.has(WIZARD_PROGRESS_KEY)).toBe(false);
  });

  it("starts from scratch when another account saves, without the previous data", () => {
    const values = stubBrowserStorage();
    saveWizardProgress("maria", { currentStep: 3, parsedSkills: [skill] });

    saveWizardProgress("juan", { currentStep: 2 });

    const stored = JSON.parse(values.get(WIZARD_PROGRESS_KEY) ?? "{}");
    expect(stored.ownerId).toBe("juan");
    expect(stored.currentStep).toBe(2);
    expect(stored.parsedSkills).toBeUndefined();
  });

  it("keeps and shows nothing while the account is unknown", () => {
    const values = stubBrowserStorage();
    saveWizardProgress("maria", { currentStep: 3 });

    expect(getWizardProgress(null)).toEqual({ currentStep: 1, completed: false });
    expect(hasWizardProgress(null)).toBe(false);
    saveWizardProgress(null, { currentStep: 4 });
    // Sin saber de quién es no se borra lo de nadie ni se guarda algo sin dueño.
    expect(JSON.parse(values.get(WIZARD_PROGRESS_KEY) ?? "{}").currentStep).toBe(3);
  });

  it("ignores corrupt data", () => {
    stubBrowserStorage({ [WIZARD_PROGRESS_KEY]: "{no es json" });

    expect(getWizardProgress("maria")).toEqual({ currentStep: 1, completed: false });
    expect(hasWizardProgress("maria")).toBe(false);
  });

  it("marks the onboarding as completed for its owner only", () => {
    stubBrowserStorage();
    completeWizard("maria");

    expect(getWizardProgress("maria")).toMatchObject({ currentStep: 4, completed: true });
    expect(getWizardProgress("juan").completed).toBe(false);
  });
});

describe("clearWizardProgress", () => {
  it("removes the saved progress so the next account starts from step 1", () => {
    const values = stubBrowserStorage();
    saveWizardProgress("maria", { currentStep: 3, parsedSkills: [skill] });
    expect(values.has(WIZARD_PROGRESS_KEY)).toBe(true);

    clearWizardProgress();

    expect(values.has(WIZARD_PROGRESS_KEY)).toBe(false);
    expect(getWizardProgress("maria")).toEqual({ currentStep: 1, completed: false });
  });

  it("does nothing outside the browser", () => {
    expect(() => clearWizardProgress()).not.toThrow();
  });

  it("does not fail when the browser blocks the storage", () => {
    vi.stubGlobal("window", {
      localStorage: {
        removeItem: () => {
          throw new Error("storage bloqueado");
        }
      }
    });

    expect(() => clearWizardProgress()).not.toThrow();
  });
});
