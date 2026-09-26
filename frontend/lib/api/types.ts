/**
 * API response types.
 *
 * These mirror the backend DTOs in `src/api/schemas/` *exactly as the API
 * returns them* — camelCase aliases and all. They are deliberately separate
 * from the UI domain types in `lib/types.ts`: the two agree in most places,
 * but where they disagree the difference is made explicit in `mappers.ts`
 * rather than papered over with an unsafe cast.
 *
 * Every field typed `X | null` is optional in the backend schema and observed
 * to arrive empty in practice.
 */

/* --- Shared ------------------------------------------------------------ */

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
}

/* --- Analytics --------------------------------------------------------- */

export interface AnalyticsOverviewDTO {
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

export interface TopicStatDTO {
  topic: string;
  totalProblems: number;
  solvedProblems: number;
  totalAttempts: number;
  totalSubmissions: number;
  acceptedSubmissions: number;
  acceptanceRatePct: number;
  successRatePct: number;
}

export interface DifficultyStatDTO {
  difficulty: string;
  totalProblems: number;
  solvedProblems: number;
  totalAttempts: number;
  totalSubmissions: number;
  acceptedSubmissions: number;
  acceptanceRatePct: number;
}

export interface LanguageStatDTO {
  language: string;
  totalSubmissions: number;
  acceptedSubmissions: number;
  acceptanceRatePct: number;
  usageSharePct: number;
}

export interface ProgressOverTimeDTO {
  /** "2026-09-06" (day) | "2026-W36" (week) | "2026-09" (month) */
  period: string;
  problemsSolved: number;
  totalSubmissions: number;
  acceptedSubmissions: number;
}

export interface StruggleProblemDTO {
  problemId: string;
  title: string;
  slug: string;
  difficulty: string;
  totalAttempts: number;
  failedAttempts: number;
  failedSubmissions: number;
  /** Problem-level status: "Solved" or "Unsolved" — not a submission status. */
  status: string;
  topics: string[];
}

export interface AnalyticsDTO {
  overview: AnalyticsOverviewDTO;
  topics: TopicStatDTO[];
  difficulties: DifficultyStatDTO[];
  languages: LanguageStatDTO[];
  progress: ProgressOverTimeDTO[];
  struggles: StruggleProblemDTO[];
}

/* --- Dashboard --------------------------------------------------------- */

export interface ActivityDayDTO {
  date: string;
  submissions: number;
  accepted: number;
  solved: number;
  minutesActive: number;
}

export interface TimelineEventDTO {
  id: string;
  kind: string;
  title: string;
  detail: string;
  problemSlug: string | null;
  language: string | null;
  occurredAt: string;
}

export interface DashboardDTO {
  overview: AnalyticsOverviewDTO;
  activity: ActivityDayDTO[];
  timeline: TimelineEventDTO[];
  struggles: StruggleProblemDTO[];
  topics: TopicStatDTO[];
  languages: LanguageStatDTO[];
  difficulties: DifficultyStatDTO[];
  revisionQueue: RevisionQueueItemDTO[];
  progress: ProgressOverTimeDTO[];
}

/* --- Problems ---------------------------------------------------------- */

export interface SolutionAnalysisDTO {
  approachName: string;
  timeComplexity: string;
  spaceComplexity: string;
  keyInsights: string[];
  tradeOffs: string | null;
  bottleneck: string | null;
}

export interface SubmissionDTO {
  id: string;
  problemId: string;
  attemptId: string | null;
  code: string | null;
  /** Lowercase on the wire: "python", not "Python". */
  language: string;
  status: string;
  runtimeMs: number | null;
  memoryMb: number | null;
  submittedAt: string;
  errorMessage: string | null;
  submissionHash: string;
  sourceProvider: string | null;
  sourceAccount: string | null;
}

export interface AttemptDTO {
  id: string;
  problemId: string;
  attemptNumber: number;
  approachSummary: string;
  reasoning: string | null;
  mistakes: string[];
  analysis: SolutionAnalysisDTO | null;
  status: string;
  createdAt: string;
  updatedAt: string;
  submissions: SubmissionDTO[];
}

export interface ProblemNoteDTO {
  id: string;
  problemId: string;
  attemptId: string | null;
  content: string;
  noteType: string;
  createdAt: string;
}

export interface ProblemDTO {
  id: string;
  title: string;
  slug: string;
  difficulty: string;
  platform: string;
  url: string | null;
  topics: string[];
  statement: string | null;
  createdAt: string;
  updatedAt: string;
  attempts: AttemptDTO[];
  notes: ProblemNoteDTO[];
}

export interface ProblemListItemDTO {
  id: string;
  title: string;
  slug: string;
  difficulty: string;
  platform: string;
  topics: string[];
  createdAt: string;
  updatedAt: string;
}

/* --- Revision ---------------------------------------------------------- */

export interface RevisionScoreBreakdownDTO {
  problemId: string;
  title: string;
  slug: string;
  difficulty: string;
  finalScore: number;
  /** Unnormalized: Easy=1.0, Medium=2.0, Hard=3.0, Unknown=0.5. */
  difficultyScore: number;
  /** Unnormalized: raw failed-attempt/submission count, capped at 5. */
  failureScore: number;
  /** Unnormalized: days since last activity / 7, capped at 10. */
  recencyScore: number;
  /** Unnormalized: 2.0 for a weak topic, otherwise 0.0. */
  weaknessScore: number;
  /** Unnormalized: 4.0 minus days since solve, when solved within 3 days. */
  recentSolvedPenalty: number;
  daysSinceLastActivity: number;
}

export interface RevisionQueueItemDTO {
  problemId: string;
  title: string;
  slug: string;
  difficulty: string;
  priorityScore: number;
  lastActivityAt: string | null;
  topics: string[];
  /** Not populated by the backend — arrives as null. */
  status: string | null;
  /** Not populated by the backend — arrives as null. */
  confidence: string | null;
  /** Not populated by the backend — arrives as null. */
  reason: string | null;
  breakdown: RevisionScoreBreakdownDTO;
}

/* --- Search ------------------------------------------------------------ */

export interface SearchResultItemDTO {
  type: "problem" | "submission" | "knowledge";
  id: string;
  title: string;
  slug: string;
  metadata: Record<string, unknown>;
}

export interface SearchResponseDTO {
  query: string;
  results: SearchResultItemDTO[];
}

export interface GraphNodeDTO {
  id: string;
  label: string;
  type: string;
}

export interface GraphEdgeDTO {
  sourceId: string;
  targetId: string;
  relationship: string;
}

export interface KnowledgeGraphDTO {
  nodes: GraphNodeDTO[];
  edges: GraphEdgeDTO[];
}

export interface EvolutionStepDTO {
  attemptNumber: number;
  status: string;
  approach: string;
  timeComplexity: string;
  spaceComplexity: string;
  runtime: string | null;
  memory: string | null;
  timestamp: string;
}

export interface SolutionEvolutionDTO {
  problemId: string;
  problemTitle: string;
  totalAttempts: number;
  steps: EvolutionStepDTO[];
  evolutionNarrative: string;
  keyBreakthrough: string | null;
  betterApproach?: string | null;
  similarProblems?: string[];
}

export interface KnowledgeClusterDTO {
  id: string;
  title: string;
  description: string;
  topicId: string;
  problemIds: string[];
  masteryPct: number;
}

export interface KnowledgeDTO {
  graph: KnowledgeGraphDTO;
  clusters: KnowledgeClusterDTO[];
}

/* --- Settings ---------------------------------------------------------- */

export interface SettingsDTO {
  leetcodeConnected: boolean;
  autosyncEnabled: boolean;
  dataDir: string;
  version: string;
  theme: string;
  accentEmphasis: boolean;
  compactDensity: boolean;
  reducedMotion: boolean;
  codeFontSize: string;
  defaultCodeLanguage: string;
  defaultDifficulty: string;
  showFailedAttempts: boolean;
  autoExpandEvolution: boolean;
  timestampDisplay: string;
}

/* --- LeetCode ---------------------------------------------------------- */

export interface LeetCodeStatusDTO {
  connected: boolean;
  username: string | null;
  displayName: string | null;
  userAvatar: string | null;
  accountStatus: string;
  syncState: string;
  lastAttemptedSync: string | null;
  lastSuccessfulSync: string | null;
  recordsDiscovered: number | null;
  recordsImported: number | null;
  recordsSkipped: number | null;
  recordsFailed: number | null;
  coverage: string | null;
  windowLimit: number | null;
  recordsInWindow: number | null;
  windowTruncated: boolean | null;
  gapDetected: boolean | null;
  unavailableFields: string[];
  solvedAll: number | null;
  solvedEasy: number | null;
  solvedMedium: number | null;
  solvedHard: number | null;
  ranking: number | null;
  lastError: string | null;
  capabilities: Record<string, boolean>;
}

export interface LeetCodeSyncResultDTO {
  status: string;
  recordsDiscovered: number;
  recordsImported: number;
  recordsSkipped: number;
  recordsFailed: number;
  errorMessage: string | null;
}

export interface LeetCodeAuthStatusDTO extends LeetCodeStatusDTO {
  credentialsStored: boolean;
  validationMessage: string | null;
}

export interface LeetCodeAuthSyncResultDTO {
  status: string;
  recordsDiscovered: number;
  recordsAdded: number;
  recordsSkipped: number;
  recordsFailed: number;
  codeFetched: number;
  codeFailed: number;
  errorMessage: string | null;
}

/* --- Health ------------------------------------------------------------ */

export interface HealthDTO {
  overall: string;
  storage: {
    status: string;
    problems: number;
    tiers: string;
  };
  timestamp: string;
}
