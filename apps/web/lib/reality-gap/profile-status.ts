import type { RealityGapSkill } from "@/lib/reality-gap/types";

export type RealityGapProfileState = Pick<
  RealityGapSkill,
  "saved" | "confirmed" | "rejected"
>;

export type RealityGapProfileStatus =
  | "rechazada"
  | "activa"
  | "sin confirmar"
  | "no guardada";

// Reality Gap compara las skills guardadas y también las que solo nombra un documento:
// la persona tiene que ver cuáles todavía no revisó y cuáles ni siquiera están en su
// perfil. Una rechazada manda sobre lo demás.
export function getProfileStatus(
  skill: RealityGapProfileState
): RealityGapProfileStatus {
  if (skill.rejected) {
    return "rechazada";
  }
  if (!skill.saved) {
    return "no guardada";
  }
  return skill.confirmed ? "activa" : "sin confirmar";
}
