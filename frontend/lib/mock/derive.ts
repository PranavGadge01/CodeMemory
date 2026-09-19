import type {
  Attempt,
  Language,
  Problem,
  Submission,
  SubmissionStatus,
} from "@/lib/types";

/**
 * Pure derivations over the CodeMemory domain types.
 *
 * These mirror the `@property` helpers on the backend `Problem` model so the
 * UI can ask the same questions of mock data and (later) API data.
 */

const ACCEPTED = "Accepted";

export function isAccepted(status: SubmissionStatus): boolean {
  return status === ACCEPTED;
}

export function attemptIsAccepted(attempt: Attempt): boolean {
  return (
    attempt.status === ACCEPTED || attempt.submissions.some((sub) => isAccepted(sub.status))
  );
}

/** All submissions across every attempt, oldest first. */
export function submissionsOf(problem: Problem): Submission[] {
  return problem.attempts
    .flatMap((attempt) => attempt.submissions)
    .sort((a, b) => a.submittedAt.localeCompare(b.submittedAt));
}

export function latestSubmission(problem: Problem): Submission | null {
  const all = submissionsOf(problem);
  return all[all.length - 1] ?? null;
}

export function latestAcceptedSubmission(problem: Problem): Submission | null {
  const accepted = submissionsOf(problem).filter((sub) => isAccepted(sub.status));
  return accepted[accepted.length - 1] ?? null;
}

export type SolveStatus = "Solved" | "Attempted" | "Untouched";

export function solveStatus(problem: Problem): SolveStatus {
  if (problem.attempts.some(attemptIsAccepted)) return "Solved";
  if (problem.attempts.length > 0) return "Attempted";
  return "Untouched";
}

export function isSolved(problem: Problem): boolean {
  return solveStatus(problem) === "Solved";
}

export function attemptCount(problem: Problem): number {
  return problem.attempts.length;
}

export function submissionCount(problem: Problem): number {
  return problem.attempts.reduce((sum, attempt) => sum + attempt.submissions.length, 0);
}

export function failedSubmissionCount(problem: Problem): number {
  return submissionsOf(problem).filter((sub) => !isAccepted(sub.status)).length;
}

export function languagesOf(problem: Problem): Language[] {
  return [...new Set(submissionsOf(problem).map((sub) => sub.language))];
}

export function latestAnalysis(problem: Problem): Attempt["analysis"] {
  const accepted = problem.attempts
    .filter((attempt) => attemptIsAccepted(attempt) && attempt.analysis)
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  return accepted[0]?.analysis ?? problem.attempts[problem.attempts.length - 1]?.analysis ?? null;
}

/** Fastest accepted runtime, used for the "best" column in problem tables. */
export function bestRuntime(problem: Problem): number | null {
  const accepted = submissionsOf(problem).filter((sub) => isAccepted(sub.status));
  if (!accepted.length) return null;
  return accepted.reduce(
    (best, sub) => (sub.runtimeMs !== null && (best === null || sub.runtimeMs < best) ? sub.runtimeMs : best),
    null as number | null,
  );
}

export function firstAttemptAccepted(problem: Problem): boolean {
  const first = problem.attempts[0];
  return Boolean(first && attemptIsAccepted(first));
}

export function lastActivityAt(problem: Problem): string {
  const latest = latestSubmission(problem);
  return latest?.submittedAt ?? problem.updatedAt;
}

export function daysSince(iso: string): number {
  const day = 24 * 60 * 60 * 1000;
  return Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / day));
}
