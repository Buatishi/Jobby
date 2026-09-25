import Link from "next/link";
import type { UserTier } from "@jobmatch/shared-types";

import { Button } from "@/components/ui/button";

type InterviewPrepLinkProps = {
  plan: UserTier | null;
};

/** Los kits de entrevista son premium: al plan free, o mientras el plan carga, no se ofrecen. */
export function InterviewPrepLink({ plan }: InterviewPrepLinkProps) {
  if (plan !== "premium") {
    return null;
  }
  return (
    <Button asChild className="mt-6 w-full">
      <Link href="/interview-kits/new">Preparar entrevista para este puesto</Link>
    </Button>
  );
}
