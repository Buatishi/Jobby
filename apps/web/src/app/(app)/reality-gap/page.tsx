"use client";

import { useEffect, useMemo, useState } from "react";

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
import { getScoreColor, getScoreLabel } from "@/lib/utils/score-colors";

type RealityGapSkill = {
  skill_id: string | null;
  name: string;
  category: string | null;
  in_cv: boolean;
  in_linkedin: boolean;
  rejected: boolean;
  coherence_score: number;
  recommendation: string | null;
};

type RealityGapReport = {
  profile_id: string;
  skills: RealityGapSkill[];
};

const filters = ["all", "technical", "soft", "language", "domain"];

export default function RealityGapPage() {
  const [report, setReport] = useState<RealityGapReport | null>(null);
  const [category, setCategory] = useState("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadReport() {
      try {
        setReport(
          await apiClient<RealityGapReport>("/api/v1/profiles/reality-gap")
        );
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "No se pudo cargar Reality Gap."
        );
      }
    }

    void loadReport();
  }, []);

  const filteredSkills = useMemo(() => {
    const skills = report?.skills ?? [];
    if (category === "all") {
      return skills;
    }
    return skills.filter((skill) => skill.category === category);
  }, [category, report?.skills]);

  if (error) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
        <Card>
          <CardContent className="pt-6 text-sm text-destructive">
            {error}
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:py-8">
      <div className="mb-6">
        <p className="text-sm font-medium text-muted-foreground">Reality Gap</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-normal">
          Coherencia entre CV, LinkedIn y perfil
        </h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Skills por coherencia</CardTitle>
          <CardDescription>
            Las skills con menor score aparecen primero para priorizar mejoras.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-5 flex flex-wrap gap-2">
            {filters.map((filter) => (
              <Button
                key={filter}
                onClick={() => setCategory(filter)}
                type="button"
                variant={category === filter ? "secondary" : "ghost"}
              >
                {filter}
              </Button>
            ))}
          </div>

          <div className="space-y-3">
            {filteredSkills.map((skill) => {
              const color = getScoreColor(skill.coherence_score);
              return (
                <div
                  className="rounded-md border border-border p-4"
                  key={skill.skill_id ?? skill.name}
                >
                  <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
                    <div>
                      <p className="font-medium">{skill.name}</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {skill.category ?? "sin categoría"}
                      </p>
                    </div>
                    <div className="text-right">
                      <p
                        className="text-2xl font-semibold"
                        style={{ color }}
                      >
                        {skill.coherence_score}
                      </p>
                      <p className="text-sm" style={{ color }}>
                        {getScoreLabel(skill.coherence_score)}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <Badge variant={skill.in_cv ? "default" : "outline"}>
                      CV {skill.in_cv ? "✓" : "✗"}
                    </Badge>
                    <Badge variant={skill.in_linkedin ? "default" : "outline"}>
                      LinkedIn {skill.in_linkedin ? "✓" : "✗"}
                    </Badge>
                    <Badge variant={skill.rejected ? "outline" : "default"}>
                      Perfil {skill.rejected ? "rechazada" : "activa"}
                    </Badge>
                  </div>

                  {skill.recommendation ? (
                    <p className="mt-3 text-sm leading-6 text-muted-foreground">
                      {skill.recommendation}
                    </p>
                  ) : null}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
