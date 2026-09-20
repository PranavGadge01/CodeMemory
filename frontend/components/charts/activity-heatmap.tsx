import * as React from "react";
import { cn } from "@/lib/utils";
import type { ActivityDay } from "@/lib/types";
import { formatNumber } from "@/lib/format";

/** Width reserved inside the viewBox for the weekday labels. */
const LABEL_WIDTH = 24;
/**
 * The grid scales up to fill a wide card, but not without limit — past this the
 * cells stop reading as a compact contribution graph and start reading as
 * oversized tiles, and the card grows taller than the section warrants.
 */
const MAX_CELL_SCALE = 1.5;
const WEEKDAYS = [
  { row: 0, label: "Mon" },
  { row: 2, label: "Wed" },
  { row: 4, label: "Fri" },
];

/**
 * Solving activity heatmap.
 *
 * The CodeMemory "memory trace": each cell is one day, and the cell's weight
 * is how much of that day was spent submitting. Weeks run down the columns so
 * the grid reads as a vertical timeline of the user's coding history.
 *
 * The window is a rolling trailing year: the last column is always today and
 * the first is roughly 52 weeks back, so the graph never goes stale the way a
 * Jan–Dec grid would as the year advances.
 *
 * Sizing: the viewBox is the grid's natural size at its design cell size, and
 * the SVG scales to the card width while keeping that aspect ratio, so a
 * trailing year spans the card without cells being stretched non-uniformly.
 * A floor keeps weekday and month labels legible on narrow screens — below it
 * the wrapper scrolls horizontally instead of shrinking the type any further.
 */
export function ActivityHeatmap({
  days,
  className,
  cellSize = 10,
  gap = 2,
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

  const step = cellSize + gap;
  const gridWidth = columns * step;
  const gridHeight = 7 * step;
  const width = LABEL_WIDTH + gridWidth;
  const height = gridHeight + 14;

  return (
    <div className={cn("min-w-0 overflow-x-auto", className)}>
      <svg
        className="block mx-auto h-auto w-full"
        viewBox={`0 0 ${width} ${height}`}
        style={{ minWidth: width, maxWidth: width * MAX_CELL_SCALE }}
        role="img"
        aria-label={`Solving activity over ${days.length} days. Peak ${max} submissions in a day.`}
      >
        {WEEKDAYS.map(({ row, label }) => (
          <text
            key={row}
            x={LABEL_WIDTH - 6}
            y={row * step + Math.round(cellSize / 2) + 3}
            textAnchor="end"
            className="fill-text-faint font-mono"
            fontSize={9}
          >
            {label}
          </text>
        ))}
        {days.map((day, index) => {
          const position = index + leadingBlanks;
          const column = Math.floor(position / 7);
          const row = position % 7;
          const x = LABEL_WIDTH + column * step;
          const y = row * step;
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
            x={LABEL_WIDTH + label.column * step}
            y={gridHeight + 10}
            className="fill-text-faint font-mono"
            fontSize={9}
          >
            {label.text}
          </text>
        ))}
      </svg>
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
