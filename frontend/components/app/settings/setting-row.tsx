import * as React from "react";
import { cn } from "@/lib/utils";
import { useDensity } from "./density-context";

export interface SettingRowProps {
  label: React.ReactNode;
  description?: React.ReactNode;
  /** Slot for the control and any state text beside it. Right-aligned on desktop. */
  control?: React.ReactNode;
  /** `htmlFor` of the control, so clicking the label focuses it. */
  htmlFor?: string;
  className?: string;
}

/**
 * One label, one line of description, one control. The atomic unit of every
 * settings section — grouped inside `SettingsGroup`, never free-floating.
 */
export function SettingRow({ label, description, control, htmlFor, className }: SettingRowProps) {
  const density = useDensity();

  return (
    <div
      className={cn(
        "flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-6",
        density === "compact" ? "px-5 py-2.5" : "px-5 py-4",
        className,
      )}
    >
      <div className="min-w-0">
        <label htmlFor={htmlFor} className="text-body-sm font-medium text-text-primary">
          {label}
        </label>
        {description ? (
          <p className="mt-1 max-w-[56ch] text-body-sm text-text-muted">{description}</p>
        ) : null}
      </div>
      {control ? <div className="flex shrink-0 items-center gap-3">{control}</div> : null}
    </div>
  );
}
