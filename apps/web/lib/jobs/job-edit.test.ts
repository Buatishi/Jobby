import { describe, expect, it } from "vitest";

import {
  buildJobUpdate,
  describeJobDetails,
  toJobFormValues,
  type JobSummary
} from "@/lib/jobs/job-edit";

const job: JobSummary = {
  id: "job-1",
  job_title: "Backend Engineer",
  company_name: "Acme",
  required_seniority: "Senior",
  required_modality: "remote",
  salary_min: 1000,
  salary_max: 2000,
  currency: "usd"
};

describe("toJobFormValues", () => {
  it("normalizes known values and keeps unknown ones as they are", () => {
    const values = toJobFormValues({
      ...job,
      required_seniority: "Semi Senior",
      required_modality: "Remote"
    });

    expect(values.seniority).toBe("Semi Senior");
    expect(values.modality).toBe("remote");
    expect(values.salaryMin).toBe("1000");
  });

  it("turns missing values into empty fields", () => {
    const values = toJobFormValues({ id: "job-2" });

    expect(values).toEqual({
      jobTitle: "",
      companyName: "",
      seniority: "",
      modality: "",
      salaryMin: "",
      salaryMax: "",
      currency: ""
    });
  });
});

describe("buildJobUpdate", () => {
  const initial = toJobFormValues(job);

  it("sends only the fields that changed, trimmed", () => {
    const result = buildJobUpdate(initial, {
      ...initial,
      jobTitle: "  Backend Engineer Sr ",
      seniority: "staff"
    });

    expect(result).toEqual({
      ok: true,
      payload: { job_title: "Backend Engineer Sr", required_seniority: "staff" }
    });
  });

  it("sends null to clear a field", () => {
    const result = buildJobUpdate(initial, {
      ...initial,
      companyName: "   ",
      salaryMax: ""
    });

    expect(result).toEqual({
      ok: true,
      payload: { company_name: null, salary_max: null }
    });
  });

  it("does not send the currency when only its case differs", () => {
    const result = buildJobUpdate(initial, { ...initial, currency: "USD" });

    expect(result).toEqual({ ok: false, error: "No cambiaste ningún dato." });
  });

  it("keeps an unknown detected value untouched unless another one is chosen", () => {
    const detected = toJobFormValues({ ...job, required_seniority: "Semi Senior" });

    expect(buildJobUpdate(detected, { ...detected, jobTitle: "Otro" })).toEqual({
      ok: true,
      payload: { job_title: "Otro" }
    });
    expect(buildJobUpdate(detected, { ...detected, seniority: "mid" })).toEqual({
      ok: true,
      payload: { required_seniority: "mid" }
    });
  });

  it.each([
    [{ salaryMin: "1.500" }, "Salario mínimo: ingresá un número entero"],
    [{ salaryMax: "-3" }, "Salario máximo: ingresá un número entero"],
    [{ salaryMin: "3000" }, "El salario mínimo no puede superar al máximo."],
    [{ currency: "dólares" }, "Moneda: usá el código de tres letras"],
    [{ seniority: "semi senior" }, "Seniority: elegí una opción de la lista."],
    [{ jobTitle: "x".repeat(201) }, "Puesto: admite hasta 200 caracteres."]
  ])("rejects %o before calling the API", (change, message) => {
    const result = buildJobUpdate(initial, { ...initial, ...change });

    expect(result.ok).toBe(false);
    expect(result.ok ? "" : result.error).toContain(message);
  });

  it("does not block other edits when the stored salary range is already wrong", () => {
    const wrong = toJobFormValues({ ...job, salary_min: 5000, salary_max: 3000 });

    expect(buildJobUpdate(wrong, { ...wrong, jobTitle: "Backend" })).toEqual({
      ok: true,
      payload: { job_title: "Backend" }
    });
  });
});

describe("describeJobDetails", () => {
  it("summarizes seniority, modality and salary", () => {
    expect(describeJobDetails(job)).toBe("senior · Remoto · 1.000 a 2.000 USD");
  });

  it("describes open salary ranges and skips what is missing", () => {
    expect(describeJobDetails({ id: "j", salary_min: 900, currency: "ARS" })).toBe(
      "desde 900 ARS"
    );
    expect(describeJobDetails({ id: "j" })).toBe("");
  });
});
