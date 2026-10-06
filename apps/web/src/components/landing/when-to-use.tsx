"use client";

import { useRef, useState } from "react";
import { ArrowRight } from "lucide-react";

import { ScoreRing } from "@/components/score-ring";
import { useI18n } from "@/lib/i18n/provider";
import { cn } from "@/lib/utils";
import { getScoreColor } from "@/lib/utils/score-colors";
import { SectionHead, StatusPill } from "@/src/components/landing/shared";

const moments = ["apply", "ats", "gap", "kit"] as const;

type Moment = (typeof moments)[number];

function BarRow({ label, percent, value }: { label: string; percent: number; value: string }) {
  return (
    <div className="grid grid-cols-[112px_minmax(0,1fr)_auto] items-center gap-3 text-[13px] font-semibold">
      <span>{label}</span>
      <div className="h-2 overflow-hidden rounded-full bg-brand-mint">
        <div
          className="h-full rounded-full"
          style={{ backgroundColor: getScoreColor(percent), width: `${percent}%` }}
        />
      </div>
      <span>{value}</span>
    </div>
  );
}

function MomentVisual({ moment }: { moment: Moment }) {
  const { t } = useI18n();

  if (moment === "apply") {
    return (
      <>
        <div className="flex items-center gap-3.5">
          <ScoreRing
            className="h-16 w-16"
            color={getScoreColor(78)}
            label={t("landing.when.applyScore")}
            strokeWidth={11}
            trackColor="#CBEADD"
            value={78}
          />
          <div>
            <div className="text-[22px] font-bold">{t("landing.when.applyScore")}</div>
            <div className="text-[13px] font-medium text-neutral-600">{t("landing.when.applyRole")}</div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusPill tone="ok">Python: {t("landing.met")}</StatusPill>
          <StatusPill tone="mid">SQL: {t("landing.partial")}</StatusPill>
          <StatusPill tone="bad">Docker: {t("landing.missing")}</StatusPill>
        </div>
      </>
    );
  }

  if (moment === "ats") {
    return (
      <>
        <BarRow label={t("landing.when.atsKeywords")} percent={66} value={t("landing.when.atsKeywordsValue")} />
        <BarRow label={t("landing.when.atsFormat")} percent={90} value={t("landing.when.atsFormatValue")} />
        <BarRow label={t("landing.when.atsSections")} percent={55} value={t("landing.when.atsSectionsValue")} />
      </>
    );
  }

  if (moment === "gap") {
    return (
      <>
        {(
          [
            ["landing.when.gapRole", "ok", "landing.when.gapRoleValue"],
            ["landing.when.gapDates", "bad", "landing.when.gapDatesValue"],
            ["landing.when.gapSkills", "mid", "landing.when.gapSkillsValue"]
          ] as const
        ).map(([labelKey, tone, valueKey]) => (
          <div className="flex items-center justify-between text-[13px] font-semibold" key={labelKey}>
            <span>{t(labelKey)}</span>
            <StatusPill tone={tone}>{t(valueKey)}</StatusPill>
          </div>
        ))}
      </>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {["landing.when.kitQuestionOne", "landing.when.kitQuestionTwo", "landing.when.kitQuestionThree"].map(
        (key) => (
          <span
            className="rounded-full bg-brand-green-light px-3 py-1 text-xs font-semibold text-brand-green"
            key={key}
          >
            {t(key)}
          </span>
        )
      )}
    </div>
  );
}

// Lista de momentos de uso: el elegido se despliega a la derecha, con flechas del teclado.
export function WhenToUse() {
  const { t } = useI18n();
  const [selected, setSelected] = useState<Moment>("apply");
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  function onKeyDown(event: React.KeyboardEvent, index: number) {
    const last = moments.length - 1;
    const next =
      event.key === "ArrowDown" || event.key === "ArrowRight"
        ? (index + 1) % moments.length
        : event.key === "ArrowUp" || event.key === "ArrowLeft"
          ? (index === 0 ? last : index - 1)
          : null;

    if (next === null) {
      return;
    }

    event.preventDefault();
    setSelected(moments[next] as Moment);
    tabRefs.current[next]?.focus();
  }

  return (
    <section className="mx-auto max-w-6xl px-5 pt-28 sm:px-8" id="cuando">
      <SectionHead
        eyebrow={t("landing.whenEyebrow")}
        subtitle={t("landing.whenSubtitle")}
        title={t("landing.whenTitle")}
      />
      <div className="grid overflow-hidden rounded-card border border-brand-mint bg-white lg:grid-cols-[1fr_1.1fr]">
        <div aria-label={t("landing.whenTitle")} role="tablist">
          {moments.map((moment, index) => {
            const isSelected = moment === selected;

            return (
              <button
                aria-controls="when-panel"
                aria-selected={isSelected}
                className={cn(
                  "flex w-full items-center gap-3.5 border-t border-brand-line px-6 py-[22px] text-left text-[15px] font-semibold transition-colors first:border-t-0 hover:bg-[#F3FBF7]",
                  isSelected && "bg-brand-green-light hover:bg-brand-green-light"
                )}
                id={`when-tab-${moment}`}
                key={moment}
                onClick={() => setSelected(moment)}
                onKeyDown={(event) => onKeyDown(event, index)}
                ref={(element) => {
                  tabRefs.current[index] = element;
                }}
                role="tab"
                tabIndex={isSelected ? 0 : -1}
                type="button"
              >
                <span
                  aria-hidden="true"
                  className={cn(
                    "flex h-[30px] w-[30px] flex-none items-center justify-center rounded-full bg-brand-ink text-white transition-transform",
                    isSelected && "rotate-90 bg-brand-bright text-brand-ink"
                  )}
                >
                  <ArrowRight className="h-[15px] w-[15px]" />
                </span>
                {t(`landing.when.${moment}Tab`)}
              </button>
            );
          })}
        </div>

        <div
          aria-labelledby={`when-tab-${selected}`}
          aria-live="polite"
          className="grid min-h-[300px] content-center gap-4 bg-brand-green-light p-6 md:p-9"
          id="when-panel"
          role="tabpanel"
        >
          <h3 className="text-xl font-semibold tracking-tight">{t(`landing.when.${selected}Title`)}</h3>
          <p className="max-w-[44ch] text-sm font-medium text-neutral-600">{t(`landing.when.${selected}Text`)}</p>
          <div
            aria-label={t("landing.sampleData")}
            className="grid gap-2.5 rounded-2xl bg-white p-4 text-[13px] font-semibold"
          >
            <MomentVisual moment={selected} />
          </div>
        </div>
      </div>
    </section>
  );
}
