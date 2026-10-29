import { afterEach, describe, expect, it, vi } from "vitest";

import {
  clearWizardProgress,
  getWizardProgress,
  saveWizardProgress,
  WIZARD_PROGRESS_KEY
} from "@/lib/wizard/progress";

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

describe("clearWizardProgress", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("removes the saved progress so the next account starts from step 1", () => {
    const values = stubBrowserStorage();
    saveWizardProgress({
      currentStep: 3,
      parsedSkills: [
        { id: "s1", name: "Python", category: null, level: null, source: "cv" }
      ]
    });
    expect(values.has(WIZARD_PROGRESS_KEY)).toBe(true);

    clearWizardProgress();

    expect(values.has(WIZARD_PROGRESS_KEY)).toBe(false);
    expect(getWizardProgress()).toEqual({ currentStep: 1, completed: false });
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
