"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  BarChart3,
  BriefcaseBusiness,
  Crown,
  FileSearch,
  Gauge,
  Lock,
  LogOut,
  Menu,
  MessagesSquare,
  ShieldCheck,
  TriangleAlert,
  UserRound,
  X,
  type LucideIcon
} from "lucide-react";

import { LanguageToggle } from "@/components/language-toggle";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { hasPermission, Permission, planOf } from "@/lib/auth/permissions";
import { signOutAndLeave } from "@/lib/auth/sign-out";
import { useCurrentUser } from "@/lib/auth/use-current-user";
import { useI18n } from "@/lib/i18n/provider";
import { cn } from "@/lib/utils";

type AppSidebarProps = {
  pendingAnalysesCount?: number;
  userName?: string;
};

type NavItem = {
  href: string;
  labelKey: string;
  icon: LucideIcon;
  pendingBadge?: boolean;
  lockedForFree?: boolean;
};

const navItems: NavItem[] = [
  { href: "/dashboard", labelKey: "common.dashboard", icon: Gauge },
  { href: "/profile", labelKey: "common.profile", icon: UserRound },
  {
    href: "/jobs",
    labelKey: "common.jobs",
    icon: BriefcaseBusiness,
    pendingBadge: true
  },
  { href: "/ats", labelKey: "common.ats", icon: FileSearch },
  { href: "/reality-gap", labelKey: "common.realityGap", icon: TriangleAlert },
  {
    href: "/interview-kits",
    labelKey: "common.interviewKits",
    icon: MessagesSquare,
    lockedForFree: true
  }
];

// Solo aparece si la API informa el permiso; la API igual lo vuelve a verificar (403).
const adminNavItem: NavItem = {
  href: "/admin",
  labelKey: "common.admin",
  icon: ShieldCheck
};

function SidebarContent({
  pendingAnalysesCount,
  userName,
  onNavigate
}: AppSidebarProps & { onNavigate?: () => void }) {
  const { t } = useI18n();
  const pathname = usePathname();
  const profile = useCurrentUser();
  const plan = planOf(profile);
  const [isSigningOut, setIsSigningOut] = useState(false);
  const [signOutError, setSignOutError] = useState<string | null>(null);

  async function handleSignOut() {
    setSignOutError(null);
    setIsSigningOut(true);
    if (!(await signOutAndLeave())) {
      setIsSigningOut(false);
      setSignOutError(t("auth.signOutFailed"));
    }
  }
  const items = hasPermission(profile, Permission.MetricsRead)
    ? [...navItems, adminNavItem]
    : navItems;

  return (
    <div className="flex h-full min-h-0 flex-col bg-white">
      <div className="px-4 pb-5 pt-6">
        <div className="flex items-start justify-between gap-3">
          <Link className="flex items-center gap-3" href="/dashboard">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-bright text-lg font-bold text-brand-ink">
              J
            </div>
            <div>
              <p className="text-[22px] font-bold leading-none tracking-tight">Jobby</p>
              <p className="mt-1 text-xs font-medium text-muted-foreground">
                {t("app.careerIntelligence")}
              </p>
            </div>
          </Link>
          <LanguageToggle compact />
        </div>
        {userName ? (
          <div className="mt-5 rounded-2xl border border-brand-line bg-white px-4 py-2.5">
            <p className="truncate text-xs text-muted-foreground">
              {t("app.activeSession")}
            </p>
            <p className="truncate text-sm font-bold text-black">{userName}</p>
          </div>
        ) : null}
      </div>

      <div className="h-px bg-neutral-100" />

      <nav className="min-h-0 flex-1 space-y-1.5 overflow-y-auto px-3 py-5">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          const isLocked = item.lockedForFree && plan === "free";

          return (
            <Link
              className={cn(
                "flex h-11 items-center gap-3 rounded-full px-4 text-sm font-semibold text-black/70 transition-colors hover:bg-brand-green-light hover:text-brand-green",
                isActive &&
                  "bg-brand-green-light text-brand-green hover:bg-brand-green-light hover:text-brand-green"
              )}
              href={item.href}
              key={item.href}
              onClick={onNavigate}
            >
              <Icon className="h-4 w-4 flex-none" />
              <span className="min-w-0 flex-1 truncate">{t(item.labelKey)}</span>
              {item.pendingBadge && pendingAnalysesCount ? (
                <Badge className="bg-brand-ink px-2 text-white">
                  {pendingAnalysesCount}
                </Badge>
              ) : null}
              {isLocked ? <Lock className="h-4 w-4 flex-none text-black/55" /> : null}
            </Link>
          );
        })}
      </nav>

      {plan === "free" ? (
        <div className="border-t border-brand-line p-4">
          <div className="rounded-card bg-brand-green-light p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-bold text-brand-green">
              <Crown className="h-4 w-4" />
              {t("common.upgrade")}
            </div>
            <p className="mb-3 text-xs font-medium leading-5 text-black/60">
              {t("app.upgradeText")}
            </p>
            <Button asChild className="h-9 w-full">
              <Link href="/pricing" onClick={onNavigate}>
                <BarChart3 className="mr-2 h-4 w-4" />
                {t("common.upgrade")}
              </Link>
            </Button>
          </div>
        </div>
      ) : null}

      <div className="border-t border-brand-line p-3">
        <button
          className="flex h-11 w-full items-center gap-3 rounded-full px-4 text-sm font-semibold text-black/70 transition-colors hover:bg-neutral-100 hover:text-black disabled:opacity-60"
          disabled={isSigningOut}
          onClick={handleSignOut}
          type="button"
        >
          <LogOut className="h-4 w-4 flex-none" />
          {isSigningOut ? t("auth.signingOut") : t("auth.signOut")}
        </button>
        {signOutError ? (
          <p className="mt-1 px-3 text-xs font-medium text-destructive" role="alert">
            {signOutError}
          </p>
        ) : null}
      </div>
    </div>
  );
}

export function AppSidebar({
  pendingAnalysesCount = 0,
  userName
}: AppSidebarProps) {
  const { t } = useI18n();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <div className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-brand-line bg-white/95 px-4 backdrop-blur lg:hidden">
        <Link className="font-bold" href="/dashboard">
          Jobby
        </Link>
        <div className="flex items-center gap-2">
          <LanguageToggle compact />
          <button
            aria-label={t("common.openMenu")}
            className="inline-flex h-9 w-9 items-center justify-center rounded-full hover:bg-brand-green-light"
            onClick={() => setIsOpen(true)}
            type="button"
          >
            <Menu className="h-5 w-5" />
          </button>
        </div>
      </div>

      <aside className="sticky top-0 hidden h-screen w-60 border-r border-brand-line bg-white lg:block">
        <SidebarContent
          pendingAnalysesCount={pendingAnalysesCount}
          userName={userName}
        />
      </aside>

      {isOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            aria-label={t("common.closeMenu")}
            className="absolute inset-0 bg-black/30"
            onClick={() => setIsOpen(false)}
            type="button"
          />
          <aside className="relative h-full w-72 max-w-[86vw] border-r border-brand-line bg-white shadow-xl">
            <button
              aria-label={t("common.closeMenu")}
              className="absolute right-3 top-3 z-10 inline-flex h-8 w-8 items-center justify-center rounded-full hover:bg-brand-green-light"
              onClick={() => setIsOpen(false)}
              type="button"
            >
              <X className="h-4 w-4" />
            </button>
            <SidebarContent
              onNavigate={() => setIsOpen(false)}
              pendingAnalysesCount={pendingAnalysesCount}
              userName={userName}
            />
          </aside>
        </div>
      ) : null}
    </>
  );
}
