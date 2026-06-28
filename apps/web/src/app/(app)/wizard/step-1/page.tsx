"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { WizardProgress } from "@/components/wizard-progress";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { saveWizardProgress } from "@/lib/wizard/progress";

const seniorityOptions = ["junior", "mid", "senior", "staff", "principal"];
const workModalities = [
  { value: "remote", label: "Remoto" },
  { value: "hybrid", label: "Hibrido" },
  { value: "onsite", label: "Presencial" }
];

export default function WizardStepOnePage() {
  const router = useRouter();
  const [headline, setHeadline] = useState("");
  const [summary, setSummary] = useState("");
  const [targetRole, setTargetRole] = useState("");
  const [targetSeniority, setTargetSeniority] = useState("mid");
  const [workModality, setWorkModality] = useState("remote");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await apiClient("/api/v1/profiles/me", {
        method: "PATCH",
        body: JSON.stringify({
          headline,
          summary,
          target_role: targetRole,
          target_seniority: targetSeniority,
          work_modality: workModality
        })
      });
      saveWizardProgress({ currentStep: 2 });
      router.push("/wizard/step-2");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No se pudo guardar tu perfil."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <WizardProgress currentStep={1} />
      <Card>
        <CardHeader>
          <CardTitle>Info basica</CardTitle>
          <CardDescription>
            Estos datos calibran el Match Score contra tu objetivo laboral.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="headline">
                Headline
              </label>
              <input
                className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                id="headline"
                onChange={(event) => setHeadline(event.target.value)}
                placeholder="Backend Engineer"
                required
                value={headline}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="summary">
                Bio
              </label>
              <textarea
                className="min-h-28 w-full resize-none rounded-md border border-input bg-background p-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                id="summary"
                onChange={(event) => setSummary(event.target.value)}
                placeholder="Contame en pocas lineas que haces y hacia donde queres ir."
                value={summary}
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="targetRole">
                  Rol objetivo
                </label>
                <input
                  className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  id="targetRole"
                  onChange={(event) => setTargetRole(event.target.value)}
                  placeholder="AI Product Engineer"
                  required
                  value={targetRole}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="seniority">
                  Seniority
                </label>
                <select
                  className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  id="seniority"
                  onChange={(event) => setTargetSeniority(event.target.value)}
                  value={targetSeniority}
                >
                  {seniorityOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <fieldset className="space-y-3">
              <legend className="text-sm font-medium">Modalidad</legend>
              <div className="grid gap-3 sm:grid-cols-3">
                {workModalities.map((option) => (
                  <label
                    className="flex h-11 items-center gap-3 rounded-md border border-input px-3 text-sm"
                    key={option.value}
                  >
                    <input
                      checked={workModality === option.value}
                      name="workModality"
                      onChange={() => setWorkModality(option.value)}
                      type="radio"
                    />
                    {option.label}
                  </label>
                ))}
              </div>
            </fieldset>

            {error ? <p className="text-sm text-destructive">{error}</p> : null}

            <Button className="w-full sm:w-auto" disabled={isSubmitting} type="submit">
              {isSubmitting ? "Guardando..." : "Continuar"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
