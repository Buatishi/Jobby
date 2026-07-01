"use client";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { CountUp } from "@/components/dashboard/count-up";

const defaultRows = [
  { label: "Skills técnicas", value: 92, color: "bg-[#0F6E56]" },
  { label: "Seniority", value: 84, color: "bg-[#0F6E56]" },
  { label: "ATS", value: 76, color: "bg-[#1D9E75]" },
  { label: "Brechas críticas", value: 18, color: "bg-[#E24B4A]" }
];

type MatchScoreCardProps = {
  className?: string;
  compact?: boolean;
};

export function MatchScoreCard({ className = "", compact = false }: MatchScoreCardProps) {
  return (
    <Card
      className={`rounded-2xl border-black/10 bg-white p-0 shadow-[0_24px_70px_rgba(15,23,42,0.14)] ${className}`}
    >
      <CardHeader className={compact ? "border-b border-black/5 p-4" : "border-b border-black/5 p-7"}>
        <div className="flex items-start justify-between">
          <div>
            <CardDescription className="text-xs font-semibold">
              Match Score
            </CardDescription>
            <CardTitle className={compact ? "mt-1 text-4xl font-black leading-none" : "mt-1 text-6xl font-black leading-none"}>
              <CountUp value={87} />
            </CardTitle>
          </div>
          <Badge className="rounded-full bg-brand-green-light px-3 py-1 text-[11px] font-bold text-brand-green">
            Muy alto
          </Badge>
        </div>
      </CardHeader>
      <CardContent className={compact ? "space-y-3 p-4" : "space-y-5 p-7"}>
        {defaultRows.map((row) => (
          <div className="space-y-1.5" key={row.label}>
            <div className="flex justify-between text-xs font-bold text-black/80">
              <span>{row.label}</span>
              <span>{row.value}%</span>
            </div>
            <div className="h-2.5 overflow-hidden rounded-full bg-[#E8EAED]">
              <div
                className={`h-full rounded-full ${row.color} transition-[width] duration-700`}
                style={{ width: `${row.value}%` }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
