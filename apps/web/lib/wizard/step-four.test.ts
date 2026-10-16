import { describe, expect, it } from "vitest";

import {
  applyStepFourWrite,
  mergeLoadedValues,
  planStepFourWrites,
  resolveStepFour,
  STEP_FOUR_DEFAULTS,
  STEP_FOUR_NOTHING_SAVED,
  type StepFourField,
  type StepFourSaved,
  type StepFourValues
} from "@/lib/wizard/step-four";

const details = {
  experiences: [
    { id: "exp-new", company: "Acme", title: "Backend Engineer" },
    { id: "exp-old", company: "Initech", title: "Soporte" }
  ],
  educations: [{ id: "edu-1", institution: "UTN" }],
  languages: [{ id: "lang-1", name: "Inglés" }]
};

const saved: StepFourSaved = {
  experience: { id: "exp-new", company: "Acme", title: "Backend Engineer" },
  education: { id: "edu-1", institution: "UTN" },
  language: { id: "lang-1", name: "Inglés" }
};

const sameAsSaved: StepFourValues = {
  company: "Acme",
  title: "Backend Engineer",
  education: "UTN",
  language: "Inglés"
};

describe("resolveStepFour", () => {
  it("opens with the newest saved row of each kind", () => {
    const resolution = resolveStepFour(details);

    expect(resolution.values).toEqual(sameAsSaved);
    expect(resolution.saved).toEqual(saved);
    expect(resolution.experienceCount).toBe(2);
    expect(resolution.prefilled).toBe(true);
  });

  it("opens empty when nothing was saved", () => {
    const resolution = resolveStepFour({
      experiences: [],
      educations: [],
      languages: []
    });

    expect(resolution.values).toEqual(STEP_FOUR_DEFAULTS);
    expect(resolution.saved).toEqual(STEP_FOUR_NOTHING_SAVED);
    expect(resolution.experienceCount).toBe(0);
    expect(resolution.prefilled).toBe(false);
  });

  it("opens empty when the details could not be loaded", () => {
    const resolution = resolveStepFour(null);

    expect(resolution.values).toEqual(STEP_FOUR_DEFAULTS);
    expect(resolution.saved).toEqual(STEP_FOUR_NOTHING_SAVED);
    expect(resolution.prefilled).toBe(false);
  });

  it("treats null columns as empty text", () => {
    const resolution = resolveStepFour({
      experiences: [{ id: "exp-1", company: null, title: "Dev" }]
    });

    expect(resolution.values.company).toBe("");
    expect(resolution.values.title).toBe("Dev");
    expect(resolution.saved.experience).toEqual({
      id: "exp-1",
      company: "",
      title: "Dev"
    });
  });
});

describe("mergeLoadedValues", () => {
  const loaded: StepFourValues = sameAsSaved;

  it("fills every field the person did not touch", () => {
    const merged = mergeLoadedValues(
      STEP_FOUR_DEFAULTS,
      new Set<StepFourField>(),
      loaded
    );

    expect(merged).toEqual(loaded);
  });

  it("keeps what the person typed while the data was loading", () => {
    const merged = mergeLoadedValues(
      { ...STEP_FOUR_DEFAULTS, company: "Globex" },
      new Set<StepFourField>(["company"]),
      loaded
    );

    expect(merged.company).toBe("Globex");
    expect(merged.title).toBe("Backend Engineer");
  });

  it("keeps a field the person emptied on purpose", () => {
    const merged = mergeLoadedValues(
      STEP_FOUR_DEFAULTS,
      new Set<StepFourField>(["language"]),
      loaded
    );

    expect(merged.language).toBe("");
  });
});

