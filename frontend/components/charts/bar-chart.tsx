import * as React from "react";
import { CHART_COLORS, ChartSvg, GridLines, niceTicks, scaleLinear } from "@/components/charts/lib";

export interface BarDatum {
  label: string;
  value: number;
  /** Highlighted series — the one the page is making a point about. */
  emphasized?: boolean;
  hint?: string;
}

/**
 * Compact column chart. Submissions per week, solved per month — any series
 * where the count is the story and the label is a period.
 */
export function BarChart({
  data,
  className,
  height = 140,
  formatValue = (value) => String(value),
  emphasizedOnly = false,
}: {
  data: BarDatum[];
  className?: string;
  height?: number;
  formatValue?: (value: number) => string;
  /** Only draw the emphasized bars, keeping the rest as ghost outlines. */
  emphasizedOnly?: boolean;
}) {
  const padLeft = 30;
  const padBottom = 22;
  const padTop = 8;
  const innerHeight = height - padBottom - padTop;
  const max = Math.max(1, ...data.map((d) => d.value));
  const ticks = niceTicks(max, 3);
  const top = ticks[ticks.length - 1] ?? max;

  const y = scaleLinear([0, top], [innerHeight + padTop, padTop]);
  const usable = 100 - padLeft;
  const slot = usable / Math.max(1, data.length);
  const barWidth = Math.min(slot * 0.62, 14);

  return (
    <ChartSvg
      className={className}
      viewBox={`0 0 100 ${height}`}
      label={`Bar chart. ${data.map((d) => `${d.label}: ${d.value}`).join(", ")}`}
    >
      <GridLines
        values={ticks}
        y={y}
        x0={padLeft}
        x1={100}
        format={formatValue}
      />
      {data.map((datum, index) => {
        const centerX = padLeft + slot * index + slot / 2;
        const isEmphasized = datum.emphasized ?? !emphasizedOnly;
        const rectHeight = Math.max(1, innerHeight + padTop - y(datum.value));
        return (
          <g key={`${datum.label}-${index}`}>
            <rect
              x={centerX - barWidth / 2}
              y={y(datum.value)}
              width={barWidth}
              height={rectHeight}
              rx={1.5}
              fill={isEmphasized ? CHART_COLORS.accent : "rgba(255,255,255,0.10)"}
              opacity={isEmphasized ? 0.9 : 1}
            >
              {datum.hint ? <title>{datum.hint}</title> : null}
            </rect>
            <text
              x={centerX}
              y={height - 8}
              textAnchor="middle"
              className="fill-text-faint font-mono"
              fontSize={7.5}
            >
              {datum.label}
            </text>
          </g>
        );
      })}
    </ChartSvg>
  );
}
