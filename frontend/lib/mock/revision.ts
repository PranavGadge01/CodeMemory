import type { RevisionQueueItem } from "@/lib/types";
import { getMockProblems } from "@/lib/mock/problems";
import {
  attemptCount,
  daysSince,
  failedSubmissionCount,
  isSolved,
  lastActivityAt,
  submissionCount,
} from "@/lib/mock/derive";

/**
 * Revision priority, following the backend formula:
 *
 *   P = W_diff·S_diff + W_fail·S_fail + W_recency·S_recency
 *        + W_weakness·S_weakness − W_recent·S_recent
 *
 * (`revision/revision_models.py`). The UI recomputes the breakdown locally so
 * the queue and the explanation panel stay in sync.
 */
const WEIGHTS = {
  difficulty: 2.0,
  failure: 3.0,
  recency: 2.5,
  weakness: 2.0,
  recentSolvedPenalty: 1.5,
};

const DIFFICULTY_SCORE: Record<string, number> = { Easy: 0.35, Medium: 0.7, Hard: 1.0 };

const WEAK_TOPICS = new Set([
  "Dynamic Programming",
  "Monotonic Stack",
  "Union Find",
  "Topological Sort",
  "Heap",
  "Binary Search",
  "Matrix",
]);

export function getMockRevisionQueue(): RevisionQueueItem[] {
  const problems = getMockProblems();

  const items = problems
    .map((problem): RevisionQueueItem | null => {
      const attempts = attemptCount(problem);
      const failed = failedSubmissionCount(problem);
      const lastActivity = lastActivityAt(problem);
      const daysSinceActivity = daysSince(lastActivity);
      const solved = isSolved(problem);
      const submissions = submissionCount(problem);

      // Nothing worth revisiting if it was solved first-try very recently.
      if (solved && attempts === 1 && daysSinceActivity < 21) return null;
      // Solved cleanly long ago is only scheduled, never urgent.
      if (solved && failed === 0 && daysSinceActivity < 45) return null;

      const difficultyScore = DIFFICULTY_SCORE[problem.difficulty] ?? 0.5;
      const failureScore = Math.min(1, (failed * 0.34) + (solved ? 0 : 0.25));
      const recencyScore = Math.min(1, daysSinceActivity / 120);
      const weaknessScore = problem.topics.some((topic) => WEAK_TOPICS.has(topic)) ? 0.85 : 0.25;
      const recentSolvedPenalty = solved && daysSinceActivity < 14 ? 0.8 : 0;

      const finalScore =
        WEIGHTS.difficulty * difficultyScore +
        WEIGHTS.failure * failureScore +
        WEIGHTS.recency * recencyScore +
        WEIGHTS.weakness * weaknessScore -
        WEIGHTS.recentSolvedPenalty * recentSolvedPenalty;

      const overdue = !solved || daysSinceActivity > 60;

      return {
        problemId: problem.id,
        title: problem.title,
        slug: problem.slug,
        difficulty: problem.difficulty,
        priorityScore: Math.max(0, finalScore),
        lastActivityAt: lastActivity,
        topics: problem.topics,
        status: overdue ? "Overdue" : daysSinceActivity > 30 ? "Due" : "Scheduled",
        confidence: confidenceFor(failureScore, attempts),
        reason: reasonFor(problem, solved, failed, submissions, daysSinceActivity),
        breakdown: {
          problemId: problem.id,
          title: problem.title,
          slug: problem.slug,
          difficulty: problem.difficulty,
          finalScore: Math.max(0, finalScore),
          difficultyScore,
          failureScore,
          recencyScore,
          weaknessScore,
          recentSolvedPenalty,
          daysSinceLastActivity: daysSinceActivity,
        },
      };
    })
    .filter((item): item is RevisionQueueItem => item !== null);

  return items.sort((a, b) => b.priorityScore - a.priorityScore);
}

function confidenceFor(failureScore: number, attempts: number): RevisionQueueItem["confidence"] {
  if (failureScore > 0.7 || attempts >= 4) return "Low";
  if (failureScore > 0.4) return "Medium";
  return "High";
}

function reasonFor(
  problem: ReturnType<typeof getMockProblems>[number],
  solved: boolean,
  failed: number,
  submissions: number,
  days: number,
): string {
  if (!solved) {
    return `Unsolved after ${submissions} submission${submissions === 1 ? "" : "s"} across ${problem.attempts.length} attempt${problem.attempts.length === 1 ? "" : "s"}.`;
  }
  if (failed >= 3) {
    return `Took ${failed} failed submissions before accepting — the pattern is not yet internalised.`;
  }
  if (WEAK_TOPICS.has(problem.topics[0] ?? "")) {
    return `Sits in a weak topic (${problem.topics[0]}) and was last touched ${days} days ago.`;
  }
  return `Solved cleanly, but ${days} days have passed since the last attempt.`;
}
