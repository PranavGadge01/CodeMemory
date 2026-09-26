/**
 * CodeMemory frontend domain types.
 *
 * These deliberately mirror the backend domain models in
 * `src/codememory/domain/{models,enums}.py` so the mock-data layer can be
 * swapped for a real API without reshaping the UI.
 */

export type Difficulty = "Easy" | "Medium" | "Hard" | "Unknown";

export type SubmissionStatus =
  | "Accepted"
  | "Wrong Answer"
  | "Time Limit Exceeded"
  | "Memory Limit Exceeded"
  | "Runtime Error"
  | "Compile Error"
  | "Unknown";

export type Platform = "LeetCode" | "HackerRank" | "Codeforces" | "Custom";

export type Language =
  | "Python"
  | "Python 3"
  | "Java"
  | "C++"
  | "C"
  | "JavaScript"
  | "TypeScript"
  | "Go"
  | "Rust"
  | "Ruby"
  | "Swift"
  | "Kotlin";

export interface Submission {
  id: string;
  problemId: string;
  attemptId: string | null;
  code: string | null;
  language: Language;
  status: SubmissionStatus;
  runtimeMs: number | null;
  memoryMb: number | null;
  beatsPercent: number | null;
  submittedAt: string;
  errorMessage: string | null;
  submissionHash: string;
  sourceProvider: string | null;
  sourceAccount: string | null;
}

export interface SolutionAnalysis {
  approachName: string;
  timeComplexity: string;
  spaceComplexity: string;
  keyInsights: string[];
  tradeOffs: string | null;
  bottleneck: string | null;
}

export interface Attempt {
  id: string;
  problemId: string;
  attemptNumber: number;
  approachSummary: string;
  reasoning: string | null;
  mistakes: string[];
  analysis: SolutionAnalysis | null;
  status: SubmissionStatus;
  createdAt: string;
  updatedAt: string;
  submissions: Submission[];
}

export interface ProblemNote {
  id: string;
  problemId: string;
  attemptId: string | null;
  content: string;
  noteType: "Intuition" | "Bug Pattern" | "Complexity Analysis" | "General";
  createdAt: string;
}

export interface Problem {
  id: string;
  title: string;
  slug: string;
  difficulty: Difficulty;
  platform: Platform;
  url: string | null;
  topics: string[];
  statement: string | null;
  createdAt: string;
  updatedAt: string;
  attempts: Attempt[];
  notes: ProblemNote[];
}

/* --- Analytics (mirrors analytics/analytics_models.py) ------------------ */

export interface AnalyticsOverview {
  totalProblems: number;
  totalAttempts: number;
  totalSubmissions: number;
  acceptedProblems: number;
  unsolvedProblems: number;
  overallAcceptanceRatePct: number;
  avgAttemptsPerSolvedProblem: number;
  firstAttemptAcceptanceRatePct: number;
  repeatedProblemRatePct: number;
  avgSolvingTimeMinutes: number | null;
  currentStreakDays: number;
  longestStreakDays: number;
  activeDaysLast30: number;
}

export interface TopicStat {
  topic: string;
  totalProblems: number;
  solvedProblems: number;
  totalAttempts: number;
  totalSubmissions: number;
  acceptedSubmissions: number;
  acceptanceRatePct: number;
  successRatePct: number;
}

export interface DifficultyStat {
  difficulty: Difficulty;
  totalProblems: number;
  solvedProblems: number;
  totalAttempts: number;
  totalSubmissions: number;
  acceptedSubmissions: number;
  acceptanceRatePct: number;
}

export interface LanguageStat {
  language: Language;
  totalSubmissions: number;
  acceptedSubmissions: number;
  acceptanceRatePct: number;
  usageSharePct: number;
}

export interface ProgressOverTime {
  period: string;
  label: string;
  problemsSolved: number;
  totalSubmissions: number;
  acceptedSubmissions: number;
}

export interface StruggleProblem {
  problemId: string;
  title: string;
  slug: string;
  difficulty: Difficulty;
  totalAttempts: number;
  failedAttempts: number;
  failedSubmissions: number;
  status: SubmissionStatus;
  topics: string[];
}

/* --- Revision (mirrors revision/revision_models.py) --------------------- */

export interface RevisionScoreBreakdown {
  problemId: string;
  title: string;
  slug: string;
  difficulty: Difficulty;
  finalScore: number;
  difficultyScore: number;
  failureScore: number;
  recencyScore: number;
  weaknessScore: number;
  recentSolvedPenalty: number;
  daysSinceLastActivity: number;
}

export interface RevisionQueueItem {
  problemId: string;
  title: string;
  slug: string;
  difficulty: Difficulty;
  priorityScore: number;
  lastActivityAt: string;
  topics: string[];
  breakdown: RevisionScoreBreakdown;
  reason: string;
  confidence: "Low" | "Medium" | "High";
  status: "Due" | "Overdue" | "Scheduled" | "Learned";
}

/* --- Knowledge graph (mirrors graph/knowledge_graph.py) ----------------- */

export type GraphNodeType = "Topic" | "Problem" | "Approach" | "Mistake" | "Language" | "Concept";

export type GraphRelationship =
  | "TAGGED_WITH"
  | "USES_APPROACH"
  | "ENCOUNTERED_MISTAKE"
  | "SOLVED_IN"
  | "RELATED_TO"
  | "REQUIRES_CONCEPT";

export interface GraphNode {
  id: string;
  label: string;
  type: GraphNodeType;
}

export interface GraphEdge {
  sourceId: string;
  targetId: string;
  relationship: GraphRelationship;
}

export interface KnowledgeGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface KnowledgeCluster {
  id: string;
  title: string;
  description: string;
  topicId: string;
  problemIds: string[];
  masteryPct: number;
}

/* --- Search ----------------------------------------------------------- */

export type SearchResultType = "problem" | "submission" | "knowledge";

export interface SearchResultProblem {
  difficulty: string;
  platform: string;
  topics: string[];
}

export interface SearchResultSubmission {
  language: string;
  status: string;
  runtimeMs: number | null;
  memoryMb: number | null;
  sourceProvider: string | null;
  sourceAccount: string | null;
  submittedAt: string | null;
}

export interface SearchResult {
  type: SearchResultType;
  id: string;
  title: string;
  slug: string;
  metadata: Record<string, unknown>;
}

export interface ActivityDay {
  date: string;
  submissions: number;
  accepted: number;
  solved: number;
  minutesActive: number;
}

export interface TimelineEvent {
  id: string;
  kind: "solved" | "attempted" | "learned" | "revised" | "imported";
  title: string;
  detail: string;
  problemSlug: string | null;
  language: Language | null;
  occurredAt: string;
}
