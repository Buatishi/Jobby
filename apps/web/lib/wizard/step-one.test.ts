import { describe, expect, it } from "vitest";

import { resolveStepOneValues } from "@/lib/wizard/step-one";

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
