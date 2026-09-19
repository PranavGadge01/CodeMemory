/**
 * Mock clock.
 *
 * Timestamps in the mock dataset are generated relative to the start of the
 * *current day* rather than a hard-coded date, so "3d ago" stays truthful
 * whenever the frontend is opened. Anchoring to midnight (rather than to the
 * instant of page load) keeps the server-rendered and client-rendered trees
 * identical, so React hydration is clean.
 */

export function mockNow(): Date {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return now;
}

/** Epoch milliseconds for the day anchor. */
export function mockNowMs(): number {
  return mockNow().getTime();
}

const DAY_MS = 24 * 60 * 60 * 1000;

/** ISO string for `n` days before the anchor day. */
export function daysAgo(n: number): string {
  return new Date(mockNowMs() - n * DAY_MS).toISOString();
}

/** ISO string for `n` days after the anchor day (scheduled revisions). */
export function daysAhead(n: number): string {
  return new Date(mockNowMs() + n * DAY_MS).toISOString();
}

/** Stable day key, e.g. "2026-09-19", used by activity heatmaps. */
export function dayKey(date: Date | string): string {
  const d = typeof date === "string" ? new Date(date) : date;
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${month}-${day}`;
}
