"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";

import { DarkPanel } from "@/components/dark-panel";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n/provider";
import {
  NETWORK_CENTER,
  NETWORK_VIEWBOX,
  NODE_RING_RADIUS,
  arcPath,
  networkNodes,
  ringDash
} from "@/lib/landing/job-network";
import { getScoreColorOnDark } from "@/lib/utils/score-colors";

// Tu CV en el centro, conectado con cada puesto y su puntaje de match (datos de ejemplo).
export function JobNetwork() {
  const { t } = useI18n();
  const reduceMotion = useReducedMotion();
  const scores = networkNodes.map((node) => node.score).join(", ");
  const viewport = { once: true, amount: 0.35 };

  return (
    <DarkPanel className="mx-4 mt-28" floor id="red">
      <div className="px-4 pb-24 pt-20 text-center sm:px-6 md:pb-32">
        <h2 className="mx-auto max-w-[18ch] text-[clamp(1.875rem,4vw,3rem)] font-semibold leading-[1.08] tracking-[-0.025em]">
          {t("landing.networkTitle")}
        </h2>
        <p className="mx-auto mt-4 max-w-[46ch] text-base font-medium text-neutral-300">
          {t("landing.networkSubtitle")}
        </p>
        <Button asChild className="mt-7" size="lg">
          <Link href="/register">{t("landing.heroCta")}</Link>
        </Button>

        <svg
          aria-label={t("landing.networkAria", { scores })}
          className="mx-auto mt-10 block w-full max-w-[980px] overflow-visible"
          role="img"
          viewBox={`0 0 ${NETWORK_VIEWBOX.width} ${NETWORK_VIEWBOX.height}`}
        >
          {networkNodes.map((node, index) => (
            <motion.path
              d={arcPath(node)}
              fill="none"
              initial={reduceMotion ? false : { pathLength: 0 }}
              key={`arc-${node.id}`}
              stroke={getScoreColorOnDark(node.score)}
              strokeLinecap="round"
              strokeOpacity={0.7}
              strokeWidth={1.6}
              transition={{ delay: index * 0.12, duration: 1.1, ease: [0.2, 0.7, 0.2, 1] }}
              viewport={viewport}
              whileInView={{ pathLength: 1 }}
            />
          ))}

          {networkNodes.map((node, index) => {
            const color = getScoreColorOnDark(node.score);

            return (
              <motion.g
                initial={reduceMotion ? false : { opacity: 0 }}
                key={node.id}
                transition={{ delay: 0.5 + index * 0.12, duration: 0.5 }}
                viewport={viewport}
                whileInView={{ opacity: 1 }}
              >
                <circle cx={node.x} cy={node.y} fill="#12302A" r={38} stroke="#1E3A32" />
                <circle
                  cx={node.x}
                  cy={node.y}
                  fill="none"
                  r={NODE_RING_RADIUS}
                  stroke="#2A4A41"
                  strokeWidth={5}
                />
                <circle
                  cx={node.x}
                  cy={node.y}
                  fill="none"
                  r={NODE_RING_RADIUS}
                  stroke={color}
                  strokeDasharray={ringDash(node.score)}
                  strokeLinecap="round"
                  strokeWidth={5}
                  transform={`rotate(-90 ${node.x} ${node.y})`}
                />
                <text
                  dominantBaseline="central"
                  fill="#FFFFFF"
                  fontSize={17}
                  fontWeight={600}
                  textAnchor="middle"
                  x={node.x}
                  y={node.y}
                >
                  {node.score}
                </text>
                <text
                  className="max-md:hidden"
                  fill="#BDBDB5"
                  fontSize={12}
                  fontWeight={500}
                  textAnchor="middle"
                  x={node.x}
                  y={node.y - 52}
                >
                  {node.label}
                </text>
              </motion.g>
            );
          })}

          <rect
            fill="#FFFFFF"
            height={76}
            rx={20}
            width={76}
            x={NETWORK_CENTER.x - 38}
            y={NETWORK_CENTER.y - 38}
          />
          <text
            dominantBaseline="central"
            fill="#1D1D1B"
            fontSize={22}
            fontWeight={700}
            textAnchor="middle"
            x={NETWORK_CENTER.x}
            y={NETWORK_CENTER.y}
          >
            CV
          </text>
          <text
            fill="#BDBDB5"
            fontSize={12}
            fontWeight={500}
            textAnchor="middle"
            x={NETWORK_CENTER.x}
            y={NETWORK_CENTER.y + 62}
          >
            {t("landing.networkYourCv")}
          </text>
        </svg>
        <ul className="mx-auto mt-6 grid max-w-xs gap-2 md:hidden">
          {networkNodes.map((node) => (
            <li
              className="flex items-center justify-between rounded-full bg-white/5 px-4 py-2 text-sm font-medium"
              key={node.id}
            >
              <span>{node.label}</span>
              <span className="font-semibold" style={{ color: getScoreColorOnDark(node.score) }}>
                {node.score}
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs font-medium text-neutral-400">{t("landing.sampleData")}</p>
      </div>
    </DarkPanel>
  );
}
