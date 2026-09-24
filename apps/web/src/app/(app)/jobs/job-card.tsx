"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { Pencil, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import {
  JOB_MODALITIES,
  JOB_SENIORITIES,
  buildJobUpdate,
  describeJobDetails,
  toJobFormValues,
  type JobFormValues,
  type JobSummary
} from "@/lib/jobs/job-edit";

type JobCardProps = {
  job: JobSummary;
  onUpdated: (job: JobSummary) => void;
  onDeleted: (jobId: string) => void;
};

type Mode = "view" | "edit" | "confirm-delete";

const fieldClassName =
  "h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring";

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function JobCard({ job, onUpdated, onDeleted }: JobCardProps) {
  const [mode, setMode] = useState<Mode>("view");
  const [values, setValues] = useState<JobFormValues>(() => toJobFormValues(job));
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const title = job.job_title || "Puesto sin título";
  const details = describeJobDetails(job);
  const initialValues = toJobFormValues(job);
  const fieldId = (name: string) => `job-${job.id}-${name}`;

  function changeMode(nextMode: Mode) {
    setValues(toJobFormValues(job));
    setError(null);
    setMode(nextMode);
  }

  function setField(field: keyof JobFormValues, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  async function saveChanges(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const result = buildJobUpdate(initialValues, values);
    if (!result.ok) {
      setError(result.error);
      return;
    }

    setIsBusy(true);
    setError(null);
    try {
      const updated = await apiClient<JobSummary>(`/api/v1/jobs/${job.id}`, {
        method: "PATCH",
        body: JSON.stringify(result.payload)
      });
      onUpdated(updated);
      setMode("view");
    } catch (requestError) {
      setError(errorMessage(requestError, "No se pudo guardar el puesto."));
    } finally {
      setIsBusy(false);
    }
  }

  async function deleteJob() {
    setIsBusy(true);
    setError(null);
    try {
      await apiClient<void>(`/api/v1/jobs/${job.id}`, { method: "DELETE" });
      onDeleted(job.id);
    } catch (requestError) {
      // Vuelve a la vista normal con el motivo (por ejemplo, el 409 si ya tiene resultados).
      setError(errorMessage(requestError, "No se pudo eliminar el puesto."));
      setMode("view");
      setIsBusy(false);
    }
  }

  // Si la IA guardó un valor que no está en la lista, se muestra como opción para
  // que quede como estaba mientras nadie elija otro.
  const seniorityOptions: readonly string[] = JOB_SENIORITIES;
  const hasUnknownSeniority =
    initialValues.seniority !== "" &&
    !seniorityOptions.includes(initialValues.seniority);
  const hasUnknownModality =
    initialValues.modality !== "" &&
    !JOB_MODALITIES.some((option) => option.value === initialValues.modality);

  return (
    <Card>
      <CardContent className="p-5">
        {mode === "edit" ? (
          <form className="space-y-4" onSubmit={saveChanges}>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor={fieldId("title")}>
                  Puesto
                </label>
                <input
                  className={fieldClassName}
                  id={fieldId("title")}
                  maxLength={200}
                  onChange={(event) => setField("jobTitle", event.target.value)}
                  value={values.jobTitle}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor={fieldId("company")}>
                  Empresa
                </label>
                <input
                  className={fieldClassName}
                  id={fieldId("company")}
                  maxLength={200}
                  onChange={(event) => setField("companyName", event.target.value)}
                  value={values.companyName}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor={fieldId("seniority")}>
                  Seniority
                </label>
                <select
                  className={fieldClassName}
                  id={fieldId("seniority")}
                  onChange={(event) => setField("seniority", event.target.value)}
                  value={values.seniority}
                >
                  <option value="">Sin definir</option>
                  {hasUnknownSeniority ? (
                    <option value={initialValues.seniority}>
                      {initialValues.seniority} (detectado)
                    </option>
                  ) : null}
                  {JOB_SENIORITIES.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor={fieldId("modality")}>
                  Modalidad
                </label>
                <select
                  className={fieldClassName}
                  id={fieldId("modality")}
                  onChange={(event) => setField("modality", event.target.value)}
                  value={values.modality}
                >
                  <option value="">Sin definir</option>
                  {hasUnknownModality ? (
                    <option value={initialValues.modality}>
                      {initialValues.modality} (detectado)
                    </option>
                  ) : null}
                  {JOB_MODALITIES.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor={fieldId("salary-min")}>
                  Salario mínimo
                </label>
                <input
                  className={fieldClassName}
                  id={fieldId("salary-min")}
                  inputMode="numeric"
                  onChange={(event) => setField("salaryMin", event.target.value)}
                  value={values.salaryMin}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor={fieldId("salary-max")}>
                  Salario máximo
                </label>
                <input
                  className={fieldClassName}
                  id={fieldId("salary-max")}
                  inputMode="numeric"
                  onChange={(event) => setField("salaryMax", event.target.value)}
                  value={values.salaryMax}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor={fieldId("currency")}>
                  Moneda
                </label>
                <input
                  className={fieldClassName}
                  id={fieldId("currency")}
                  maxLength={3}
                  onChange={(event) => setField("currency", event.target.value)}
                  placeholder="ARS"
                  value={values.currency}
                />
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              El texto original del aviso no se edita: para analizar otro texto, cargá
              un puesto nuevo. Los cambios no recalculan comparaciones ya hechas.
            </p>
            {error ? (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            ) : null}
            <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
              <Button
                disabled={isBusy}
                onClick={() => changeMode("view")}
                type="button"
                variant="outline"
              >
                Cancelar
              </Button>
              <Button isLoading={isBusy} type="submit">
                Guardar cambios
              </Button>
            </div>
          </form>
        ) : (
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-medium">{title}</p>
              <p className="text-sm text-muted-foreground">
                {job.company_name || "Empresa no detectada"}
              </p>
              {details ? (
                <p className="mt-1 text-xs text-muted-foreground">{details}</p>
              ) : null}
            </div>
            {mode === "confirm-delete" ? (
              <div className="flex flex-col gap-2 sm:items-end">
                <p className="text-sm">¿Eliminar este puesto? No se puede deshacer.</p>
                <div className="flex gap-2">
                  <Button
                    disabled={isBusy}
                    onClick={() => changeMode("view")}
                    size="sm"
                    type="button"
                    variant="outline"
                  >
                    Cancelar
                  </Button>
                  <Button
                    isLoading={isBusy}
                    onClick={() => void deleteJob()}
                    size="sm"
                    type="button"
                    variant="danger"
                  >
                    Eliminar
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                <Button asChild variant="secondary">
                  <Link href={`/jobs/${job.id}`}>Ver reporte</Link>
                </Button>
                <Button
                  aria-label={`Editar ${title}`}
                  leftIcon={<Pencil aria-hidden="true" className="h-4 w-4" />}
                  onClick={() => changeMode("edit")}
                  type="button"
                  variant="outline"
                >
                  Editar
                </Button>
                <Button
                  aria-label={`Eliminar ${title}`}
                  leftIcon={<Trash2 aria-hidden="true" className="h-4 w-4" />}
                  onClick={() => changeMode("confirm-delete")}
                  type="button"
                  variant="ghost"
                >
                  Eliminar
                </Button>
              </div>
            )}
          </div>
        )}
        {mode !== "edit" && error ? (
          <p className="mt-3 text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
