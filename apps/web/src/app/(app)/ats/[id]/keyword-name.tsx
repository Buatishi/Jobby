import { Badge } from "@/components/ui/badge";

/** El nombre de una palabra clave del reporte; las que el aviso presenta como deseables lo dicen. */
export function KeywordName({
  keyword,
  priority
}: {
  keyword: string;
  priority?: "required" | "nice";
}) {
  return (
    <>
      {keyword}
      {priority === "nice" ? (
        <Badge className="ml-2" variant="outline">
          Deseable
        </Badge>
      ) : null}
    </>
  );
}
