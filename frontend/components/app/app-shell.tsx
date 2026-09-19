"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Sidebar } from "@/components/app/sidebar";
import { Topbar } from "@/components/app/topbar";
import { MOBILE_NAV, PRIMARY_NAV } from "@/components/app/nav";
import Link from "next/link";

const COLLAPSE_KEY = "codememory.sidebar.collapsed";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = React.useState(false);
  const [mobileOpen, setMobileOpen] = React.useState(false);

  // Restore the collapse preference; localStorage is unavailable during SSR.
  React.useEffect(() => {
    try {
      setCollapsed(window.localStorage.getItem(COLLAPSE_KEY) === "1");
    } catch {
      /* storage unavailable — keep the default */
    }
  }, []);

  const toggleCollapsed = React.useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        window.localStorage.setItem(COLLAPSE_KEY, next ? "1" : "0");
      } catch {
        /* storage unavailable — preference is session-only */
      }
      return next;
    });
  }, []);

  // Close the mobile drawer whenever the route changes.
  React.useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  // Lock background scroll while the drawer is open.
  React.useEffect(() => {
    if (!mobileOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [mobileOpen]);

  const title = React.useMemo(() => {
    const match = PRIMARY_NAV.find(
      (item) => pathname === item.href || pathname.startsWith(`${item.href}/`),
    );
    return match ? (
      <span className="flex items-center gap-2">
        <span className="text-text-faint">CodeMemory</span>
        <span className="text-border-strong" aria-hidden="true">
          /
        </span>
        <span className="text-text-secondary">{match.label}</span>
      </span>
    ) : null;
  }, [pathname]);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-canvas">
      {/* Fixed desktop rail */}
      <aside
        aria-hidden={mobileOpen ? "true" : undefined}
        className={cn(
          "hidden shrink-0 transition-[width] duration-ui ease-standard md:block",
          collapsed ? "w-[56px]" : "w-[240px]",
        )}
      >
        <Sidebar collapsed={collapsed} onToggleCollapsed={toggleCollapsed} />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onOpenSidebar={() => setMobileOpen(true)} title={title} />
        <main
          className="relative flex-1 overflow-y-auto pb-14 md:pb-0"
          tabIndex={-1}
          id="cm-main"
          aria-label="Main content"
        >
          {children}
        </main>
      </div>

      {/* Mobile drawer */}
      {mobileOpen ? (
        <div className="fixed inset-0 z-50 md:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <button
            type="button"
            className="absolute inset-0 bg-black/70"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute left-0 top-0 h-full w-[280px] max-w-[85vw] border-r border-border bg-surface shadow-floating">
            <div className="flex items-center justify-between px-4 h-14 border-b border-border-soft">
              <span className="eyebrow">Navigate</span>
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                className="press inline-flex h-8 w-8 items-center justify-center rounded-md text-text-muted hover:bg-surface-hover hover:text-text-primary"
                aria-label="Close navigation"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
            <div className="h-[calc(100%-3.5rem)]">
              <Sidebar variant="drawer" collapsed={false} onToggleCollapsed={() => {}} onNavigate={() => setMobileOpen(false)} />
            </div>
          </div>
        </div>
      ) : null}

      {/* Mobile bottom navigation */}
      <nav
        aria-label="Primary mobile"
        className={cn(
          "fixed bottom-0 left-0 right-0 z-40 flex border-t border-border bg-surface/95 backdrop-blur-md",
          "h-14 md:hidden",
        )}
      >
        {MOBILE_NAV.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "press flex flex-1 flex-col items-center justify-center gap-1",
                active ? "text-accent" : "text-text-faint",
              )}
              aria-current={active ? "page" : undefined}
            >
              <Icon className="h-[18px] w-[18px]" aria-hidden="true" strokeWidth={1.75} />
              <span className="text-[10px] font-medium leading-none">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
