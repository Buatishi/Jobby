"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Check, Info, X } from "lucide-react";

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
import {
  getWizardProgress,
  saveWizardProgress,
  type WizardSkillDraft
} from "@/lib/wizard/progress";

export default function WizardStepThreePage() {
  const router = useRouter();
  const [skills, setSkills] = useState<WizardSkillDraft[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const progress = getWizardProgress();
    setSkills(progress.parsedSkills ?? []);
  }, []);

  function updateSkill(id: string, patch: Partial<WizardSkillDraft>) {
    setSkills((currentSkills) =>
      currentSkills.map((skill) =>
        skill.id === id ? { ...skill, ...patch } : skill
      )
    );
  }

  async function confirmSkill(skill: WizardSkillDraft) {
    await apiClient("/api/v1/profiles/skills", {
      method: "POST",
      body: JSON.stringify({
        name: skill.name,
        category: skill.category,
        level: skill.level,
        in_cv: true,
        confirmed: true
      })
    });
    updateSkill(skill.id, { confirmed: true, rejected: false });
  }

  async function rejectSkill(skill: WizardSkillDraft) {
    await apiClient("/api/v1/profiles/rejected-skills", {
      method: "POST",
      body: JSON.stringify({
        name: skill.name,
        category: skill.category,
        reason: "wizard_review"
      })
    });
    updateSkill(skill.id, { rejected: true, confirmed: false });
  }

  async function handleConfirmAll() {
    setError(null);
    setIsSubmitting(true);

    try {
      for (const skill of skills.filter((item) => !item.rejected)) {
        if (!skill.confirmed && skill.name.trim()) {
          await confirmSkill(skill);
        }
      }
      saveWizardProgress({ currentStep: 4, parsedSkills: skills });
      router.push("/wizard/step-4");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No se pudieron confirmar las skills."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <WizardProgress currentStep={3} completionPercent={60} />
      <Card>
        <CardHeader>
          <CardTitle>Revisá la extracción</CardTitle>
          <CardDescription>
            Confirmá solo lo que querés sumar al perfil maestro. Nada se elimina
            automáticamente.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {skills.length === 0 ? (
            <div className="rounded-md border border-border bg-muted/30 p-5 text-sm">
              <div className="flex gap-3">
                <Info className="mt-0.5 h-4 w-4 flex-none text-[#0F6E56]" />
                <div>
                  <p className="font-medium">No hay skills para revisar todavía.</p>
                  <p className="mt-1 text-muted-foreground">
                    Podés volver a cargar un CV o avanzar y completar skills
                    manualmente desde tu perfil.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-md border border-border">
              <table className="w-full min-w-[720px] text-sm">
                <thead className="bg-muted/50 text-left">
                  <tr>
                    <th className="px-4 py-3 font-medium">Skill</th>
                    <th className="px-4 py-3 font-medium">Nivel</th>
                    <th className="px-4 py-3 font-medium">Fuente</th>
                    <th className="px-4 py-3 text-right font-medium">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {skills.map((skill) => (
                    <tr className="border-t border-border" key={skill.id}>
                      <td className="px-4 py-3">
                        <input
                          className="h-10 w-full rounded-md border border-input bg-background px-3 outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          onChange={(event) =>
                            updateSkill(skill.id, { name: event.target.value })
                          }
                          value={skill.name}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <input
                          className="h-10 w-full rounded-md border border-input bg-background px-3 outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          onChange={(event) =>
                            updateSkill(skill.id, { level: event.target.value })
                          }
                          value={skill.level ?? ""}
                        />
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {skill.source}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-2">
                          <Button
                            aria-label={`Confirmar ${skill.name}`}
                            disabled={isSubmitting || skill.confirmed}
                            onClick={() => void confirmSkill(skill)}
                            type="button"
                            variant="secondary"
                          >
                            <Check className="h-4 w-4" />
                          </Button>
                          <Button
                            aria-label={`Rechazar ${skill.name}`}
                            disabled={isSubmitting || skill.rejected}
                            onClick={() => void rejectSkill(skill)}
                            type="button"
                            variant="ghost"
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {error ? <p className="mt-4 text-sm text-destructive">{error}</p> : null}

          <div className="mt-5 flex flex-col gap-3 sm:flex-row">
            <Button
              disabled={isSubmitting || skills.length === 0}
              onClick={handleConfirmAll}
              type="button"
            >
              {isSubmitting ? "Confirmando..." : "Confirmar todo"}
            </Button>
            <Button
              disabled={isSubmitting}
              onClick={() => {
                saveWizardProgress({ currentStep: 4, parsedSkills: skills });
                router.push("/wizard/step-4");
              }}
              type="button"
              variant="ghost"
            >
              Continuar
            </Button>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
