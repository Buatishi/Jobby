"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2 } from "lucide-react";

import { WizardProgress } from "@/components/wizard-progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import {
  completeWizard,
  getWizardProgress,
  type WizardSkillDraft
} from "@/lib/wizard/progress";

type ProfilePreview = {
  headline?: string | null;
  target_role?: string | null;
  completeness_pct?: number | null;
};

export default function WizardStepFourPage() {
  const router = useRouter();
  const [company, setCompany] = useState("");
  const [title, setTitle] = useState("");
  const [education, setEducation] = useState("");
  const [language, setLanguage] = useState("");
  const [profile, setProfile] = useState<ProfilePreview | null>(null);
  const [skills, setSkills] = useState<WizardSkillDraft[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const progress = getWizardProgress();
    setSkills((progress.parsedSkills ?? []).filter((skill) => !skill.rejected));

    void apiClient<ProfilePreview>("/api/v1/profiles/me")
      .then(setProfile)
      .catch(() => setProfile(null));
  }, []);

  const visibleSkills = useMemo(() => skills.slice(0, 8), [skills]);
  const experienceCount = company || title ? 1 : 0;

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
      <WizardProgress currentStep={4} completionPercent={85} />
      <Card>
        <CardHeader>
          <CardTitle>Enriquecé tu perfil</CardTitle>
          <CardDescription>
            Sumá señales adicionales para mejorar el primer reporte. Este paso
            es opcional y editable más adelante.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-5 rounded-md border border-[#0F6E56]/20 bg-[#0F6E56]/5 p-4 text-sm">
            <div className="flex gap-3">
              <CheckCircle2 className="mt-0.5 h-4 w-4 flex-none text-[#0F6E56]" />
              <p className="text-muted-foreground">
                Ya podés usar el dashboard. Estos datos solo ayudan a que el
                sistema entienda mejor experiencia, educación e idiomas.
              </p>
            </div>
          </div>

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

            <Card className="border-[#0F6E56]/15 bg-[#0F6E56]/5 shadow-none">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">
                  Así va a ver tu perfil la IA
                </CardTitle>
                <CardDescription>
                  Revisá el resumen antes de terminar la configuración.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm font-semibold">
                    {profile?.headline || "Headline pendiente"}
                    {profile?.target_role ? ` · ${profile.target_role}` : ""}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Experiencias cargadas en este paso: {experienceCount}
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  {visibleSkills.length > 0 ? (
                    visibleSkills.map((skill) => (
                      <Badge
                        className="rounded-full bg-white text-[#0F6E56]"
                        key={skill.id}
                        variant="outline"
                      >
                        {skill.name}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-xs text-muted-foreground">
                      Todavía no hay skills confirmadas en este wizard.
                    </span>
                  )}
                </div>

                <Badge className="bg-[#0F6E56] text-white">
                  Completeness actual: {profile?.completeness_pct ?? 0}%
                </Badge>
              </CardContent>
            </Card>

            {error ? <p className="text-sm text-destructive">{error}</p> : null}

            <div className="flex flex-col gap-3 sm:flex-row">
              <Button disabled={isSubmitting} type="submit">
                {isSubmitting ? "Guardando..." : "Guardar y finalizar"}
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
