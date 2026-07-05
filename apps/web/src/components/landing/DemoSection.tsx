"use client";

import { useRef, useState } from "react";
import { AnimatePresence, motion, useInView } from "framer-motion";
import { BadgeCheck, FileSearch, MessageSquareText } from "lucide-react";

import { MatchScoreCard } from "@/components/match-score-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useI18n } from "@/lib/i18n/provider";
import { cn } from "@/lib/utils";

type DemoTab = "match" | "ats" | "kit";

const tabs: Array<{ id: DemoTab; label: string }> = [
  { id: "match", label: "Match Score" },
  { id: "ats", label: "ATS Report" },
  { id: "kit", label: "Interview Kit" }
];

const keywordRows = [
  { label: "React", statusKey: "landing.literal", color: "bg-[#0F6E56]" },
  { label: "FastAPI", statusKey: "landing.semantic", color: "bg-[#1D9E75]" },
  { label: "PostgreSQL", statusKey: "landing.literal", color: "bg-[#0F6E56]" },
  { label: "Kubernetes", statusKey: "landing.missing", color: "bg-[#E24B4A]" }
];

function AtsPreview() {
  const { t } = useI18n();

  return (
    <Card className="rounded-2xl border-black/10 bg-white shadow-[0_24px_70px_rgba(15,23,42,0.08)]">
      <CardContent className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold text-black/55">
              {t("landing.sampleData")}
            </p>
            <h3 className="mt-1 text-2xl font-black">ATS Report</h3>
          </div>
          <Badge className="rounded-full bg-brand-green-light text-brand-green">
            76/100
          </Badge>
        </div>
        <div className="mt-6 space-y-3">
          {keywordRows.map((row) => (
            <div
              className="flex items-center justify-between rounded-xl border border-black/5 bg-bg-dashboard px-4 py-3"
              key={row.label}
            >
              <span className="font-semibold">{row.label}</span>
              <span className="flex items-center gap-2 text-xs font-bold text-black/60">
                <span className={cn("h-2.5 w-2.5 rounded-full", row.color)} />
                {t(row.statusKey)}
              </span>
            </div>
          ))}
        </div>
        <div className="mt-5 rounded-xl bg-brand-green-light p-4 text-sm font-semibold text-brand-green">
          {t("landing.atsHint")}
        </div>
      </CardContent>
    </Card>
  );
}

function InterviewKitPreview() {
  const { t } = useI18n();
  const cards = [
    ["landing.kitStrength", "landing.kitStrengthBody"],
    ["landing.kitRisk", "landing.kitRiskBody"],
    ["landing.kitQuestion", "landing.kitQuestionBody"],
    ["landing.kitPlan", "landing.kitPlanBody"]
  ] as const;

  return (
    <Card className="rounded-2xl border-black/10 bg-white shadow-[0_24px_70px_rgba(15,23,42,0.08)]">
      <CardContent className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold text-black/55">
              {t("landing.sampleData")}
            </p>
            <h3 className="mt-1 text-2xl font-black">Interview Kit</h3>
          </div>
          <MessageSquareText className="h-6 w-6 text-brand-green" />
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          {cards.map(([titleKey, bodyKey]) => (
            <div
              className="rounded-xl border border-black/5 bg-bg-dashboard p-4"
              key={titleKey}
            >
              <p className="text-sm font-black">{t(titleKey)}</p>
              <p className="mt-2 text-xs font-medium leading-5 text-black/65">
                {t(bodyKey)}
              </p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function DemoPanel({ activeTab }: { activeTab: DemoTab }) {
  if (activeTab === "ats") {
    return <AtsPreview />;
  }

  if (activeTab === "kit") {
    return <InterviewKitPreview />;
  }

  return <MatchScoreCard compact className="mx-auto max-w-xl" />;
}

export function DemoSection() {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<DemoTab>("match");
  const ref = useRef<HTMLElement>(null);
  const isInView = useInView(ref, { amount: 0.2, once: true });

  return (
    <section className="bg-white px-5 py-20 sm:px-8" id="demo" ref={ref}>
      <motion.div
        animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
        className="mx-auto max-w-6xl"
        initial={{ opacity: 0, y: 20 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
      >
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-bold uppercase tracking-[0.2em] text-brand-green">
            {t("landing.demoEyebrow")}
          </p>
          <h2 className="mt-3 text-3xl font-black tracking-tight text-black md:text-5xl">
            {t("landing.demoTitle")}
          </h2>
          <p className="mt-4 text-base font-medium leading-7 text-black/60">
            {t("landing.demoSubtitle")}
          </p>
        </div>

        <div className="mx-auto mt-8 flex max-w-xl rounded-2xl border border-black/10 bg-bg-dashboard p-1">
          {tabs.map((tab) => (
            <Button
              className={cn(
                "h-10 flex-1 rounded-xl bg-transparent text-xs font-bold text-black/55 shadow-none transition-all duration-200 hover:bg-white hover:text-black",
                activeTab === tab.id && "bg-white text-brand-green shadow-sm"
              )}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              type="button"
              variant="ghost"
            >
              {tab.label}
            </Button>
          ))}
        </div>

        <div className="mx-auto mt-8 max-w-3xl">
          <AnimatePresence mode="wait">
            <motion.div
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              initial={{ opacity: 0 }}
              key={activeTab}
              transition={{ duration: 0.2, ease: "easeOut" }}
            >
              <DemoPanel activeTab={activeTab} />
            </motion.div>
          </AnimatePresence>
        </div>

        <div className="mt-5 flex items-center justify-center gap-2 text-xs font-semibold text-black/50">
          <BadgeCheck className="h-4 w-4 text-brand-green" />
          <span>{t("landing.demoFootnote")}</span>
          <FileSearch className="h-4 w-4 text-brand-green" />
        </div>
      </motion.div>
    </section>
  );
}
