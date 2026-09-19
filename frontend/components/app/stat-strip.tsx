import { cn } from "@/lib/utils";
import { formatNumber } from "@/lib/format";

/**
 * Stat strip.
 *
 * DESIGN.md §12 is explicit: avoid the four-icon-stat-card grid. So this is a
 * single ruled strip, not a card each — values sit on one baseline and read as
 * a sentence about the user's coding history.
 */
export function StatStrip({
  stats,
  className,
}: {
  stats: Array<{
    label: string;
    value: number | string;
    hint?: string;
    accent?: boolean;
  }>;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "grid grid-cols-2 divide-x divide-border-soft rounded-lg border border-border bg-surface",
        "sm:grid-cols-3 lg:grid-cols-5",
        className,
      )}
    >
      {stats.map((stat) => (
        <div key={stat.label} className="px-4 py-3.5 sm:px-5">
          <div className="eyebrow">{stat.label}</div>
          <div
            className={cn(
              "mt-1.5 font-technical text-text-primary tabular-nums",
              stat.accent && "text-accent",
            )}
          >
            {typeof stat.value === "number" ? formatNumber(stat.value) : stat.value}
          </div>
          {stat.hint ? (
            <div className="mt-1 text-caption text-text-faint">{stat.hint}</div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
