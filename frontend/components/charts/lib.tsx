import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Hand-built SVG chart primitives.
 *
 * CodeMemory's analytics should look like one product, not like a charting
 * library's default theme. These primitives give full control over gridline
 * weight, label typography and colour restraint, and they add no dependency.
 * Every chart is pure SVG, so it reflows to its container via viewBox.
 */

export const CHART_COLORS = {
  accent: "var(--color-accent)",
  muted: "rgba(255,255,255,0.22)",
  faint: "rgba(255,255,255,0.09)",
  success: "var(--color-success)",
  warning: "var(--color-warning)",
  error: "var(--color-error)",
  info: "var(--color-info)",
  easy: "var(--color-easy)",
  medium: "var(--color-medium)",
  hard: "var(--color-hard)",
} as const;

export function ChartSvg({
  children,
  className,
  viewBox,
  role = "img",
  label,
}: {
  children: React.ReactNode;
  className?: string;
  viewBox: string;
  role?: "img" | "presentation";
  label?: string;
}) {
  return (
    <svg
      className={cn("block h-auto w-full", className)}
      viewBox={viewBox}
      role={role}
      aria-label={label}
      preserveAspectRatio="none"
    >
      {children}
    </svg>
  );
}

/** Horizontal hairlines + value labels down the left edge. */
export function GridLines({
  values,
  y,
  x0,
  x1,
  format,
}: {
  values: number[];
  y: (value: number) => number;
  x0: number;
  x1: number;
  format?: (value: number) => string;
}) {
  return (
    <g>
      {values.map((value) => (
        <g key={value}>
          <line
            x1={x0}
            x2={x1}
            y1={y(value)}
            y2={y(value)}
            stroke={CHART_COLORS.faint}
            strokeWidth={1}
          />
          {format ? (
            <text
              x={x0 - 8}
              y={y(value) + 3.5}
              textAnchor="end"
              className="fill-text-faint font-mono"
              fontSize={9}
            >
              {format(value)}
            </text>
          ) : null}
        </g>
      ))}
    </g>
  );
}

/** Linear scale, matching d3's API shape without the dependency. */
export function scaleLinear(domain: [number, number], range: [number, number]) {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  const span = d1 - d0 || 1;
  return (value: number): number => r0 + ((value - d0) / span) * (r1 - r0);
}

/** Nice-ish tick values: 0 and up to 4 clean steps. */
export function niceTicks(max: number, count = 4): number[] {
  if (max <= 0) return [0, 1];
  const rough = max / count;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const normalized = rough / magnitude;
  const step = (normalized >= 5 ? 5 : normalized >= 2 ? 2 : 1) * magnitude;
  const ticks: number[] = [];
  for (let value = 0; value <= max + step * 0.5; value += step) {
    ticks.push(Math.round(value * 100) / 100);
  }
  return ticks;
}
