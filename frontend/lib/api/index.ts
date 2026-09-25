/**
 * Public API surface. Pages and components import from here.
 *
 *     import { getDashboard } from "@/lib/api";
 */

export { ApiError, isNetworkError, API_BASE_URL } from "@/lib/api/client";
export { toAsyncState, type AsyncState } from "@/lib/api/async-state";
export {
  getHealth,
  getDashboard,
  listProblems,
  getProblem,
  getProblemEvolution,
  listSubmissions,
  getSubmission,
  getAnalytics,
  getKnowledge,
  getRevisionQueue,
  markProblemReviewed,
  getSettings,
  updateSettings,
  getLeetCodeStatus,
  connectLeetCode,
  syncLeetCode,
  disconnectLeetCode,
  search,
  type DashboardData,
  type ProblemListParams,
  type ProblemListResult,
  type SubmissionListParams,
  type SubmissionListResult,
  type AnalyticsData,
  type AnalyticsGranularity,
  type KnowledgeData,
  type RevisionListParams,
  type SolutionEvolutionData,
  type SearchResult,
} from "@/lib/api/resources";
