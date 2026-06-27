"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  BriefcaseBusiness,
  Crown,
  FileSearch,
  Gauge,
  Lock,
  MessagesSquare,
  TriangleAlert,
  UserRound
} from "lucide-react";

import type { UserTier } from "@jobmatch/shared-types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type AppSidebarProps = {
  pendingAnalysesCount?: number;
  userTier?: UserTier;
};

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: Gauge },
  { href: "/profile", label: "Mi perfil", icon: UserRound },
  {
    href: "/jobs",
    label: "Jobs analizados",
    icon: BriefcaseBusiness,
    pendingBadge: true
  },
  { href: "/ats", label: "ATS", icon: FileSearch },
  { href: "/reality-gap", label: "Reality Gap", icon: TriangleAlert },
  {
    href: "/interview-kits",
    label: "Interview Kits",
    icon: MessagesSquare,
    lockedForFree: true
  }
];

export function AppSidebar({
  pendingAnalysesCount = 0,
  userTier = "free"
}: AppSidebarProps) {
  const pathname = usePathname();

  return (
    <aside className="flex min-h-screen w-full flex-col border-r border-border bg-background lg:w-72">
      <div className="flex h-16 items-center gap-3 border-b border-border px-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-sm font-bold text-primary-foreground">
          JM
        </div>
        <div>
          <p className="font-semibold leading-none">JobMatch AI</p>
          <p className="mt-1 text-xs text-muted-foreground">Career intelligence</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          const isLocked = item.lockedForFree && userTier === "free";

          return (
            <Link
              className={cn(
                "flex h-11 items-center gap-3 rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                isActive && "bg-muted text-foreground"
              )}
              href={item.href}
              key={item.href}
            >
              <Icon className="h-4 w-4" />
              <span className="flex-1">{item.label}</span>
              {item.pendingBadge && pendingAnalysesCount > 0 ? (
                <Badge>{pendingAnalysesCount}</Badge>
              ) : null}
              {isLocked ? <Lock className="h-4 w-4" /> : null}
            </Link>
          );
        })}
      </nav>

      {userTier === "free" ? (
        <div className="border-t border-border p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-medium">
            <Crown className="h-4 w-4 text-secondary" />
            Premium desbloquea más análisis
          </div>
          <Button asChild className="w-full">
            <Link href="/upgrade">
              <BarChart3 className="mr-2 h-4 w-4" />
              Upgrade a Premium
            </Link>
          </Button>
        </div>
      ) : null}
    </aside>
  );
}
