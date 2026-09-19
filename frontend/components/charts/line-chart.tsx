import * as React from "react";
import { cn } from "@/lib/utils";
import { CHART_COLORS, ChartSvg, GridLines, niceTicks, scaleLinear } from "@/components/charts/lib";

export interface LineSeries {
  label: string;
  values: number[];
  color?: string;
  /** Filled area under the line. */
  area?: boolean;
}

/**
 * Trend chart for time series. Orange carries the primary series; comparison
 * series render as quiet outlines so the eye lands on the story, not on the
 * legend.
 */
export function LineChart({
  series,
  labels,
  className,
  height = 150,
  formatValue = (value) => String(value),
}: {
  series: LineSeries[];
  labels: string[];
  className?: string;
  height?: number;
  formatValue?: (value: number) => string;
}) {
  const padLeft = 32;
  const padBottom = 22;
  const padTop = 10;
  const innerHeight = height - padBottom - padTop;
  const usable = 100 - padLeft;

  const max = Math.max(1, ...series.flatMap((s) => s.values));
  const ticks = niceTicks(max, 3);
  const top = ticks[ticks.length - 1] ?? max;

  const y = scaleLinear([0, top], [innerHeight + padTop, padTop]);
  const pointCount = series[0]?.values.length ?? 1;
  const x = (index: number) =>
    pointCount > 1 ? padLeft + (index * usable) / (pointCount - 1) : padLeft + usable / 2;

  return (
    <div className={cn("w-full", className)}>
      <ChartSvg
        viewBox={`0 0 100 ${height}`}
        label={`Line chart. ${series
          .map((s) => `${s.label}: ${s.values.join(", ")}`)
          .join(". ")}`}
      >
        <GridLines values={ticks} y={y} x0={padLeft} x1={100} format={formatValue} />
        {series.map((line, seriesIndex) => {
          const points = line.values.map((value, index) => [x(index), y(value)] as const);
          const path = points
            .map(([px, py], index) => `${index === 0 ? "M" : "L"}${px.toFixed(2)},${py.toFixed(2)}`)
            .join(" ");
          const isPrimary = seriesIndex === 0;
          const stroke = line.color ?? (isPrimary ? CHART_COLORS.accent : CHART_COLORS.muted);
          const areaPath = `${path} L${points[points.length - 1]?.[0]},${
            innerHeight + padTop
          } L${points[0]?.[0]},${innerHeight + padTop} Z`;

          return (
            <g key={line.label}>
              {line.area && isPrimary ? (
                <path
                  d={areaPath}
                  fill="url(#cm-line-gradient)"
                  opacity={0.5}
                />
              ) : null}
              <path
                d={path}
                fill="none"
                stroke={stroke}
                strokeWidth={isPrimary ? 1.6 : 1.1}
                strokeLinecap="round"
                strokeLinejoin="round"
                vectorEffect="non-scaling-stroke"
              />
              {isPrimary
                ? points.map(([px, py], index) => (
                    <circle key={index} cx={px} cy={py} r={1.8} fill={stroke}>
                      <title>{`${labels[index]} — ${line.values[index]}`}</title>
                    </circle>
                  ))
                : null}
            </g>
          );
        })}
        {labels.map((label, index) => (
          <text
            key={`${label}-${index}`}
            x={x(index)}
            y={height - 7}
            textAnchor="middle"
            className="fill-text-faint font-mono"
            fontSize={7.5}
          >
            {label}
          </text>
        ))}
        <defs>
          <linearGradient id="cm-line-gradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(255,161,22,0.22)" />
            <stop offset="100%" stopColor="rgba(255,161,22,0)" />
          </linearGradient>
        </defs>
      </ChartSvg>
      {series.length > 1 ? (
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1">
          {series.map((line) => (
            <span key={line.label} className="inline-flex items-center gap-1.5 text-caption text-text-muted">
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: line.color ?? CHART_COLORS.muted }}
                aria-hidden="true"
              />
              {line.label}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
