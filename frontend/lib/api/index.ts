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
  getFullProfileInsight,
  getTopicInsight,
  getProblemInsight,
  getOptimizationExplanation,
  getLearningAnalysis,
  getSubmissionPatterns,
  getCollectiveLearningProfile,
  getSubmissionLearningAnalysis,
  getNextRecommendations,
  getPersonalizedRoadmap,
  type DashboardData,
  type ProblemListParams,
  type ProblemListResult,
  type SubmissionListParams,
  type SubmissionListResult,
  type AnalyticsData,
  type AnalyticsGranularity,
  type KnowledgeData,
  type RevisionListParams,
  type KnowledgePatternsData,
  type OptimizationExplanation,
  type AttemptEvolutionAnalysis,
  type SubmissionPatternInsights,
  type ProblemRecommendation,
  type RoadmapMilestone,
  type PersonalizedRoadmap,
  type CollectiveLearningInsight,
  type SubmissionLearningAnalysis,
  type NextProblems,
  type KnowledgeCluster,
} from "@/lib/api/resources";

export type {
  SubmissionListItem,
  ProblemListItem,
  SolveStatus,
} from "@/lib/api/mappers";

export type {
  SolutionEvolutionData,
  SearchResult,
  KnowledgeGraph,
  GraphNode,
  GraphEdge,
  GraphNodeDetail,
} from "@/lib/types";

