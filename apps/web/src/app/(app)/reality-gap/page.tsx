"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { PageBanner } from "@/components/page-banner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { useApiResource } from "@/lib/api/use-api-resource";
import {
  availableFilters,
  filterLabels,
  matchesFilter,
  type RealityGapFilter
} from "@/lib/reality-gap/filters";
import { describeDocuments, getNotices } from "@/lib/reality-gap/notices";
import { getProfileStatus } from "@/lib/reality-gap/profile-status";
import type {
  RealityGapReport,
  RealityGapSkill,
  RealityGapSummary
} from "@/lib/reality-gap/types";
import { getScoreColor, getScoreLabel } from "@/lib/utils/score-colors";

function markLabel(name: string, value: boolean | null): string {
  if (value === null) {
    return `${name} —`;
  }
  return `${name} ${value ? "✓" : "✗"}`;
}

function SummaryCard({ summary }: { summary: RealityGapSummary }) {
  if (summary.score === null) {
    return null;
  }
  const color = getScoreColor(summary.score);
  const counts: [string, number][] = [
    ["En los dos", summary.in_both],
    ["Solo en el CV", summary.only_cv],
    ["Solo en LinkedIn", summary.only_linkedin],
    ["Solo en tu perfil", summary.in_neither]
  ];

  return (
    <Card className="mt-5">
      <CardContent className="flex flex-col gap-5 pt-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-muted-foreground">Coherencia general</p>
          <p className="text-5xl font-semibold italic" style={{ color }}>
            {summary.score}
          </p>
          <p className="text-sm" style={{ color }}>
            {getScoreLabel(summary.score)} · {summary.total} skills comparadas
          </p>
        </div>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-4">
          {counts.map(([label, count]) => (
            <div key={label}>
              <dd className="text-2xl font-semibold italic">{count}</dd>
              <dt className="text-muted-foreground">{label}</dt>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

function SkillRow({ skill }: { skill: RealityGapSkill }) {
  const score = skill.coherence_score;
  const color = score === null ? undefined : getScoreColor(score);
  const status = getProfileStatus(skill);

  return (
    <div className="rounded-2xl border border-border p-4">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <p className="font-medium">{skill.name}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {skill.category ?? "sin categoría"}
          </p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-semibold" style={{ color }}>
            {score ?? "—"}
          </p>
          {score !== null ? (
            <p className="text-sm" style={{ color }}>
              {getScoreLabel(score)}
            </p>
          ) : null}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Badge variant={skill.in_cv ? "default" : "outline"}>
          {markLabel("CV", skill.in_cv)}
        </Badge>
        <Badge variant={skill.in_linkedin ? "default" : "outline"}>
          {markLabel("LinkedIn", skill.in_linkedin)}
        </Badge>
        <Badge variant={status === "activa" ? "default" : "outline"}>
          Perfil {status}
        </Badge>
      </div>

      {skill.recommendation ? (
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          {skill.recommendation}
        </p>
      ) : null}
    </div>
  );
}

export default function RealityGapPage() {
  const {
    data: report,
    error,
    loading
  } = useApiResource<RealityGapReport>(
    "/api/v1/profiles/reality-gap",
    "No se pudo cargar Reality Gap."
  );
  const [selected, setSelected] = useState<RealityGapFilter>("all");

  const filters = useMemo(
    () => availableFilters(report?.skills ?? []),
    [report?.skills]
  );
  // Si después de actualizar el grupo elegido quedó vacío, se vuelve a «Todas».
  const filter = filters.some((item) => item.filter === selected)
    ? selected
    : "all";
  const visibleSkills = useMemo(
    () => (report?.skills ?? []).filter((skill) => matchesFilter(skill, filter)),
    [filter, report?.skills]
  );

  // Si falla la actualización pero hay un reporte anterior, se muestra con el error arriba.
  if (error && !report) {
    return (
      <main className="min-h-screen bg-white p-4 pb-14">
        <Card>
          <CardContent className="pt-6 text-sm text-destructive">
            {error}
          </CardContent>
        </Card>
      </main>
    );
  }

  const notices = report ? getNotices(report) : [];
  const documents = report ? describeDocuments(report) : null;

  return (
    <main className="min-h-screen bg-white p-4 pb-14">
      <PageBanner
        eyebrow="Reality Gap"
        title="Coherencia entre CV, LinkedIn y perfil"
      />

      {error ? <p className="mt-5 text-sm text-destructive">{error}</p> : null}

      {notices.map((notice) => (
        <div
          className="mt-5 flex flex-col gap-3 rounded-2xl border border-brand-line bg-brand-green-light p-4 text-sm sm:flex-row sm:items-center sm:justify-between"
          key={notice.id}
        >
          <p>{notice.text}</p>
          {notice.href && notice.actionLabel ? (
            <Button asChild size="sm" variant="secondary">
              <Link href={notice.href}>{notice.actionLabel}</Link>
            </Button>
          ) : null}
        </div>
      ))}

      {report?.summary.comparable ? (
        <SummaryCard summary={report.summary} />
      ) : null}

      <Card className="mt-5">
        <CardHeader>
          <CardTitle>Skills por coherencia</CardTitle>
          <CardDescription>
            {report?.summary.comparable
              ? "Comparamos las skills de tu perfil con lo que dicen tu CV y el PDF de tu LinkedIn. Las de menor score aparecen primero para priorizar mejoras."
              : "Estas son las skills de tu perfil. Cuando estén tu CV y el PDF de tu LinkedIn, las comparamos y les ponemos un score."}
          </CardDescription>
          {documents ? (
            <p className="text-xs text-muted-foreground">{documents}</p>
          ) : null}
        </CardHeader>
        <CardContent>
          {loading && !report ? (
            <p className="text-sm text-muted-foreground">Cargando…</p>
          ) : null}

          {report && report.skills.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Todavía no hay skills para comparar.
            </p>
          ) : null}

          {filters.length > 1 ? (
            <div className="mb-5 flex flex-wrap gap-2">
              {filters.map((item) => (
                <Button
                  aria-pressed={filter === item.filter}
                  key={item.filter}
                  onClick={() => setSelected(item.filter)}
                  type="button"
                  variant={filter === item.filter ? "secondary" : "ghost"}
                >
                  {filterLabels[item.filter]} ({item.count})
                </Button>
              ))}
            </div>
          ) : null}

          <div className="space-y-3">
            {visibleSkills.map((skill) => (
              <SkillRow
                key={skill.skill_id ?? `unsaved:${skill.name}`}
                skill={skill}
              />
            ))}
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
