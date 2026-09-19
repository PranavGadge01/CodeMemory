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

function subscribeCollapsed(notify: () => void) {
  window.addEventListener("storage", notify);
  return () => window.removeEventListener("storage", notify);
}

function readCollapsed(): boolean {
  try {
    return window.localStorage.getItem(COLLAPSE_KEY) === "1";
  } catch {
    /* storage unavailable — treat as not collapsed */
    return false;
  }
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  // The collapse preference lives in localStorage, an external store, so it is
  // read through `useSyncExternalStore` rather than a setState-in-effect. The
  // server snapshot is always `false` — localStorage is unavailable during SSR
  // — which also means the first client render matches the server HTML, so the
  // shell hydrates expanded and then settles to the stored preference.
  const storedCollapsed = React.useSyncExternalStore(
    subscribeCollapsed,
    readCollapsed,
    () => false,
  );
  // Session-only override, so the rail still toggles when writing to storage
  // fails (blocked storage, private browsing) instead of freezing in place.
  const [override, setOverride] = React.useState<boolean | null>(null);
  const collapsed = override ?? storedCollapsed;

  const [mobileOpen, setMobileOpen] = React.useState(false);

  // Close the mobile drawer whenever the route changes. Compared against the
  // previous pathname during render — rather than in an effect — so the drawer
  // closes before the new route paints instead of afterwards.
  const [previousPathname, setPreviousPathname] = React.useState(pathname);
  if (pathname !== previousPathname) {
    setPreviousPathname(pathname);
    setMobileOpen(false);
  }

  const toggleCollapsed = React.useCallback(() => {
    setOverride((prev) => {
      const next = !(prev ?? storedCollapsed);
      try {
        window.localStorage.setItem(COLLAPSE_KEY, next ? "1" : "0");
      } catch {
        /* storage unavailable — preference is session-only */
      }
      return next;
    });
  }, [storedCollapsed]);

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
          collapsed ? "w-14" : "w-60",
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
          <div className="absolute left-0 top-0 h-full w-70 max-w-[85vw] border-r border-border bg-surface shadow-floating">
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
              <Icon className="h-4.5 w-4.5" aria-hidden="true" strokeWidth={1.75} />
              <span className="text-[10px] font-medium leading-none">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
