import { cn } from "@/lib/utils";
import { statusTones, type StatusTone } from "@/lib/utils/score-colors";

export function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-block rounded-full border-[1.5px] border-brand-bright bg-brand-green-light px-3.5 py-1 text-xs font-semibold text-brand-green">
      {children}
    </span>
  );
}

type StatusPillProps = {
  tone: StatusTone;
  surface?: "light" | "dark";
  className?: string;
  children: React.ReactNode;
};

// Píldora de estado ("cumple", "parcial", "falta"): los colores viven en score-colors.ts.
export function StatusPill({
  tone,
  surface = "light",
  className,
  children
}: StatusPillProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center whitespace-nowrap rounded-full px-3 py-1 text-xs font-bold",
        className
      )}
      style={statusTones[surface][tone]}
    >
      {children}
    </span>
  );
}

export function SectionHead({
  eyebrow,
  title,
  subtitle
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="mx-auto mb-12 grid max-w-2xl justify-items-center gap-4 text-center">
      <Eyebrow>{eyebrow}</Eyebrow>
      <h2 className="text-[clamp(1.75rem,3.4vw,2.5rem)] font-semibold leading-[1.12] tracking-[-0.02em]">
        {title}
      </h2>
      {subtitle ? (
        <p className="max-w-[50ch] text-[15px] font-medium text-neutral-600">{subtitle}</p>
      ) : null}
    </div>
  );
}

export function PillRow({
  strong,
  children
}: {
  strong: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3.5 rounded-full bg-brand-green-light py-2.5 pl-2.5 pr-5 text-sm font-medium">
      <span
        aria-hidden="true"
        className="flex h-[30px] w-[30px] flex-none items-center justify-center rounded-full bg-brand-ink text-white"
      >
        <svg fill="none" height="15" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="15">
          <path d="M5 12h14M13 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
      <span>
        <strong className="font-bold text-brand-green">{strong}</strong> {children}
      </span>
    </div>
  );
}
