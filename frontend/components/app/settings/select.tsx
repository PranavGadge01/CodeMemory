"use client";

import * as React from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps {
  value: string;
  onValueChange: (value: string) => void;
  options: SelectOption[];
  id?: string;
  disabled?: boolean;
  className?: string;
  "aria-label"?: string;
}

/**
 * Native select, restyled. Native is deliberately kept: it is the most
 * keyboard- and screen-reader-friendly way to pick from a short list, and
 * `color-scheme: dark` on <html> makes the open menu match the canvas.
 */
export function Select({
  value,
  onValueChange,
  options,
  className,
  ...props
}: SelectProps) {
  return (
    <div className={cn("relative", className)}>
      <select
        value={value}
        onChange={(event) => onValueChange(event.target.value)}
        className={cn(
          "press h-9 w-full appearance-none rounded-md border border-border bg-surface pl-3 pr-8",
          "text-body-sm text-text-primary",
          "hover:border-border-strong",
          "focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/40",
          "disabled:cursor-not-allowed disabled:opacity-40",
        )}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-muted"
        aria-hidden="true"
      />
    </div>
  );
}
