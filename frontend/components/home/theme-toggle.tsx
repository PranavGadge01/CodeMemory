"use client";

import { Moon, Sun } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "@/components/system/theme";

/**
 * Icon-only theme switch for the site navbar. Dark is the default
 * CodeMemory experience. Both icons are rendered and the visible one is
 * chosen by the `<html>` class in `globals.css`, so the control needs no
 * client state and never flashes the wrong icon.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const { toggle } = useTheme();

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label="Toggle theme"
      title="Toggle theme"
      className={cn(
        "press inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-text-muted hover:bg-surface-hover hover:text-text-primary",
        className,
      )}
    >
      <Sun className="theme-icon-dark h-4 w-4" aria-hidden="true" />
      <Moon className="theme-icon-light h-4 w-4" aria-hidden="true" />
    </button>
  );
}
