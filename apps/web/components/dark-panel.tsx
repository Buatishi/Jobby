import { cn } from "@/lib/utils";

type DarkPanelProps = {
  children: React.ReactNode;
  variant?: "glow" | "forest";
  // Suelo de rejilla en perspectiva: solo en paneles amplios.
  floor?: boolean;
  // Decoración que va detrás del contenido (por ejemplo, el radar de Premium).
  backdrop?: React.ReactNode;
  className?: string;
  id?: string;
};

export function DarkPanel({
  children,
  variant = "glow",
  floor = false,
  backdrop,
  className,
  id
}: DarkPanelProps) {
  return (
    <section
      className={cn(
        "relative isolate overflow-hidden rounded-panel text-white",
        variant === "glow" ? "panel-glow" : "panel-forest",
        className
      )}
      id={id}
    >
      {floor ? <div aria-hidden="true" className="grid-floor" /> : null}
      {backdrop}
      <div className="relative z-10">{children}</div>
    </section>
  );
}
