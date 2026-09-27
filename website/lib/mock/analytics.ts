import type {
  AnalyticsOverview,
  Difficulty,
  DifficultyStat,
  LanguageStat,
  ProgressOverTime,
  StruggleProblem,
  TopicStat,
} from "@/lib/types";
import { getMockProblems } from "@/lib/mock/problems";
import {
  attemptCount,
  attemptIsAccepted,
  isSolved,
  submissionsOf,
} from "@/lib/mock/derive";

const DIFFICULTIES: Difficulty[] = ["Easy", "Medium", "Hard"];

function groupBy<T>(items: T[], key: (item: T) => string): Map<string, T[]> {
  const map = new Map<string, T[]>();
  for (const item of items) {
    const k = key(item);
    if (!map.has(k)) map.set(k, []);
    map.get(k)!.push(item);
  }
  return map;
}

export function getMockOverview(): AnalyticsOverview {
  const problems = getMockProblems();
  const allSubmissions = problems.flatMap(submissionsOf);

  const acceptedProblems = problems.filter(isSolved);
  const acceptedSubmissions = allSubmissions.filter((sub) => sub.status === "Accepted");
  const solvedWithMultipleAttempts = problems.filter(
    (problem) => isSolved(problem) && attemptCount(problem) > 1,
  );

  const firstAttemptAccepted = problems.filter((problem) => {
    const first = problem.attempts[0];
    return Boolean(first && attemptIsAccepted(first));
  });

  return {
    totalProblems: problems.length,
    totalAttempts: problems.reduce((sum, problem) => sum + attemptCount(problem), 0),
    totalSubmissions: allSubmissions.length,
    acceptedProblems: acceptedProblems.length,
    unsolvedProblems: problems.length - acceptedProblems.length,
    overallAcceptanceRatePct:
      allSubmissions.length > 0
        ? (acceptedSubmissions.length / allSubmissions.length) * 100
        : 0,
    avgAttemptsPerSolvedProblem:
      acceptedProblems.length > 0
        ? (acceptedProblems.reduce((sum, problem) => sum + attemptCount(problem), 0) /
            acceptedProblems.length)
        : 0,
    firstAttemptAcceptanceRatePct:
      problems.length > 0 ? (firstAttemptAccepted.length / problems.length) * 100 : 0,
    repeatedProblemRatePct:
      problems.length > 0 ? (solvedWithMultipleAttempts.length / problems.length) * 100 : 0,
    avgSolvingTimeMinutes: 26.4,
    currentStreakDays: 0,
    longestStreakDays: 0,
    activeDaysLast30: 0,
  };
}

export function getMockDifficultyStats(): DifficultyStat[] {
  const problems = getMockProblems();

  return DIFFICULTIES.map((difficulty) => {
    const subset = problems.filter((problem) => problem.difficulty === difficulty);
    const submissions = subset.flatMap(submissionsOf);
    const accepted = submissions.filter((sub) => sub.status === "Accepted");

    return {
      difficulty,
      totalProblems: subset.length,
      solvedProblems: subset.filter(isSolved).length,
      totalAttempts: subset.reduce((sum, problem) => sum + attemptCount(problem), 0),
      totalSubmissions: submissions.length,
      acceptedSubmissions: accepted.length,
      acceptanceRatePct:
        submissions.length > 0 ? (accepted.length / submissions.length) * 100 : 0,
    };
  });
}

export function getMockTopicStats(): TopicStat[] {
  const problems = getMockProblems();
  const byTopic = groupBy(
    problems.flatMap((problem) => problem.topics.map((topic) => ({ topic, problem }))),
    (entry) => entry.topic,
  );

  const stats: TopicStat[] = [...byTopic.entries()].map(([topic, entries]) => {
    const problems = [...new Set(entries.map((entry) => entry.problem))];
    const submissions = problems.flatMap(submissionsOf);
    const accepted = submissions.filter((sub) => sub.status === "Accepted");
    const solved = problems.filter(isSolved);

    return {
      topic,
      totalProblems: problems.length,
      solvedProblems: solved.length,
      totalAttempts: problems.reduce((sum, problem) => sum + attemptCount(problem), 0),
      totalSubmissions: submissions.length,
      acceptedSubmissions: accepted.length,
      acceptanceRatePct:
        submissions.length > 0 ? (accepted.length / submissions.length) * 100 : 0,
      successRatePct: problems.length > 0 ? (solved.length / problems.length) * 100 : 0,
    };
  });

  return stats.sort((a, b) => b.totalSubmissions - a.totalSubmissions);
}

