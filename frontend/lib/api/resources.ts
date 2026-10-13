/**
 * Typed API resources.
 *
 * One function per backend endpoint. Pages and components import these rather than touching `client.ts`, so the URL surface and the response typing live in one place. Each function returns the UI domain type — the DTO → domain conversion happens through `mappers.ts`.
 *
 * No business logic here: these are fetch + map, nothing else.
 */

import { apiGet, apiPost, apiPut } from "@/lib/api/client";
import type {
  DashboardDTO,
  AnalyticsDTO,
  KnowledgeDTO,
  SettingsDTO,
  HealthDTO,
  PaginatedResponse,
  ProblemDTO,
  ProblemListItemDTO,
  SubmissionDTO,
  SubmissionListDTO,
  RevisionQueueItemDTO,
  SolutionEvolutionDTO,
  SearchResponseDTO,
  GroundedInsightDTO,
  KnowledgePatternsDTO,
  OptimizationExplanationDTO,
  AttemptEvolutionAnalysisDTO,
  SubmissionPatternInsightsDTO,
  CollectiveLearningInsightDTO,
  SubmissionLearningAnalysisDTO,
  NextProblemsDTO,
  PersonalizedRoadmapDTO,
} from "@/lib/api/types";
import type {
  ActivityDay,
  AnalyticsOverview,
  DifficultyStat,
  KnowledgeData,
  LanguageStat,
  Problem,
  ProgressOverTime,
  RevisionQueueItem,
  SearchResult,
  StruggleProblem,
  Submission,
  TimelineEvent,
  TopicStat,
  GroundedInsight,
  KnowledgePatternsData,
  SolutionEvolutionData,
  OptimizationExplanation,
  AttemptEvolutionAnalysis,
  SubmissionPatternInsights,
  NextProblems,
  PersonalizedRoadmap,
  CollectiveLearningInsight,
  SubmissionLearningAnalysis,
} from "@/lib/types";
import {
  mapActivityDay,
  mapAnalyticsOverview,
  mapDifficultyStat,
  mapKnowledgeGraphWithDetails,
  mapLanguageStat,
  mapProblem,
  mapProblemListItem,
  mapProgressOverTime,
  mapRevisionQueueItem,
  mapSearchResult,
  mapStruggleProblem,
  mapSubmission,
  mapTimelineEvent,
  mapTopicStat,
  mapGroundedInsight,
  mapSubmissionListItem,
  type SubmissionListItem,
  mapKnowledgePatterns,
  mapSolutionEvolution,
  mapOptimizationExplanation,
  mapAttemptEvolutionAnalysis,
  mapSubmissionPatternInsights,
  mapNextProblems,
  mapPersonalizedRoadmap,
  mapCollectiveLearningInsight,
  mapSubmissionLearningAnalysis,
} from "@/lib/api/mappers";

/* --- Health ------------------------------------------------------------- */

export function getHealth(): Promise<HealthDTO> {
  return apiGet<HealthDTO>("/health");
}

/* --- Dashboard --------------------------------------------------------- */

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

/**
 * The dashboard endpoint. The backend now serves real activity and timeline
 * arrays, so they are mapped through the DTO → domain layer instead of being
 * discarded.
 */
export async function getDashboard(): Promise<DashboardData> {
  const dto = await apiGet<DashboardDTO>("/dashboard");

  return {
    overview: mapAnalyticsOverview(dto.overview),
    activity: dto.activity.map(mapActivityDay),
    timeline: dto.timeline.map(mapTimelineEvent),
    struggles: dto.struggles.map(mapStruggleProblem),
    topics: dto.topics.map(mapTopicStat),
    languages: dto.languages.map(mapLanguageStat),
    difficulties: dto.difficulties.map(mapDifficultyStat),
    revisionQueue: dto.revisionQueue.map(mapRevisionQueueItem),
    progress: dto.progress.map(mapProgressOverTime),
  };
}

/* --- Problems ---------------------------------------------------------- */

export interface ProblemListResult {
  items: ReturnType<typeof mapProblemListItem>[];
  page: number;
  pageSize: number;
  total: number;
}

export interface ProblemListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  difficulty?: string;
  status?: string;
}

/**
 * The problems list. Filtering happens server-side — the endpoint accepts
 * `search`, `difficulty` and `status`, so the caller passes the same values the
 * UI filters on instead of re-filtering the response.
 */
