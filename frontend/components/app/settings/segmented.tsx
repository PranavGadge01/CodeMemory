"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface SegmentedOption {
  value: string;
  label: string;
}

export interface SegmentedProps {
  value: string;
  onValueChange: (value: string) => void;
  options: SegmentedOption[];
  id?: string;
  className?: string;
  "aria-label"?: string;
}

/**
 * Two- or three-way choice where a select would be heavier than the decision
 * warrants. Renders as a single group to assistive tech.
 */
export function Segmented({ value, onValueChange, options, className, ...props }: SegmentedProps) {
  return (
    <div
      role="group"
      className={cn(
        "press inline-flex items-center rounded-md border border-border bg-surface p-0.5",
        className,
      )}
      {...props}
    >
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            onClick={() => onValueChange(option.value)}
            className={cn(
              "press h-8 rounded-sm px-3 text-body-sm font-medium",
              active
                ? "bg-surface-active text-text-primary"
                : "text-text-muted hover:bg-surface-hover hover:text-text-primary",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