export function getMockLanguageStats(): LanguageStat[] {
  const problems = getMockProblems();
  const submissions = problems.flatMap(submissionsOf);
  const byLanguage = groupBy(submissions, (sub) => sub.language);

  const stats: LanguageStat[] = [...byLanguage.entries()].map(([language, subs]) => {
    const accepted = subs.filter((sub) => sub.status === "Accepted");
    return {
      language: language as LanguageStat["language"],
      totalSubmissions: subs.length,
      acceptedSubmissions: accepted.length,
      acceptanceRatePct: subs.length > 0 ? (accepted.length / subs.length) * 100 : 0,
      usageSharePct: 0,
    };
  });

  const total = stats.reduce((sum, stat) => sum + stat.totalSubmissions, 0);
  for (const stat of stats) {
    stat.usageSharePct = total > 0 ? (stat.totalSubmissions / total) * 100 : 0;
  }

  return stats.sort((a, b) => b.totalSubmissions - a.totalSubmissions);
}

/** Weekly buckets covering the full activity window. */
export function getMockProgress(): ProgressOverTime[] {
  const problems = getMockProblems();
  const submissions = problems
    .flatMap(submissionsOf)
    .sort((a, b) => a.submittedAt.localeCompare(b.submittedAt));

  if (submissions.length === 0) return [];

  const buckets: ProgressOverTime[] = [];
  const weekStarts: Date[] = [];

  // Anchor buckets to the Monday of the first week seen.
  const cursor = new Date(submissions[0].submittedAt);
  cursor.setHours(0, 0, 0, 0);
  cursor.setDate(cursor.getDate() - ((cursor.getDay() + 6) % 7));

  const end = new Date();
  while (cursor <= end) {
    const key = `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, "0")}-${String(
      cursor.getDate(),
    ).padStart(2, "0")}`;
    buckets.push({
      period: key,
      label: cursor.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      problemsSolved: 0,
      totalSubmissions: 0,
      acceptedSubmissions: 0,
    });
    weekStarts.push(new Date(cursor));
    cursor.setDate(cursor.getDate() + 7);
  }

  const bucketFor = (iso: string): ProgressOverTime | null => {
    const time = new Date(iso).getTime();
    for (let i = weekStarts.length - 1; i >= 0; i--) {
      if (time >= weekStarts[i].getTime()) return buckets[i];
    }
    return null;
  };

  for (const sub of submissions) {
    const bucket = bucketFor(sub.submittedAt);
    if (!bucket) continue;
    bucket.totalSubmissions += 1;
    if (sub.status === "Accepted") bucket.acceptedSubmissions += 1;
  }

  for (const problem of problems) {
    const accepted = submissionsOf(problem).find((sub) => sub.status === "Accepted");
    if (!accepted) continue;
    const bucket = bucketFor(accepted.submittedAt);
    if (bucket) bucket.problemsSolved += 1;
  }

  return buckets;
}

export function getMockStruggles(limit = 6): StruggleProblem[] {
  const problems = getMockProblems();

  return problems
    .map((problem) => {
      const attempts = problem.attempts;
      const failedAttempts = attempts.filter((attempt) => !attemptIsAccepted(attempt)).length;
      const failedSubmissions = submissionsOf(problem).filter(
        (sub) => sub.status !== "Accepted",
      ).length;

      return {
        problemId: problem.id,
        title: problem.title,
        slug: problem.slug,
        difficulty: problem.difficulty,
        totalAttempts: attempts.length,
        failedAttempts,
        failedSubmissions,
        status: latestStatus(problem),
        topics: problem.topics,
      };
    })
    .filter((problem) => problem.failedSubmissions >= 1)
    .sort((a, b) => b.failedSubmissions - a.failedSubmissions || b.totalAttempts - a.totalAttempts)
    .slice(0, limit);
}

function latestStatus(problem: ReturnType<typeof getMockProblems>[number]): StruggleProblem["status"] {
  const subs = submissionsOf(problem);
  return subs[subs.length - 1]?.status ?? "Unknown";
}
