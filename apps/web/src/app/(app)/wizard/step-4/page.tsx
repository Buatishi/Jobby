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
import { completeWizard } from "@/lib/wizard/progress";

export default function WizardStepFourPage() {
  const router = useRouter();
  const [company, setCompany] = useState("");
  const [title, setTitle] = useState("");
  const [education, setEducation] = useState("");
  const [language, setLanguage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const requests: Array<Promise<unknown>> = [];

      if (company || title) {
        requests.push(
          apiClient("/api/v1/profiles/experiences", {
            method: "POST",
            body: JSON.stringify({
              company,
              title,
              description: null,
              achievements: []
            })
          })
        );
      }

      if (education) {
        requests.push(
          apiClient("/api/v1/profiles/educations", {
            method: "POST",
            body: JSON.stringify({
              institution: education,
              field_of_study: null,
              degree_level: null
            })
          })
        );
      }

      if (language) {
        requests.push(
          apiClient("/api/v1/profiles/languages", {
            method: "POST",
            body: JSON.stringify({
              name: language,
              level: "professional"
            })
          })
        );
      }

      await Promise.all(requests);
      completeWizard();
      router.push("/dashboard");
      router.refresh();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No se pudo completar el onboarding."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <WizardProgress currentStep={4} />
      <Card>
        <CardHeader>
          <CardTitle>Enriquecimiento</CardTitle>
          <CardDescription>
            Agregá datos manuales para mejorar la primera lectura de tu perfil.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="company">
                  Empresa reciente
                </label>
                <input
                  className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  id="company"
                  onChange={(event) => setCompany(event.target.value)}
                  placeholder="Acme"
                  value={company}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="title">
                  Cargo
                </label>
                <input
                  className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  id="title"
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="Software Engineer"
                  value={title}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="education">
                Educación
              </label>
              <input
                className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                id="education"
                onChange={(event) => setEducation(event.target.value)}
                placeholder="Universidad, bootcamp o certificación principal"
                value={education}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="language">
                Idioma adicional
              </label>
              <input
                className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                id="language"
                onChange={(event) => setLanguage(event.target.value)}
                placeholder="Inglés"
                value={language}
              />
            </div>

            {error ? <p className="text-sm text-destructive">{error}</p> : null}

            <div className="flex flex-col gap-3 sm:flex-row">
              <Button disabled={isSubmitting} type="submit">
                {isSubmitting ? "Guardando..." : "Completar onboarding"}
              </Button>
              <Button
                disabled={isSubmitting}
                onClick={() => {
                  completeWizard();
                  router.push("/dashboard");
                }}
                type="button"
                variant="ghost"
              >
                Finalizar sin agregar más
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