export async function listProblems(params: ProblemListParams = {}): Promise<ProblemListResult> {
  const dto = await apiGet<PaginatedResponse<ProblemListItemDTO>>("/problems", {
    page: params.page,
    page_size: params.pageSize,
    search: params.search,
    difficulty: params.difficulty,
    status: params.status,
  });

  return {
    items: dto.items.map(mapProblemListItem),
    page: dto.page,
    pageSize: dto.pageSize,
    total: dto.total,
  };
}

export function getProblem(slug: string): Promise<Problem> {
  return apiGet<ProblemDTO>(`/problems/${encodeURIComponent(slug)}`).then(mapProblem);
}

export function getProblemEvolution(slug: string): Promise<SolutionEvolutionData> {
  return apiGet<SolutionEvolutionDTO>(`/problems/${encodeURIComponent(slug)}/evolution`).then(mapSolutionEvolution);
}

/* --- Submissions ------------------------------------------------------- */

export interface SubmissionListResult {
  items: SubmissionListItem[];
  page: number;
  pageSize: number;
  total: number;
  summary: SubmissionListDTO["summary"];
  filterOptions: SubmissionListDTO["filterOptions"];
}

export interface SubmissionListParams {
  page?: number;
  pageSize?: number;
  language?: string;
  status?: string;
  problem?: string;
}

export async function listSubmissions(
  params: SubmissionListParams = {},
): Promise<SubmissionListResult> {
  const dto = await apiGet<SubmissionListDTO>("/submissions", {
    page: params.page,
    page_size: params.pageSize,
    language: params.language,
    status: params.status,
    problem: params.problem,
  });

  return {
    items: dto.items.map(mapSubmissionListItem),
    page: dto.page,
    pageSize: dto.pageSize,
    total: dto.total,
    summary: dto.summary,
    filterOptions: dto.filterOptions,
  };
}

export function getSubmission(id: string): Promise<Submission> {
  return apiGet<SubmissionDTO>(`/submissions/${encodeURIComponent(id)}`).then(mapSubmission);
}

/* --- Analytics --------------------------------------------------------- */

export interface AnalyticsData {
  overview: AnalyticsOverview;
  difficulties: DifficultyStat[];
  topics: TopicStat[];
  languages: LanguageStat[];
  progress: ProgressOverTime[];
  struggles: StruggleProblem[];
}

export type AnalyticsGranularity = "day" | "week" | "month";

/**
 * Full analytics. `granularity` maps to the endpoint's query parameter; the UI
 * asks for weeks by default so the progress charts read the way they did with
 * the mock data.
 */
export async function getAnalytics(
  granularity: AnalyticsGranularity = "week",
): Promise<AnalyticsData> {
  const dto = await apiGet<AnalyticsDTO>("/analytics", { granularity });

  return {
    overview: mapAnalyticsOverview(dto.overview),
    difficulties: dto.difficulties.map(mapDifficultyStat),
    topics: dto.topics.map(mapTopicStat),
    languages: dto.languages.map(mapLanguageStat),
    progress: dto.progress.map(mapProgressOverTime),
    struggles: dto.struggles.map(mapStruggleProblem),
  };
}

/* --- Knowledge --------------------------------------------------------- */

export async function getKnowledge(): Promise<KnowledgeData> {
  const dto = await apiGet<KnowledgeDTO>("/knowledge");

  return {
    graph: mapKnowledgeGraphWithDetails(dto.graph),
    clusters: [],  // Deprecated - clusters belong to Analytics
    entityCounts: dto.entityCounts ?? {},
  };
}

/**
 * Get pattern summaries and relationships for the Knowledge page.
 * Returns reusable techniques encountered in practice, along with their
 * connections to other patterns.
 */
export function getKnowledgePatterns(): Promise<KnowledgePatternsData> {
  return apiGet<KnowledgePatternsDTO>("/knowledge/patterns").then(mapKnowledgePatterns);
}

/* --- Revision ---------------------------------------------------------- */

export interface RevisionListParams {
  limit?: number;
  topic?: string;
}

export function getRevisionQueue(params: RevisionListParams = {}): Promise<RevisionQueueItem[]> {
  return apiGet<RevisionQueueItemDTO[]>("/revision", {
    limit: params.limit,
    topic: params.topic,
  }).then((items) => items.map(mapRevisionQueueItem));
}

/**
 * Record a review. The backend returns `{ "status": "ok" }` on success and a
 * 404-shaped error when the slug is unknown; the caller surfaces that error
 * rather than optimistically removing the row.
 */
