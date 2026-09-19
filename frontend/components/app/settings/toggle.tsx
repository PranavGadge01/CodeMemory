"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface ToggleProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  disabled?: boolean;
  id?: string;
  className?: string;
  "aria-label"?: string;
}

/**
 * Accessible switch. Real button, `role="switch"`, `aria-checked`, and the
 * arrow / home / end keys from the ARIA switch pattern — Space and Enter come
 * for free. The track is 44px wide so the touch target stays usable.
 */
export const Toggle = React.forwardRef<HTMLButtonElement, ToggleProps>(function Toggle(
  { checked, onCheckedChange, disabled, className, ...props },
  ref,
) {
  const handleKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    switch (event.key) {
      case "ArrowLeft":
      case "Home":
        event.preventDefault();
        onCheckedChange(false);
        break;
      case "ArrowRight":
      case "End":
        event.preventDefault();
        onCheckedChange(true);
        break;
      default:
        break;
    }
  };

  return (
    <button
      ref={ref}
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onCheckedChange(!checked)}
      onKeyDown={handleKeyDown}
      className={cn(
        "press relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border",
        "transition-colors duration-micro ease-standard",
        checked ? "border-accent bg-accent" : "border-border bg-surface-card",
        disabled ? "opacity-40" : undefined,
        className,
      )}
      {...props}
    >
      <span
        aria-hidden="true"
        className={cn(
          "pointer-events-none ml-1 h-4 w-4 rounded-full transition-transform duration-micro ease-standard",
          checked ? "translate-x-5 bg-black" : "translate-x-0 bg-text-primary",
        )}
      />
    </button>
  );
});
