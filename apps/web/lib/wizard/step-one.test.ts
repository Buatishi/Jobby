import { describe, expect, it } from "vitest";

import {
  mergeLoadedValues,
  resolveStepOneValues,
  STEP_ONE_DEFAULTS,
  type StepOneField
} from "@/lib/wizard/step-one";

const profile = {
  id: "profile-1",
  headline: "Full Stack Developer",
  summary: "Automatizo flujos de trabajo con Python.",
  target_role: "Tech engineering",
  target_seniority: "junior",
  work_modality: "hybrid"
};

describe("resolveStepOneValues", () => {
  it("opens with everything the profile already has", () => {
    const { values, prefilled } = resolveStepOneValues(profile, undefined);

    expect(values).toEqual({
      headline: "Full Stack Developer",
      summary: "Automatizo flujos de trabajo con Python.",
      targetRole: "Tech engineering",
      targetSeniority: "junior",
      workModality: "hybrid"
    });
    expect(prefilled).toBe(true);
  });

  it("keeps the saved profile over an autosaved draft of the same profile", () => {
    // El borrador se autoguarda con los valores por defecto aunque nadie los toque.
    const { values } = resolveStepOneValues(profile, {
      profileId: "profile-1",
      headline: "",
      summary: "",
      targetRole: "",
      targetSeniority: "mid",
      workModality: "remote"
    });

    expect(values.headline).toBe("Full Stack Developer");
    expect(values.targetSeniority).toBe("junior");
    expect(values.workModality).toBe("hybrid");
  });

  it("uses the draft of the same profile only for what the profile lacks", () => {
    const { values, prefilled } = resolveStepOneValues(
      { id: "profile-1", headline: "Chef", summary: null, target_role: "" },
      {
        profileId: "profile-1",
        headline: "Otro titular",
        summary: "Cocino para eventos.",
        targetRole: "Jefe de cocina",
        targetSeniority: "senior",
        workModality: "onsite"
      }
    );

    expect(values).toEqual({
      headline: "Chef",
      summary: "Cocino para eventos.",
      targetRole: "Jefe de cocina",
      targetSeniority: "senior",
      workModality: "onsite"
    });
    expect(prefilled).toBe(true);
  });

  it("ignores a draft that belongs to another account", () => {
    const { values, prefilled } = resolveStepOneValues(
      { id: "profile-2", headline: null, summary: null },
      {
        profileId: "profile-1",
        headline: "Titular de otra cuenta",
        summary: "Bio de otra cuenta",
        targetRole: "Rol de otra cuenta",
        targetSeniority: "senior",
        workModality: "onsite"
      }
    );

    expect(values).toEqual({
      headline: "",
      summary: "",
      targetRole: "",
      targetSeniority: "mid",
      workModality: "remote"
    });
    expect(prefilled).toBe(false);
  });

  it("ignores a draft saved before drafts carried the profile", () => {
    const { values } = resolveStepOneValues(
      { id: "profile-1" },
      { headline: "Borrador viejo", summary: "Sin dueño conocido" }
    );

    expect(values.headline).toBe("");
    expect(values.summary).toBe("");
  });

  it("falls back to the draft when the profile could not be loaded", () => {
    const { values, prefilled } = resolveStepOneValues(null, {
      headline: "Del borrador",
      targetSeniority: "senior"
    });

    expect(values.headline).toBe("Del borrador");
    expect(values.targetSeniority).toBe("senior");
    expect(prefilled).toBe(false);
  });

  it("starts empty with the defaults for a brand new profile", () => {
    const { values, prefilled } = resolveStepOneValues({ id: "profile-1" }, undefined);

    expect(values).toEqual({
      headline: "",
      summary: "",
      targetRole: "",
      targetSeniority: "mid",
      workModality: "remote"
    });
    expect(prefilled).toBe(false);
  });

  it("accepts the seniority and modality the form offers, ignoring case", () => {
    const { values } = resolveStepOneValues(
      { id: "profile-1", target_seniority: " Senior ", work_modality: "Hybrid" },
      undefined
    );

    expect(values.targetSeniority).toBe("senior");
    expect(values.workModality).toBe("hybrid");
  });

  it("does not put in the form a seniority or modality it has no option for", () => {
    const { values } = resolveStepOneValues(
      { id: "profile-1", target_seniority: "semi senior", work_modality: "remoto" },
      undefined
    );

    expect(values.targetSeniority).toBe("mid");
    expect(values.workModality).toBe("remote");
  });

  it("treats a whitespace-only text as missing", () => {
    const { values, prefilled } = resolveStepOneValues(
      { id: "profile-1", headline: "   ", summary: "\n" },
      undefined
    );

    expect(values.headline).toBe("");
    expect(values.summary).toBe("");
    expect(prefilled).toBe(false);
  });
});

describe("mergeLoadedValues", () => {
  const loaded = {
    headline: "Full Stack Developer",
    summary: "Automatizo flujos de trabajo con Python.",
    targetRole: "Tech engineering",
    targetSeniority: "junior",
    workModality: "hybrid"
  };

  it("takes everything from the profile when the person has not typed yet", () => {
    const merged = mergeLoadedValues(STEP_ONE_DEFAULTS, new Set(), loaded);

    expect(merged).toEqual(loaded);
  });

  it("keeps what the person already typed while the profile was loading", () => {
    const typed = { ...STEP_ONE_DEFAULTS, headline: "Mi titular nuevo" };
    const touched = new Set<StepOneField>(["headline"]);

    const merged = mergeLoadedValues(typed, touched, loaded);

    expect(merged.headline).toBe("Mi titular nuevo");
    expect(merged.summary).toBe(loaded.summary);
    expect(merged.targetSeniority).toBe("junior");
  });

  it("keeps a field the person emptied on purpose", () => {
    const emptied = { ...loaded, summary: "" };
    const touched = new Set<StepOneField>(["summary"]);

    expect(mergeLoadedValues(emptied, touched, loaded).summary).toBe("");
  });

  it("changes nothing when every field was typed", () => {
    const typed = {
      headline: "A",
      summary: "B",
      targetRole: "C",
      targetSeniority: "senior",
      workModality: "onsite"
    };
    const touched = new Set<StepOneField>([
      "headline",
      "summary",
      "targetRole",
      "targetSeniority",
      "workModality"
    ]);

    expect(mergeLoadedValues(typed, touched, loaded)).toEqual(typed);
  });
});
