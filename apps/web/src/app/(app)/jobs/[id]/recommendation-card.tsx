import { Badge } from "@/components/ui/badge";
import { toRecommendationView, type Recommendation } from "@/lib/jobs/recommendation";
import { cn } from "@/lib/utils";

type RecommendationCardProps = {
  recommendation: Recommendation;
};

export function RecommendationCard({ recommendation }: RecommendationCardProps) {
  const view = toRecommendationView(recommendation);
  if (!view) {
    return null;
  }

  return (
    <div className="rounded-2xl border border-border p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="font-medium">{view.heading}</p>
        <Badge
          className={cn(recommendation.priority === "high" && "border-primary")}
          variant="outline"
        >
          {recommendation.priority ?? "medium"}
        </Badge>
      </div>
      {view.body ? (
        <p className="mt-2 text-sm leading-6 text-muted-foreground">{view.body}</p>
      ) : null}
    </div>
  );
}
