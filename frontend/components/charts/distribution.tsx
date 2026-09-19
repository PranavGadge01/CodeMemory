import * as React from "react";
import { cn } from "@/lib/utils";
import { formatPercent } from "@/lib/format";

export interface DistributionRow {
  label: string;
  value: number;
  /** Absolute share used for the bar width, when it differs from `value`. */
  share?: number;
  color?: string;
  hint?: string;
}

/**
 * Horizontal distribution — languages, topics, difficulty mix.
 *
 * Chosen over a donut everywhere a precise comparison matters: bars sort
 * naturally and the eye reads length faster than angle.
 */
export function DistributionBars({
  rows,
  className,
  max,
  formatValue = (value) => String(value),
}: {
  rows: DistributionRow[];
  className?: string;
  max?: number;
  formatValue?: (value: number) => string;
}) {
  const ceiling = max ?? Math.max(1, ...rows.map((row) => row.share ?? row.value));

  return (
    <div className={cn("flex flex-col", className)} role="list" aria-label="Distribution">
      {rows.map((row) => {
        const width = Math.min(100, ((row.share ?? row.value) / ceiling) * 100);
        return (
          <div key={row.label} className="group flex items-center gap-3 py-1.5" role="listitem">
            <div className="w-[88px] shrink-0 truncate text-body-sm text-text-secondary" title={row.label}>
              {row.label}
            </div>
            <div className="relative h-2.5 min-w-[40px] flex-1 overflow-hidden rounded-sm bg-surface-card">
              <div
                className="absolute inset-y-0 left-0 rounded-sm transition-[width] duration-meaningful ease-emphasis"
                style={{
                  width: `${width}%`,
                  backgroundColor: row.color ?? "var(--color-accent)",
                }}
              >
                {row.hint ? <title>{row.hint}</title> : null}
              </div>
            </div>
            <div className="w-[52px] shrink-0 text-right font-technical-sm text-text-muted">
              {formatValue(row.value)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function PercentDistributionBars({
  rows,
  className,
}: {
  rows: DistributionRow[];
  className?: string;
}) {
  return <DistributionBars rows={rows} className={className} formatValue={(v) => formatPercent(v)} />;
}
