/**
 * Typed API resources.
 *
 * One function per backend endpoint. Pages and components import these rather
 * than touching `client.ts`, so the URL surface and the response typing live in
 * one place. Each function returns the UI domain type — the DTO → domain
 * conversion happens through `mappers.ts`.
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
  RevisionQueueItemDTO,
  SolutionEvolutionDTO,
  SearchResponseDTO,
} from "@/lib/api/types";
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
  SearchResult,
  StruggleProblem,
  Submission,
  TimelineEvent,
  TopicStat,
} from "@/lib/types";
import {
  mapActivityDay,
  mapAnalyticsOverview,
  mapDifficultyStat,
  mapKnowledgeCluster,
  mapKnowledgeGraph,
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

export interface SolutionEvolutionData {
  problemId: string;
  problemTitle: string;
  totalAttempts: number;
  steps: SolutionEvolutionStep[];
  evolutionNarrative: string;
  keyBreakthrough: string | null;
}

export interface SolutionEvolutionStep {
  attemptNumber: number;
  status: string;
  approach: string;
  timeComplexity: string;
  spaceComplexity: string;
  runtime: string | null;
  memory: string | null;
  timestamp: string;
}

export function getProblemEvolution(slug: string): Promise<SolutionEvolutionData> {
  return apiGet<SolutionEvolutionDTO>(`/problems/${encodeURIComponent(slug)}/evolution`);
}

/* --- Submissions ------------------------------------------------------- */

export interface SubmissionListResult {
  items: Submission[];
  page: number;
  pageSize: number;
  total: number;
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
  const dto = await apiGet<PaginatedResponse<SubmissionDTO>>("/submissions", {
    page: params.page,
    page_size: params.pageSize,
    language: params.language,
    status: params.status,
    problem: params.problem,
  });

  return {
    items: dto.items.map(mapSubmission),
    page: dto.page,
    pageSize: dto.pageSize,
    total: dto.total,
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

export interface KnowledgeData {
  graph: KnowledgeGraph;
  clusters: KnowledgeCluster[];
}

export async function getKnowledge(): Promise<KnowledgeData> {
  const dto = await apiGet<KnowledgeDTO>("/knowledge");

  return {
    graph: mapKnowledgeGraph(dto.graph),
    clusters: dto.clusters.map(mapKnowledgeCluster),
  };
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

export type { SearchResult } from "@/lib/types";
export type { SearchResultItemDTO } from "@/lib/api/types";

/* --- Search ----------------------------------------------------------- */

export function search(query: string, limit?: number): Promise<SearchResult[]> {
  const params: Record<string, unknown> = { q: query };
  if (limit !== undefined) params.limit = limit;
  return apiGet<SearchResponseDTO>("/search", params).then((dto) => dto.results.map(mapSearchResult));
}

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
