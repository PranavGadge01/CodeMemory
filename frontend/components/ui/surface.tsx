import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Surface — the CodeMemory card.
 *
 * DESIGN.md is explicit that cards should group *meaningful* information and
 * that not every piece of content deserves one. This primitive is deliberately
 * quiet: a single surface step above the canvas plus a hairline border. No
 * shadow, no gradient, no blur.
 */
const Surface = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    /** One step lighter than the default surface. */
    elevated?: boolean;
  }
>(({ className, elevated = false, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-lg border border-border",
      elevated ? "bg-surface-elevated" : "bg-surface",
      className,
    )}
    {...props}
  />
));
Surface.displayName = "Surface";

/**
 * Surface with a header row — eyebrow, title, and an optional action slot.
 * Used across the dashboard and home page so section framing is identical.
 */
const SurfaceHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    eyebrow?: string;
    title: React.ReactNode;
    description?: React.ReactNode;
    action?: React.ReactNode;
  }
>(({ className, eyebrow, title, description, action, children, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "flex items-start justify-between gap-4 border-b border-border-soft px-5 py-4",
      className,
    )}
    {...props}
  >
    <div className="min-w-0">
      {eyebrow ? <div className="eyebrow mb-1.5">{eyebrow}</div> : null}
      <div className="text-heading-sm text-text-primary truncate">{title}</div>
      {description ? (
        <div className="mt-1 text-body-sm text-text-muted">{description}</div>
      ) : null}
    </div>
    {action ? <div className="shrink-0">{action}</div> : null}
    {children}
  </div>
));
SurfaceHeader.displayName = "SurfaceHeader";

export { Surface, SurfaceHeader };
