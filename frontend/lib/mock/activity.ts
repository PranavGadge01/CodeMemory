import type { ActivityDay, TimelineEvent } from "@/lib/types";
import { dayKey, daysAgo } from "@/lib/mock/clock";
import { createRng, intIn } from "@/lib/mock/random";
import { getMockProblems } from "@/lib/mock/problems";
import { isSolved, latestSubmission, submissionsOf } from "@/lib/mock/derive";

/** Number of trailing days the activity heatmap covers. */
export const ACTIVITY_WINDOW_DAYS = 182;

/**
 * Activity is generated from the *actual* mock submission timestamps, so the
 * heatmap and the submission table always agree. Deterministic jitter is added
 * on days that have submissions to make the bars read naturally.
 */
export function getMockActivity(): ActivityDay[] {
  const rng = createRng(0x2c17);

  const byDay = new Map<string, ActivityDay>();

  // Oldest first, so the leading-zero trim and the streak walk both work.
  for (let offset = ACTIVITY_WINDOW_DAYS - 1; offset >= 0; offset--) {
    const iso = daysAgo(offset);
    byDay.set(dayKey(iso), {
      date: dayKey(iso),
      submissions: 0,
      accepted: 0,
      solved: 0,
      minutesActive: 0,
    });
  }

  for (const problem of getMockProblems()) {
    const subs = submissionsOf(problem);
    const firstAccepted = subs.find((sub) => sub.status === "Accepted");

    for (const sub of subs) {
      const day = byDay.get(dayKey(sub.submittedAt));
      if (!day) continue;
      day.submissions += 1;
      if (sub.status === "Accepted") day.accepted += 1;
      day.minutesActive += intIn(rng, 6, 34);
    }

    if (firstAccepted) {
      const day = byDay.get(dayKey(firstAccepted.submittedAt));
      if (day) day.solved += 1;
    }
  }

  // Drop the leading zero days so the heatmap starts on the first active day.
  const days = [...byDay.values()];
  const firstActive = days.findIndex((day) => day.submissions > 0);
  return days.slice(Math.max(0, firstActive));
}

export function getMockTimeline(limit = 14): TimelineEvent[] {
  const events: TimelineEvent[] = [];

  for (const problem of getMockProblems()) {
    const latest = latestSubmission(problem);
    if (!latest) continue;

    events.push({
      id: `ev_${latest.id}`,
      kind: latest.status === "Accepted" && isSolved(problem) ? "solved" : "attempted",
      title: problem.title,
      detail:
        latest.status === "Accepted"
          ? `Accepted in ${latest.language} · ${problem.attempts.length} attempt${
              problem.attempts.length === 1 ? "" : "s"
            }`
          : `${latest.status} in ${latest.language}`,
      problemSlug: problem.slug,
      language: latest.language,
      occurredAt: latest.submittedAt,
    });

    for (const note of problem.notes) {
      events.push({
        id: `ev_${note.id}`,
        kind: "learned",
        title: `Note on ${problem.title}`,
        detail: note.content,
        problemSlug: problem.slug,
        language: null,
        occurredAt: note.createdAt,
      });
    }
  }

  // System-level events, so the timeline reads as a living archive.
  events.push({
    id: "ev_import_leetcode",
    kind: "imported",
    title: "LeetCode history imported",
    detail: "41 submissions · 21 problems · deduplicated by SHA-256",
    problemSlug: null,
    language: null,
    occurredAt: daysAgo(128),
  });
  events.push({
    id: "ev_memory_index",
    kind: "revised",
    title: "Memory index rebuilt",
    detail: "Semantic embeddings refreshed for 63 memory documents",
    problemSlug: null,
    language: null,
    occurredAt: daysAgo(3),
  });

  return events.sort((a, b) => b.occurredAt.localeCompare(a.occurredAt)).slice(0, limit);
}

/** Current and longest streak, computed from the real activity series. */
export function getMockStreaks(): { current: number; longest: number; activeDays30: number } {
  const activity = getMockActivity();
  let current = 0;
  let longest = 0;
  let run = 0;

  for (const day of activity) {
    if (day.submissions > 0) {
      run += 1;
      longest = Math.max(longest, run);
    } else {
      run = 0;
    }
  }
  // The current streak is the run touching today.
  for (let i = activity.length - 1; i >= 0; i--) {
    if (activity[i].submissions > 0) current += 1;
    else break;
  }

  const activeDays30 = activity.slice(-30).filter((day) => day.submissions > 0).length;

  return { current, longest, activeDays30 };
}