export function markProblemReviewed(slug: string): Promise<{ status: string }> {
  return apiPost<{ status: string }>(`/revision/${encodeURIComponent(slug)}/reviewed`);
}

/* --- Settings ---------------------------------------------------------- */

export function getSettings(): Promise<SettingsDTO> {
  return apiGet<SettingsDTO>("/settings");
}

export function updateSettings(patch: Partial<SettingsDTO>): Promise<SettingsDTO> {
  return apiPut<SettingsDTO>("/settings", patch);
}

/* --- Search ----------------------------------------------------------- */

export function search(query: string, limit?: number): Promise<SearchResult[]> {
  const params: Record<string, unknown> = { q: query };
  if (limit !== undefined) params.limit = limit;
  return apiGet<SearchResponseDTO>("/search", params).then((dto) => dto.results.map(mapSearchResult));
}

/* --- Grounded Insights ------------------------------------------------ */

export function getFullProfileInsight(): Promise<GroundedInsight> {
  return apiGet<GroundedInsightDTO>("/insights").then(mapGroundedInsight);
}

export function getTopicInsight(topic: string): Promise<GroundedInsight> {
  return apiGet<GroundedInsightDTO>(`/insights/topic/${encodeURIComponent(topic)}`).then(mapGroundedInsight);
}

export function getProblemInsight(slug: string): Promise<GroundedInsight> {
  return apiGet<GroundedInsightDTO>(`/insights/problem/${encodeURIComponent(slug)}`).then(mapGroundedInsight);
}

/* --- Learning / Explainable AI --------------------------------------- */

export function getOptimizationExplanation(
  slug: string,
  submissionId?: string
): Promise<OptimizationExplanation> {
  const qs = submissionId ? `?submission_id=${encodeURIComponent(submissionId)}` : "";
  return apiGet<OptimizationExplanationDTO>(`/problems/${encodeURIComponent(slug)}/optimization${qs}`).then(mapOptimizationExplanation);
}

export function getLearningAnalysis(slug: string): Promise<AttemptEvolutionAnalysis> {
  return apiGet<AttemptEvolutionAnalysisDTO>(`/problems/${encodeURIComponent(slug)}/learning-analysis`).then(mapAttemptEvolutionAnalysis);
}

export function getSubmissionPatterns(): Promise<SubmissionPatternInsights> {
  return apiGet<SubmissionPatternInsightsDTO>("/learning/patterns").then(mapSubmissionPatternInsights);
}

export function getCollectiveLearningProfile(): Promise<CollectiveLearningInsight> {
  return apiGet<CollectiveLearningInsightDTO>("/learning/profile").then(mapCollectiveLearningInsight);
}

export function getSubmissionLearningAnalysis(
  submissionId: string
): Promise<SubmissionLearningAnalysis> {
  return apiGet<SubmissionLearningAnalysisDTO>(
    `/learning/submissions/${encodeURIComponent(submissionId)}`
  ).then(mapSubmissionLearningAnalysis);
}

export function getNextRecommendations(limit = 3): Promise<NextProblems> {
  return apiGet<NextProblemsDTO>(`/learning/recommendations?limit=${limit}`).then(mapNextProblems);
}

export function getPersonalizedRoadmap(): Promise<PersonalizedRoadmap> {
  return apiGet<PersonalizedRoadmapDTO>("/learning/roadmap").then(mapPersonalizedRoadmap);
}

/* --- Type exports for components --------------------------------------- */

export type {
  KnowledgeData,
  KnowledgePatternsData,
  OptimizationExplanation,
  AttemptEvolutionAnalysis,
  SubmissionPatternInsights,
  ProblemRecommendation,
  RoadmapMilestone,
  PersonalizedRoadmap,
  CollectiveLearningInsight,
  SubmissionLearningAnalysis,
  NextProblems,
  KnowledgeCluster,
  SolutionEvolutionData,
  SubmissionListItem,
} from "@/lib/types";

/* --- LeetCode ---------------------------------------------------------- */

// LeetCode calls live in `lib/api/leetcode.ts` so the whole connector surface
// is defined in one module. Re-exported here so the existing
// `import { getLeetCodeStatus } from "@/lib/api"` callsite keeps working.
export {
  getLeetCodeStatus,
  connectLeetCode,
  syncLeetCode,
  disconnectLeetCode,
} from "@/lib/api/leetcode";