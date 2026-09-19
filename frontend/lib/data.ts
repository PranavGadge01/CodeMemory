/**
 * Data service seam.
 *
 * Every page and component reads data through this module rather than reaching
 * into `lib/mock` directly. Today these calls resolve against generated mock
 * data. When the backend is wired up, only this file changes — the
 * implementations below are swapped for `fetch()` calls against the API and
 * every page keeps its exact signature.
 *
 *     UI component  →  lib/data  →  lib/mock  (today)
 *     UI component  →  lib/data  →  lib/api   (later)
 */

import type {
  ActivityDay,
  AnalyticsOverview,
  DifficultyStat,
  KnowledgeCluster,
  KnowledgeGraph,
  LanguageStat,
  Problem,
  ProgressOverTime,
  RevisionQueueItem,
  StruggleProblem,
  TimelineEvent,
  TopicStat,
} from "@/lib/types";
import {
  getMockActivity,
  getMockStreaks,
  getMockTimeline,
} from "@/lib/mock/activity";
import {
  getMockDifficultyStats,
  getMockLanguageStats,
  getMockOverview,
  getMockProgress,
  getMockStruggles,
  getMockTopicStats,
} from "@/lib/mock/analytics";
import { getMockKnowledgeGraph, getMockClusters } from "@/lib/mock/knowledge";
import { getMockProblems } from "@/lib/mock/problems";
import { getMockRevisionQueue } from "@/lib/mock/revision";

export interface DashboardData {
  overview: AnalyticsOverview;
  activity: ActivityDay[];
  timeline: TimelineEvent[];
  struggles: StruggleProblem[];
  topics: TopicStat[];
  languages: LanguageStat[];
  difficulties: DifficultyStat[];
  revisionQueue: RevisionQueueItem[];
  progress: ProgressOverTime[];
}

export function getDashboardData(): DashboardData {
  const streaks = getMockStreaks();
  const overview = getMockOverview();

  return {
    overview: {
      ...overview,
      currentStreakDays: streaks.current,
      longestStreakDays: streaks.longest,
      activeDaysLast30: streaks.activeDays30,
    },
    activity: getMockActivity(),
    timeline: getMockTimeline(10),
    struggles: getMockStruggles(5),
    topics: getMockTopicStats(),
    languages: getMockLanguageStats(),
    difficulties: getMockDifficultyStats(),
    revisionQueue: getMockRevisionQueue().slice(0, 5),
    progress: getMockProgress(),
  };
}

export function getProblems(): Problem[] {
  return getMockProblems();
}

export function getProblem(slug: string): Problem | null {
  return getMockProblems().find((problem) => problem.slug === slug) ?? null;
}

export function getActivity(): ActivityDay[] {
  return getMockActivity();
}

export function getAnalytics(): {
  overview: AnalyticsOverview;
  difficulties: DifficultyStat[];
  topics: TopicStat[];
  languages: LanguageStat[];
  progress: ProgressOverTime[];
  struggles: StruggleProblem[];
} {
  return {
    overview: getDashboardData().overview,
    difficulties: getMockDifficultyStats(),
    topics: getMockTopicStats(),
    languages: getMockLanguageStats(),
    progress: getMockProgress(),
    struggles: getMockStruggles(8),
  };
}

export function getRevisionQueue(): RevisionQueueItem[] {
  return getMockRevisionQueue();
}

export function getKnowledge(): {
  graph: KnowledgeGraph;
  clusters: KnowledgeCluster[];
} {
  return {
    graph: getMockKnowledgeGraph(),
    clusters: getMockClusters(),
  };
}

export function getTimeline(limit = 14): TimelineEvent[] {
  return getMockTimeline(limit);
}

export function getStreaks(): { current: number; longest: number; activeDays30: number } {
  return getMockStreaks();
}
