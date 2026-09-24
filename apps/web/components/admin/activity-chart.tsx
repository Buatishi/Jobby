"use client";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "@/components/ui/tooltip";
import {
  activityBars,
  type ActivitySeries,
  type DailyActivity,
  formatDay,
  seriesTotal
} from "@/lib/admin/metrics";

type ActivityChartProps = {
  title: string;
  unit: string;
  days: DailyActivity[];
  series: ActivitySeries;
  locale: string;
};

/** Una sola serie por gráfico: el título la nombra, así que no hace falta leyenda. */
export function ActivityChart({
  title,
  unit,
  days,
  series,
  locale
}: ActivityChartProps) {
  const bars = activityBars(days, series);
  const first = bars[0];
  const last = bars[bars.length - 1];

  return (
    <figure className="rounded-2xl border border-neutral-100 bg-white p-4 shadow-[0_8px_30px_rgb(0,0,0,0.02)]">
      <figcaption className="flex items-baseline justify-between gap-3">
        <span className="text-sm font-semibold text-black">{title}</span>
        <span className="text-xs text-muted-foreground">
          {seriesTotal(days, series)} {unit}
        </span>
      </figcaption>

      <TooltipProvider delayDuration={100}>
        <div className="mt-6 flex h-28 items-end gap-[2px] border-b border-neutral-200">
          {bars.map((bar) => {
            const label = `${bar.value} ${unit} · ${formatDay(bar.day, locale)}`;
            return (
              <Tooltip key={bar.day}>
                <TooltipTrigger asChild>
                  {/* El área de la columna entera es el blanco: más grande que la barra. */}
                  <div
                    aria-label={label}
                    className="group relative flex h-full min-w-0 flex-1 items-end justify-center rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-[#007a5e]/40"
                    role="img"
                    tabIndex={0}
                  >
                    {bar.isPeak ? (
                      <span
                        className="absolute left-1/2 -translate-x-1/2 text-[11px] font-semibold text-black/70"
                        style={{ bottom: `calc(${bar.heightPercent}% + 4px)` }}
                      >
                        {bar.value}
                      </span>
                    ) : null}
                    <div
                      className="w-full max-w-6 rounded-t-[4px] bg-[#007a5e] transition-opacity group-hover:opacity-75 group-focus-visible:opacity-75"
                      style={{ height: `${bar.heightPercent}%` }}
                    />
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <span className="font-semibold text-black">{bar.value}</span>{" "}
                  <span className="text-muted-foreground">
                    {unit} · {formatDay(bar.day, locale)}
                  </span>
                </TooltipContent>
              </Tooltip>
            );
          })}
        </div>
      </TooltipProvider>

      {first && last ? (
        <div className="mt-1.5 flex justify-between text-[11px] text-muted-foreground">
          <span>{formatDay(first.day, locale)}</span>
          <span>{formatDay(last.day, locale)}</span>
        </div>
      ) : null}
    </figure>
  );
}
