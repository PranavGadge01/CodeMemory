/**
 * Formatting helpers. CodeMemory renders technical metadata (runtime, memory,
 * timestamps, submission ids, complexity) in Geist Mono — these helpers keep
 * that output stable and readable.
 */

const NUMBER_FORMATTER = new Intl.NumberFormat("en-US");

const RELATIVE_UNITS: { unit: Intl.RelativeTimeFormatUnit; ms: number }[] = [
  { unit: "year", ms: 365 * 24 * 60 * 60 * 1000 },
  { unit: "month", ms: 30 * 24 * 60 * 60 * 1000 },
  { unit: "week", ms: 7 * 24 * 60 * 60 * 1000 },
  { unit: "day", ms: 24 * 60 * 60 * 1000 },
  { unit: "hour", ms: 60 * 60 * 1000 },
  { unit: "minute", ms: 60 * 1000 },
];

const RELATIVE = new Intl.RelativeTimeFormat("en-US", { numeric: "auto" });

/** "3d ago", "in 2 weeks" — short and stable width. */
export function formatRelative(input: Date | string): string {
  const date = typeof input === "string" ? new Date(input) : input;
  const diff = date.getTime() - Date.now();

  for (const { unit, ms } of RELATIVE_UNITS) {
    if (Math.abs(diff) >= ms) {
      return RELATIVE.format(Math.round(diff / ms), unit);
    }
  }
  return RELATIVE.format(Math.round(diff / 1000), "second");
}

/** Short absolute date for tables: "Sep 12". */
export function formatDate(input: Date | string): string {
  const date = typeof input === "string" ? new Date(input) : input;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** Full timestamp for tooltips / detail panels. */
export function formatDateTime(input: Date | string): string {
  const date = typeof input === "string" ? new Date(input) : input;
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** ISO-8601 UTC, the canonical CodeMemory serialization form. */
export function formatIso(input: Date | string): string {
  const date = typeof input === "string" ? new Date(input) : input;
  return date.toISOString().replace(".000Z", "Z");
}

/** "45 ms" — LeetCode style runtime. */
export function formatRuntime(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  if (ms < 1) return `${Math.round(ms * 1000)} µs`;
  return `${NUMBER_FORMATTER.format(Math.round(ms))} ms`;
}

/** "17.2 MB" — LeetCode style memory. */
export function formatMemory(mb: number | null | undefined): string {
  if (mb === null || mb === undefined) return "—";
  return `${mb.toFixed(1)} MB`;
}

/** "2,184" — thousands separators on large counters. */
export function formatNumber(value: number): string {
  return NUMBER_FORMATTER.format(value);
}

/** Percent with one decimal, e.g. "68.4%". */
export function formatPercent(value: number, digits = 1): string {
  return `${value.toFixed(digits)}%`;
}

/** "1,024" -> "1K" for compact stat strips. */
export function formatCompact(value: number): string {
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(
    value,
  );
}

/** Beats percentile, e.g. "beats 92%". */
export function formatBeats(percentile: number | null | undefined): string {
  if (percentile === null || percentile === undefined) return "—";
  return `beats ${Math.round(percentile)}%`;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
