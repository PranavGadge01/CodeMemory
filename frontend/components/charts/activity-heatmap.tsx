import * as React from "react";
import { cn } from "@/lib/utils";
import type { ActivityDay } from "@/lib/types";
import { formatNumber } from "@/lib/format";

/**
 * Solving activity heatmap.
 *
 * The CodeMemory "memory trace": each cell is one day, and the cell's weight
 * is how much of that day was spent submitting. Weeks run down the columns so
 * the grid reads as a vertical timeline of the user's coding history.
 */
export function ActivityHeatmap({
  days,
  className,
  cellSize = 11,
  gap = 3,
  max: maxProp,
}: {
  days: ActivityDay[];
  className?: string;
  cellSize?: number;
  gap?: number;
  max?: number;
}) {
  const max = maxProp ?? Math.max(1, ...days.map((day) => day.submissions));

  // Pad the leading days so every column is a full week.
  const firstDate = new Date(days[0]?.date ?? 0);
  const leadingBlanks = (firstDate.getDay() + 6) % 7;
  const columns = Math.ceil((days.length + leadingBlanks) / 7);
  const weekLabels = monthLabels(days);

  const width = columns * (cellSize + gap);
  const height = 7 * (cellSize + gap);

  return (
    <div className={cn("flex gap-3", className)}>
      <div className="flex flex-col justify-between gap-1 pt-[14px] pb-1">
        {["Mon", "Wed", "Fri"].map((label) => (
          <span key={label} className="font-technical-sm text-text-faint">
            {label}
          </span>
        ))}
      </div>
      <div className="min-w-0 flex-1 overflow-x-auto">
        <svg
          className="block h-auto w-full min-w-max"
          viewBox={`0 0 ${width} ${height + 14}`}
          role="img"
          aria-label={`Solving activity over ${days.length} days. Peak ${max} submissions in a day.`}
        >
          {days.map((day, index) => {
            const position = index + leadingBlanks;
            const column = Math.floor(position / 7);
            const row = position % 7;
            const x = column * (cellSize + gap);
            const y = row * (cellSize + gap);
            return (
              <rect
                key={day.date}
                x={x}
                y={y}
                width={cellSize}
                height={cellSize}
                rx={2}
                fill={cellFill(day.submissions, max)}
              >
                <title>
                  {`${day.date} — ${formatNumber(day.submissions)} submission${day.submissions === 1 ? "" : "s"}, ${day.accepted} accepted`}
                </title>
              </rect>
            );
          })}
          {weekLabels.map((label) => (
            <text
              key={label.key}
              x={label.column * (cellSize + gap)}
              y={height + 10}
              className="fill-text-faint font-mono"
              fontSize={9}
            >
              {label.text}
            </text>
          ))}
        </svg>
      </div>
    </div>
  );
}

/** Every cell is reachable without colour — the tooltip carries the numbers. */
function cellFill(value: number, max: number): string {
  if (value === 0) return "var(--color-heatmap-empty)";
  const ratio = Math.min(1, value / Math.max(1, max));
  if (ratio < 0.25) return "rgba(255,161,22,0.16)";
  if (ratio < 0.5) return "rgba(255,161,22,0.32)";
  if (ratio < 0.75) return "rgba(255,161,22,0.55)";
  return "rgba(255,161,22,0.85)";
}

function monthLabels(days: ActivityDay[]) {
  const firstDate = new Date(days[0]?.date ?? 0);
  const leadingBlanks = (firstDate.getDay() + 6) % 7;
  const seen = new Set<string>();
  const labels: { key: string; column: number; text: string }[] = [];

  days.forEach((day, index) => {
    const date = new Date(day.date);
    const month = date.toLocaleString("en-US", { month: "short" });
    const key = `${date.getFullYear()}-${month}`;
    if (seen.has(key)) return;
    seen.add(key);
    const column = Math.floor((index + leadingBlanks) / 7);
    labels.push({ key, column, text: month });
  });

  // Drop a month label when it would collide with the previous one.
  return labels.filter((label, index) =>
    index === 0 ? true : label.column - labels[index - 1].column >= 3,
  );
}
