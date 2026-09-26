"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { getHealth } from "@/lib/api";
import type { HealthDTO } from "@/lib/api/types";
import { PRIMARY_NAV, SECONDARY_NAV, type NavItem } from "@/components/app/nav";
import { Wordmark, WordmarkCollapsed } from "@/components/system/logo";

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapsed: () => void;
  /** When true the sidebar renders as the contents of a mobile drawer. */
  variant?: "fixed" | "drawer";
  onNavigate?: () => void;
}

export function Sidebar({
  collapsed,
  onToggleCollapsed,
  variant = "fixed",
  onNavigate,
}: SidebarProps) {
  const pathname = usePathname();

  return (
    <div
      className={cn(
        "flex h-full flex-col bg-surface",
        variant === "fixed" ? "border-r border-border" : "",
      )}
    >
      {/* Brand */}
      <div className={cn("flex h-14 items-center", collapsed ? "justify-center px-0" : "px-4")}>
        {collapsed ? (
          <Link href="/dashboard" aria-label="CodeMemory — go to overview">
            <WordmarkCollapsed />
          </Link>
        ) : (
          <Link href="/dashboard" className="block" onClick={onNavigate}>
            <Wordmark />
          </Link>
        )}
      </div>

      <div className="mx-3 h-px bg-border-soft" />

      <nav
        aria-label="Primary"
        className={cn("flex flex-1 flex-col gap-0.5 overflow-y-auto py-3", collapsed ? "px-2" : "px-3")}
      >
        <div className={cn("mb-1.5", collapsed ? "hidden" : "block")}>
          <span className="eyebrow px-2">Workspace</span>
        </div>
        {PRIMARY_NAV.map((item) => (
          <NavRow
            key={item.href}
            item={item}
            active={isActive(pathname, item.href)}
            collapsed={collapsed}
            onNavigate={onNavigate}
          />
        ))}

        <div className={cn("mt-5 mb-1.5", collapsed ? "hidden" : "block")}>
          <span className="eyebrow px-2">System</span>
        </div>
        {SECONDARY_NAV.map((item) => (
          <NavRow
            key={item.href}
            item={item}
            active={isActive(pathname, item.href)}
            collapsed={collapsed}
            onNavigate={onNavigate}
          />
        ))}

        {collapsed ? (
          <div className="mt-5 h-px bg-border-soft" />
        ) : (
          <div className="mt-5 mb-1.5">
            <span className="eyebrow px-2">Memory</span>
          </div>
        )}

        {collapsed ? null : <MemoryStatus />}
      </nav>

      {/* Collapse control */}
      {variant === "fixed" ? (
        <div className={cn("border-t border-border-soft p-3", collapsed ? "flex justify-center" : "")}>
          <button
            type="button"
            onClick={onToggleCollapsed}
            className={cn(
              "press inline-flex h-8 items-center gap-2 rounded-md text-text-muted",
              "hover:bg-surface-hover hover:text-text-primary",
              collapsed ? "w-8 justify-center" : "px-2 text-body-sm",
            )}
            aria-expanded={!collapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <PanelLeftOpen className="h-4 w-4" aria-hidden="true" />
            ) : (
              <>
                <PanelLeftClose className="h-4 w-4" aria-hidden="true" />
                <span>Collapse</span>
              </>
            )}
          </button>
        </div>
      ) : null}
    </div>
  );
}

function NavRow({
  item,
  active,
  collapsed,
  onNavigate,
}: {
  item: NavItem;
  active: boolean;
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  const Icon = item.icon;

  if (collapsed) {
    return (
      <Link
        href={item.href}
        onClick={onNavigate}
        title={item.label}
        aria-label={item.label}
        aria-current={active ? "page" : undefined}
        className={cn(
          "press group relative flex h-9 w-full items-center justify-center rounded-md",
          active
            ? "bg-surface-active text-text-primary"
            : "text-text-muted hover:bg-surface-hover hover:text-text-primary",
        )}
      >
        {active ? (
          <span
            aria-hidden="true"
            className="absolute -left-2 top-1/2 h-4 w-[2px] -translate-y-1/2 rounded-full bg-accent"
          />
        ) : null}
        <Icon className="h-[18px] w-[18px]" aria-hidden="true" strokeWidth={1.75} />
      </Link>
    );
  }

  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      className={cn(
        "press group relative flex h-9 items-center gap-2.5 rounded-md px-2 text-body-sm",
        active
          ? "bg-surface-active text-text-primary"
          : "text-text-secondary hover:bg-surface-hover hover:text-text-primary",
      )}
    >
      {active ? (
        <span
          aria-hidden="true"
          className="absolute -left-3 top-1/2 h-4 w-[2px] -translate-y-1/2 rounded-full bg-accent"
        />
      ) : null}
      <Icon
        className={cn("h-[17px] w-[17px] shrink-0", active ? "text-accent" : "text-text-muted")}
        aria-hidden="true"
        strokeWidth={1.75}
      />
      <span className="truncate">{item.label}</span>
    </Link>
  );
}

function MemoryStatus() {
  const [health, setHealth] = React.useState<HealthDTO | null>(null);
  const [checked, setChecked] = React.useState(false);

  React.useEffect(() => {
    let active = true;
    void getHealth()
      .then((result) => {
        if (active) setHealth(result);
      })
      .catch(() => {
        if (active) setHealth(null);
      })
      .finally(() => {
        if (active) setChecked(true);
      });

    return () => {
      active = false;
    };
  }, []);

  const healthy = health?.storage.status === "ok";

  return (
    <div className="rounded-md border border-border-soft bg-surface-elevated px-3 py-3">
      <div className="flex items-center justify-between">
        <span className="eyebrow">Index</span>
        <span className={cn("inline-flex items-center gap-1.5 font-technical-sm", healthy ? "text-success" : "text-text-muted")} role="status">
          <span className={cn("h-1.5 w-1.5 rounded-full", healthy ? "bg-success" : "bg-text-disabled")} aria-hidden="true" />
          {!checked ? "Checking" : health ? health.storage.status : "Unavailable"}
        </span>
      </div>
      <div className="mt-2 font-technical-sm text-text-muted">
        {health ? `${health.storage.problems} problems` : checked ? "Index details unavailable" : "Loading index details…"}
      </div>
      <div className="mt-2 flex items-center justify-between text-[11px] text-text-faint">
        <span>Health check</span>
        <span className="font-technical-sm">
          {health ? new Date(health.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}
        </span>
      </div>
    </div>
  );
}

function isActive(pathname: string | null, href: string): boolean {
  if (!pathname) return false;
  if (href === "/dashboard") return pathname === "/dashboard";
  return pathname === href || pathname.startsWith(`${href}/`);
}

