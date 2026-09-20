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
 * Width of the chart's design space, in the same units as the viewBox.
 *
 * Sizing is split across two props:
 * - `VIEW_WIDTH` sets the coordinate space the bars are laid out in. It is
 *   deliberately only a little wider than the legacy 560, so 12 weekly bars
 *   still keep readable spacing and the x-axis labels never collide.
 * - `maxWidth` caps the rendered pixel width. `ChartSvg` fills its container,
 *   so without a cap a full-width analytics card stretches this viewBox into a
 *   6:1 strip. Capping it near the design width keeps the plot area at a
 *   dashboard-like ~2.6:1 aspect ratio instead.
 */
const VIEW_WIDTH = 620;

/**
 * Compact column chart. Submissions per week, solved per month — any series
 * where the count is the story and the label is a period.
 */
export function BarChart({
  data,
  className,
  height = 160,
  maxWidth = VIEW_WIDTH,
  formatValue = (value) => String(value),
  emphasizedOnly = false,
}: {
  data: BarDatum[];
  className?: string;
  height?: number;
  maxWidth?: number;
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
  const slot = (VIEW_WIDTH - padLeft) / Math.max(1, data.length);
  const barWidth = Math.min(slot * 0.5, 18);

  return (
    <ChartSvg
      className={className}
      viewBox={`0 0 ${VIEW_WIDTH} ${height}`}
      height={height}
      maxWidth={maxWidth}
      label={`Bar chart. ${data.map((d) => `${d.label}: ${d.value}`).join(", ")}`}
    >
      <GridLines
        values={ticks}
        y={y}
        x0={padLeft}
        x1={VIEW_WIDTH}
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
              fill={isEmphasized ? CHART_COLORS.accent : CHART_COLORS.bar}
              opacity={isEmphasized ? 0.9 : 1}
            >
              {datum.hint ? <title>{datum.hint}</title> : null}
            </rect>
            <text
              x={centerX}
              y={height - 7}
              textAnchor="middle"
              className="fill-text-faint font-mono"
              fontSize={10}
            >
              {datum.label}
            </text>
          </g>
        );
      })}
    </ChartSvg>
  );
}
