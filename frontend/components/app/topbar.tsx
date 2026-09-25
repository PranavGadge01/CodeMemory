"use client";

import * as React from "react";
import { Search, Plus, Menu } from "lucide-react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { Kbd } from "@/components/ui/primitives";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/system/theme-toggle";

interface TopbarProps {
  onOpenSidebar: () => void;
  /** Rendered title slot, usually the page breadcrumb. */
  title?: React.ReactNode;
}

export function Topbar({ onOpenSidebar, title }: TopbarProps) {
  const router = useRouter();

  React.useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        router.push("/search");
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [router]);

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-canvas/85 px-4 backdrop-blur-md md:px-6">
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="md:hidden"
        onClick={onOpenSidebar}
        aria-label="Open navigation"
      >
        <Menu className="h-[18px] w-[18px]" aria-hidden="true" />
      </Button>

      {title ? (
        <div className="min-w-0 flex-1 truncate text-body-sm text-text-muted">{title}</div>
      ) : (
        <div className="flex-1" />
      )}

      {/* Command palette trigger — opens the global search page. */}
      <button
        type="button"
        onClick={() => router.push("/search")}
        className={cn(
          "group hidden h-8 items-center gap-2 rounded-md border border-border bg-surface px-2.5 text-body-sm text-text-faint",
          "transition-colors duration-micro ease-standard hover:border-border-strong hover:text-text-muted",
          "sm:flex",
        )}
        aria-label="Search memory (⌘K)"
      >
        <Search className="h-4 w-4" aria-hidden="true" />
        <span className="mr-1">Search memory</span>
        <span className="flex items-center gap-1">
          <Kbd>⌘</Kbd>
          <Kbd>K</Kbd>
        </span>
      </button>

      {/* The same icon-only switch the site navbar uses — one theme system,
          rendered once here rather than per page. Always visible: on narrow
          screens it is the only theme control in the app shell. */}
      <ThemeToggle />

      <Button type="button" variant="outline" size="icon" aria-label="Import data" className="hidden sm:inline-flex">
        <Plus className="h-4 w-4" aria-hidden="true" />
      </Button>
    </header>
  );
}
