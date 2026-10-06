"use client";

import { useI18n } from "@/lib/i18n/provider";

const roleKeys = Array.from({ length: 12 }, (_, index) => `landing.roles.r${index + 1}`);

export function RolesMarquee() {
  const { t } = useI18n();
  const roles = roleKeys.map((key) => t(key));

  return (
    <section className="mx-auto mt-14 max-w-6xl px-5 text-center sm:px-8">
      <p className="mb-[18px] text-sm font-medium text-neutral-600">{t("landing.marqueeLabel")}</p>
      <div className="overflow-hidden [-webkit-mask-image:linear-gradient(90deg,transparent,#000_10%,#000_90%,transparent)] [mask-image:linear-gradient(90deg,transparent,#000_10%,#000_90%,transparent)]">
        <ul className="flex w-max animate-marquee gap-3 hover:[animation-play-state:paused] motion-reduce:animate-none">
          {[...roles, ...roles].map((role, index) => (
            <li
              aria-hidden={index >= roles.length}
              className="whitespace-nowrap rounded-full border border-brand-line px-[18px] py-2 text-[13px] font-semibold text-neutral-600"
              key={`${role}-${index}`}
            >
              {role}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
