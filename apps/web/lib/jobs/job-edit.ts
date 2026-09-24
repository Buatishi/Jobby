// Mismos valores que acepta PATCH /jobs/{id} y que entiende el cálculo del MatchScore.
export const JOB_SENIORITIES = [
  "junior",
  "mid",
  "senior",
  "staff",
  "principal"
] as const;

export const JOB_MODALITIES = [
  { value: "remote", label: "Remoto" },
  { value: "hybrid", label: "Híbrido" },
  { value: "onsite", label: "Presencial" }
] as const;

const MODALITY_VALUES: readonly string[] = JOB_MODALITIES.map(
  (modality) => modality.value
);
const MAX_TEXT_LENGTH = 200;
const MAX_SALARY = 100_000_000;

export type JobSummary = {
  id: string;
  job_title?: string | null;
  company_name?: string | null;
  required_seniority?: string | null;
  required_modality?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string | null;
  created_at?: string | null;
};

export type JobFormValues = {
  jobTitle: string;
  companyName: string;
  seniority: string;
  modality: string;
  salaryMin: string;
  salaryMax: string;
  currency: string;
};

export type JobUpdatePayload = {
  job_title?: string | null;
  company_name?: string | null;
  required_seniority?: string | null;
  required_modality?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string | null;
};

export type JobUpdateResult =
  | { ok: true; payload: JobUpdatePayload }
  | { ok: false; error: string };

type Parsed<T> = { ok: true; value: T } | { ok: false; error: string };

// La IA puede haber guardado "Senior" o "Remoto": si equivale a un valor conocido se
// normaliza, y si no, se conserva tal cual para no borrarlo sin que la persona lo pida.
function toKnownValue(value: string | null | undefined, allowed: readonly string[]) {
  const text = (value ?? "").trim();
  const normalized = text.toLowerCase();
  return allowed.includes(normalized) ? normalized : text;
}

export function toJobFormValues(job: JobSummary): JobFormValues {
  return {
    jobTitle: job.job_title ?? "",
    companyName: job.company_name ?? "",
    seniority: toKnownValue(job.required_seniority, JOB_SENIORITIES),
    modality: toKnownValue(job.required_modality, MODALITY_VALUES),
    salaryMin: job.salary_min == null ? "" : String(job.salary_min),
    salaryMax: job.salary_max == null ? "" : String(job.salary_max),
    currency: job.currency ?? ""
  };
}

function parseSalary(raw: string, label: string): Parsed<number | null> {
  const text = raw.trim();
  if (!text) {
    return { ok: true, value: null };
  }
  if (!/^\d+$/.test(text)) {
    return {
      ok: false,
      error: `${label}: ingresá un número entero, sin puntos ni símbolos.`
    };
  }
  const value = Number(text);
  if (value > MAX_SALARY) {
    return { ok: false, error: `${label}: el valor es demasiado alto.` };
  }
  return { ok: true, value };
}

function parseText(raw: string, label: string): Parsed<string | null> {
  const text = raw.trim();
  if (text.length > MAX_TEXT_LENGTH) {
    return {
      ok: false,
      error: `${label}: admite hasta ${MAX_TEXT_LENGTH} caracteres.`
    };
  }
  return { ok: true, value: text || null };
}

function parseChoice(
  value: string,
  initial: string,
  allowed: readonly string[],
  label: string
): Parsed<string | null> {
  // El valor original, aunque no sea uno conocido, se puede dejar como estaba.
  if (value === "" || value === initial || allowed.includes(value)) {
    return { ok: true, value: value || null };
  }
  return { ok: false, error: `${label}: elegí una opción de la lista.` };
}

/** Arma el cuerpo del PATCH solo con lo que la persona cambió. */
export function buildJobUpdate(
  initial: JobFormValues,
  current: JobFormValues
): JobUpdateResult {
  const payload: JobUpdatePayload = {};

  const title = parseText(current.jobTitle, "Puesto");
  if (!title.ok) {
    return title;
  }
  if (title.value !== (initial.jobTitle.trim() || null)) {
    payload.job_title = title.value;
  }

  const company = parseText(current.companyName, "Empresa");
  if (!company.ok) {
    return company;
  }
  if (company.value !== (initial.companyName.trim() || null)) {
    payload.company_name = company.value;
  }

  const seniority = parseChoice(
    current.seniority,
    initial.seniority,
    JOB_SENIORITIES,
    "Seniority"
  );
  if (!seniority.ok) {
    return seniority;
  }
  if (current.seniority !== initial.seniority) {
    payload.required_seniority = seniority.value;
  }

  const modality = parseChoice(
    current.modality,
    initial.modality,
    MODALITY_VALUES,
    "Modalidad"
  );
  if (!modality.ok) {
    return modality;
  }
  if (current.modality !== initial.modality) {
    payload.required_modality = modality.value;
  }

  const salaryMin = parseSalary(current.salaryMin, "Salario mínimo");
  if (!salaryMin.ok) {
    return salaryMin;
  }
  const salaryMax = parseSalary(current.salaryMax, "Salario máximo");
  if (!salaryMax.ok) {
    return salaryMax;
  }
  const minChanged = current.salaryMin.trim() !== initial.salaryMin.trim();
  const maxChanged = current.salaryMax.trim() !== initial.salaryMax.trim();
  if (minChanged || maxChanged) {
    if (
      salaryMin.value !== null &&
      salaryMax.value !== null &&
      salaryMin.value > salaryMax.value
    ) {
      return {
        ok: false,
        error: "El salario mínimo no puede superar al máximo."
      };
    }
    if (minChanged) {
      payload.salary_min = salaryMin.value;
    }
    if (maxChanged) {
      payload.salary_max = salaryMax.value;
    }
  }

  const currency = current.currency.trim().toUpperCase();
  if (currency !== initial.currency.trim().toUpperCase()) {
    if (currency && !/^[A-Z]{3}$/.test(currency)) {
      return {
        ok: false,
        error: "Moneda: usá el código de tres letras, como ARS o USD."
      };
    }
    payload.currency = currency || null;
  }

  if (Object.keys(payload).length === 0) {
    return { ok: false, error: "No cambiaste ningún dato." };
  }
  return { ok: true, payload };
}

const salaryFormat = new Intl.NumberFormat("es-AR");

function describeSalary(job: JobSummary) {
  const currency = job.currency ? ` ${job.currency.toUpperCase()}` : "";
  const min = job.salary_min;
  const max = job.salary_max;
  if (min != null && max != null) {
    return `${salaryFormat.format(min)} a ${salaryFormat.format(max)}${currency}`;
  }
  if (min != null) {
    return `desde ${salaryFormat.format(min)}${currency}`;
  }
  if (max != null) {
    return `hasta ${salaryFormat.format(max)}${currency}`;
  }
  return null;
}

/** Resumen de una línea con seniority, modalidad y salario, si los hay. */
export function describeJobDetails(job: JobSummary) {
  const modality = toKnownValue(job.required_modality, MODALITY_VALUES);
  const modalityLabel =
    JOB_MODALITIES.find((option) => option.value === modality)?.label ?? modality;
  return [
    toKnownValue(job.required_seniority, JOB_SENIORITIES),
    modalityLabel,
    describeSalary(job)
  ]
    .filter(Boolean)
    .join(" · ");
}
