import * as React from "react";
import { cn } from "@/lib/utils";
import { Surface } from "@/components/ui/surface";

export interface SettingsGroupProps {
  /** Anchor target for the section nav. */
  id: string;
  eyebrow?: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

/**
 * A settings section — heading block plus one grouped surface of rows. Rows are
 * separated by hairline dividers rather than nested cards, because a settings
 * list is one continuous surface, not a grid of cards.
 */
export function SettingsGroup({
  id,
  eyebrow,
  title,
  description,
  children,
  className,
}: SettingsGroupProps) {
  return (
    <section id={id} aria-labelledby={`${id}-heading`} className={cn("scroll-mt-8", className)}>
      <div className="mb-4">
        {eyebrow ? <div className="eyebrow mb-1.5">{eyebrow}</div> : null}
        <h2 id={`${id}-heading`} className="text-heading-md text-text-primary">
          {title}
        </h2>
        {description ? (
          <p className="mt-1.5 max-w-[64ch] text-body-sm text-text-muted">{description}</p>
        ) : null}
      </div>
      <Surface className="divide-y divide-border-soft">{children}</Surface>
    </section>
  );
}