describe("planStepFourWrites", () => {
  it("creates each row the first time", () => {
    const writes = planStepFourWrites(sameAsSaved, STEP_FOUR_NOTHING_SAVED);

    expect(writes.map((write) => [write.section, write.method, write.path])).toEqual([
      ["experience", "POST", "/api/v1/profiles/experiences"],
      ["education", "POST", "/api/v1/profiles/educations"],
      ["language", "POST", "/api/v1/profiles/languages"]
    ]);
    expect(writes[0]?.body).toEqual({
      company: "Acme",
      title: "Backend Engineer",
      description: null,
      achievements: []
    });
    expect(writes[2]?.body).toEqual({ name: "Inglés", level: "professional" });
  });

  it("writes nothing when the form matches what is saved", () => {
    // Era la causa de los duplicados: pasar otra vez por el paso volvía a insertar.
    expect(planStepFourWrites(sameAsSaved, saved)).toEqual([]);
  });

  it("ignores spaces around the saved values", () => {
    const padded: StepFourValues = {
      company: " Acme ",
      title: "Backend Engineer  ",
      education: " UTN",
      language: "Inglés "
    };

    expect(planStepFourWrites(padded, saved)).toEqual([]);
  });

  it("edits the saved row instead of adding another", () => {
    const writes = planStepFourWrites(
      { ...sameAsSaved, company: "Acme SA", language: "Portugués" },
      saved
    );

    expect(writes.map((write) => [write.method, write.path])).toEqual([
      ["PATCH", "/api/v1/profiles/experiences/exp-new"],
      ["PATCH", "/api/v1/profiles/languages/lang-1"]
    ]);
    expect(writes[0]?.body).toEqual({
      company: "Acme SA",
      title: "Backend Engineer"
    });
    expect(writes[1]?.body).toEqual({ name: "Portugués" });
  });

  it("does not create a row for an empty field", () => {
    const writes = planStepFourWrites(
      { ...STEP_FOUR_DEFAULTS, education: "UBA" },
      STEP_FOUR_NOTHING_SAVED
    );

    expect(writes.map((write) => write.section)).toEqual(["education"]);
  });

  it("does not create a row from spaces alone", () => {
    expect(
      planStepFourWrites(
        { company: "  ", title: " ", education: " ", language: "   " },
        STEP_FOUR_NOTHING_SAVED
      )
    ).toEqual([]);
  });

  it("accepts an experience with only the company or only the title", () => {
    const onlyTitle = planStepFourWrites(
      { ...STEP_FOUR_DEFAULTS, title: "Dev" },
      STEP_FOUR_NOTHING_SAVED
    );

    expect(onlyTitle[0]?.body).toMatchObject({ company: "", title: "Dev" });
  });

  it("leaves a saved value alone when the field was emptied", () => {
    // No hay borrado en la API: vaciar el campo no cambia lo guardado.
    expect(
      planStepFourWrites({ ...sameAsSaved, education: "", language: "" }, saved)
    ).toEqual([]);
  });
});

describe("applyStepFourWrite", () => {
  it("remembers the id of a row that was just created", () => {
    const [write] = planStepFourWrites(
      { ...STEP_FOUR_DEFAULTS, education: "UBA" },
      STEP_FOUR_NOTHING_SAVED
    );
    if (!write) {
      throw new Error("expected one write");
    }

    const next = applyStepFourWrite(STEP_FOUR_NOTHING_SAVED, write, "edu-9");

    expect(next.education).toEqual({ id: "edu-9", institution: "UBA" });
    expect(next.experience).toBeNull();
  });

  it("keeps the id and takes the new value after an edit", () => {
    const [write] = planStepFourWrites({ ...sameAsSaved, language: "Francés" }, saved);
    if (!write) {
      throw new Error("expected one write");
    }

    const next = applyStepFourWrite(saved, write, "ignored");

    expect(next.language).toEqual({ id: "lang-1", name: "Francés" });
  });

  it("does not repeat a write once it is applied", () => {
    // Si otro pedido del mismo guardado falla, al reintentar no se vuelve a crear.
    const values: StepFourValues = { ...sameAsSaved };
    let current = STEP_FOUR_NOTHING_SAVED;
    const first = planStepFourWrites(values, current);
    const experienceWrite = first.find((write) => write.section === "experience");
    if (!experienceWrite) {
      throw new Error("expected an experience write");
    }
    current = applyStepFourWrite(current, experienceWrite, "exp-1");

    const retry = planStepFourWrites(values, current);

    expect(retry.map((write) => write.section)).toEqual(["education", "language"]);
  });

  it("keeps the saved state when the response had no id", () => {
    const [write] = planStepFourWrites(
      { ...STEP_FOUR_DEFAULTS, language: "Inglés" },
      STEP_FOUR_NOTHING_SAVED
    );
    if (!write) {
      throw new Error("expected one write");
    }

    expect(applyStepFourWrite(STEP_FOUR_NOTHING_SAVED, write, null)).toEqual(
      STEP_FOUR_NOTHING_SAVED
    );
  });
});
