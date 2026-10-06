import { DarkPanel } from "@/components/dark-panel";

type PageBannerProps = {
  title: string;
  eyebrow?: string;
  description?: string;
  note?: string;
  actions?: React.ReactNode;
  className?: string;
};

// Encabezado de las pantallas internas: el mismo panel oscuro del dashboard.
export function PageBanner({
  title,
  eyebrow,
  description,
  note,
  actions,
  className
}: PageBannerProps) {
  return (
    <DarkPanel className={className} floor>
      <div className="px-6 pb-12 pt-8 sm:px-10 sm:pt-10">
        {eyebrow ? (
          <p className="text-sm font-semibold text-brand-bright">{eyebrow}</p>
        ) : null}
        <h1 className="mt-2 max-w-[28ch] text-[clamp(1.75rem,3.6vw,2.5rem)] font-semibold leading-[1.1] tracking-[-0.025em]">
          {title}
        </h1>
        {description ? (
          <p className="mt-3 max-w-[56ch] text-[15px] font-medium text-neutral-300">
            {description}
          </p>
        ) : null}
        {note ? <p className="mt-2 text-xs font-medium text-neutral-400">{note}</p> : null}
        {actions ? <div className="mt-6 flex flex-wrap gap-3">{actions}</div> : null}
      </div>
    </DarkPanel>
  );
}
