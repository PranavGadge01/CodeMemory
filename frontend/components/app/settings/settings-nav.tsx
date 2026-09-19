"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface SettingsNavSection {
  id: string;
  label: string;
}

export interface SettingsNavProps {
  sections: SettingsNavSection[];
  /**
   * The CodeMemory orange is an identity accent, not a default — this lets the
   * "accent emphasis" preference turn it off for selected navigation.
   */
  accent?: boolean;
  className?: string;
}

/**
 * Section nav with scroll-spy. Plain anchors rather than next/link: these are
 * same-page fragment links, where the browser's own anchor scroll (including
 * `prefers-reduced-motion: reduce` → instant jump) is the correct behaviour.
 *
 * The scroll root is the app shell's `<main>` rather than the window, so the
 * observer is rooted on `#cm-main` when it exists.
 */
export function SettingsNav({ sections, accent = true, className }: SettingsNavProps) {
  const [active, setActive] = React.useState<string>(sections[0]?.id ?? "");

  React.useEffect(() => {
    const root = document.getElementById("cm-main");
    const elements = sections
      .map((section) => document.getElementById(section.id))
      .filter((element): element is HTMLElement => element !== null);

    if (elements.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) {
          setActive(visible[0].target.id);
        }
      },
      { root, rootMargin: "-72px 0px -60% 0px", threshold: 0 },
    );

    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, [sections]);

  return (
    <nav aria-label="Settings sections" className={cn("flex flex-col gap-0.5", className)}>
      {sections.map((section) => {
        const isActive = section.id === active;
        return (
          <a
            key={section.id}
            href={`#${section.id}`}
            aria-current={isActive ? "location" : undefined}
            className={cn(
              "press relative flex h-9 items-center rounded-md px-3 text-body-sm",
              isActive
                ? accent
                  ? "bg-surface-active text-text-primary"
                  : "bg-surface-hover text-text-primary"
                : "text-text-muted hover:bg-surface-hover hover:text-text-primary",
            )}
          >
            {isActive ? (
              <span
                aria-hidden="true"
                className={cn(
                  "absolute -left-3 top-1/2 h-4 w-[2px] -translate-y-1/2 rounded-full",
                  accent ? "bg-accent" : "bg-border-strong",
                )}
              />
            ) : null}
            {section.label}
          </a>
        );
      })}
    </nav>
  );
}
