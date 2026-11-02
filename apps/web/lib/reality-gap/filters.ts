import type { RealityGapSkill } from "@/lib/reality-gap/types";

export type RealityGapFilter =
  | "all"
  | "both"
  | "only_cv"
  | "only_linkedin"
  | "unconfirmed";

export const filterLabels: Record<RealityGapFilter, string> = {
  all: "Todas",
  both: "En los dos",
  only_cv: "Solo en el CV",
  only_linkedin: "Solo en LinkedIn",
  unconfirmed: "Sin confirmar"
};

const filterOrder: RealityGapFilter[] = [
  "all",
  "both",
  "only_cv",
  "only_linkedin",
  "unconfirmed"
];

type FilterableSkill = Pick<
  RealityGapSkill,
  "in_cv" | "in_linkedin" | "saved" | "confirmed"
>;

export function matchesFilter(
  skill: FilterableSkill,
  filter: RealityGapFilter
): boolean {
  switch (filter) {
    case "all":
      return true;
    case "both":
      return skill.in_cv === true && skill.in_linkedin === true;
    case "only_cv":
      return skill.in_cv === true && skill.in_linkedin === false;
    case "only_linkedin":
      return skill.in_cv === false && skill.in_linkedin === true;
    case "unconfirmed":
      return skill.saved && !skill.confirmed;
  }
}

export type AvailableFilter = { filter: RealityGapFilter; count: number };

// Solo los filtros que tienen algo para mostrar, con «Todas» siempre.
export function availableFilters(skills: FilterableSkill[]): AvailableFilter[] {
  return filterOrder
    .map((filter) => ({
      filter,
      count: skills.filter((skill) => matchesFilter(skill, filter)).length
    }))
    .filter(({ filter, count }) => filter === "all" || count > 0);
}
