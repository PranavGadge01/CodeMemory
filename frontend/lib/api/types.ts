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

export interface SubmissionSummaryDTO {
  total: number;
  accepted: number;
  failed: number;
  acceptanceRate: number;
  problemCount: number;
  languageCount: number;
}

export interface SubmissionListDTO extends PaginatedResponse<SubmissionDTO> {
  summary: SubmissionSummaryDTO;
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

/* --- Grounded Insights ------------------------------------------------ */

export interface GroundedInsightDTO {
  scope: string;
  generated_at: string;
  headline: string;
  narrative: string;
  key_observations: string[];
  recommended_actions: string[];
  evidence_summary: string;
  evidence_refs: string[];
  confidence_notes: string[];
  evidence_id: string;
}

/* --- Learning / Explainable AI --------------------------------------- */

export interface ComplexityComparisonDTO {
  current_time: string;
  proposed_time: string;
  current_space: string;
  proposed_space: string;
  explanation: string;
  assumptions: string;
}

export interface OptimizationExplanationDTO {
  problem_slug: string;
  submission_id: string | null;
  current_approach: string;
  approach_source: string;
  current_solution_summary: string;
  bottleneck: string;
  why_it_matters: string;
  recommended_approach: string;
  why_it_works: string;
  complexity_comparison: ComplexityComparisonDTO;
  transformation_steps: string[];
  tradeoffs: string;
  worked_example: string | null;
  edge_cases: string[];
  when_original_is_acceptable: string;
  takeaway: string;
  general_pattern: string;
  follow_up_question: string | null;
  evidence_refs: string[];
}

export interface AttemptTimelineEntryDTO {
  attempt: number;
  submission_id: string;
  status: string;
  language: string;
  runtime_ms: number | null;
  memory_mb: number | null;
  date: string | null;
}

export interface AttemptEvolutionAnalysisDTO {
  problem_slug: string;
  problem_title: string;
  has_code_snapshots: boolean;
  timeline: AttemptTimelineEntryDTO[];
  changes_between_attempts: string[];
  improvements: string[];
  regressions: string[];
  unresolved_issues: string[];
  learning_summary: string;
  recommended_next_action: string;
  evidence_refs: string[];
}

export interface SubmissionPatternFindingDTO {
  title: string;
  observation: string;
  category: string;
  metric_or_examples: string;
  why_it_matters: string;
  suggested_action: string;
  evidence_refs: string[];
}

export interface SubmissionPatternInsightsDTO {
  summary: string;
  findings: SubmissionPatternFindingDTO[];
  most_important_gap: string;
  evidence_refs: string[];
  sample_size_notes: string[];
}

export interface ProblemRecommendationDTO {
  problem_slug: string;
  title: string;
  difficulty: string;
  topics: string[];
  url: string | null;
  is_revision: boolean;
  selection_rationale: string;
  target_skill: string;
  prior_attempt_connection: string;
  difficulty_rationale: string;
  solving_focus: string;
  reflection_checklist: string[];
  next_step_after: string;
  evidence_refs: string[];
  similarity_reasons: string[];
  source: string;
  source_problem_slug: string | null;
}

export interface NextProblemsDTO {
  recommendations: ProblemRecommendationDTO[];
  generated_at: string;
}

export interface RoadmapMilestoneDTO {
  id: string;
  title: string;
  order: number;
  learning_objective: string;
  relevance: string;
  objective: string;
  rationale: string;
  prerequisites: string[];
  concepts_to_study: string[];
  target_skills: string[];
  recommended_problems: ProblemRecommendationDTO[];
  completion_criteria: string;
  reflection_question: string;
  transition: string;
  next_milestone_id: string | null;
  status: string;
  evidence_refs: string[];
}

export interface PersonalizedRoadmapDTO {
  title: string;
  description: string;
  learning_profile_summary: string;
  overall_rationale: string;
  milestones: RoadmapMilestoneDTO[];
  limitations: string[];
  is_early_stage: boolean;
  generated_at: string;
  evidence_id: string;
  is_read_only: boolean;
}

/* --- Collective learning profile ------------------------------------- */

export interface LearningInsightItemDTO {
  category: string;
  title: string;
  summary: string;
  evidence: string;
  impact: string;
  interpretation: string;
  action: string;
  priority: string;
  confidence: string;
  topics: string[];
  examples: string[];
  evidence_refs: string[];
}

export interface LearningProgressTrendDTO {
  metric: string;
  earlier: string;
  recent: string;
  delta: string;
  summary: string;
  evidence_refs: string[];
}

export interface CollectiveLearningProfileDTO {
  total_problems: number;
  total_attempted: number;
  total_solved: number;
  total_submissions: number;
  total_attempts: number;
  acceptance_rate_pct: number;
  first_attempt_acceptance_rate_pct: number;
  avg_attempts_per_solved_problem: number;
  difficulty_solved: Record<string, number>;
  topic_observations: Record<string, unknown>[];
  language_share: Record<string, unknown>[];
  patterns_practiced: string[];
  complexity_signals: Record<string, unknown>[];
}

export interface CollectiveLearningInsightDTO {
  scope: string;
  generated_at: string;
  overall_summary: string;
  profile: CollectiveLearningProfileDTO;
  strengths: LearningInsightItemDTO[];
  weaknesses: LearningInsightItemDTO[];
  recurring_mistakes: LearningInsightItemDTO[];
  optimization_trends: LearningInsightItemDTO[];
  progress: LearningProgressTrendDTO[];
  focus_areas: LearningInsightItemDTO[];
  recommended_actions: string[];
  practice_next: ProblemRecommendationDTO[];
  limitations: string[];
  is_early_stage: boolean;
  evidence_id: string;
  evidence_refs: string[];
}

/* --- Per-submission learning analysis -------------------------------- */

export interface SubmissionImprovementDTO {
  title: string;
  what: string;
  why: string;
  how: string;
  evidence_refs: string[];
}

export interface AttemptComparisonDTO {
  available: boolean;
  previous_submission_id: string | null;
  previous_status: string | null;
  current_status: string | null;
  summary: string;
  changes: string[];
  improvement: string;
  lesson: string;
  evidence_refs: string[];
}

export interface SubmissionLearningAnalysisDTO {
  submission_id: string;
  problem_id: string;
  problem_slug: string;
  problem_title: string;
  difficulty: string;
  topics: string[];
  status: string;
  language: string;
  overview: string;
  what_went_well: string[];
  improvements: SubmissionImprovementDTO[];
  current_approach: string;
  current_time_complexity: string;
  current_space_complexity: string;
  complexity_source: string;
  alternative_approach: string;
  alternative_time_complexity: string;
  alternative_space_complexity: string;
  tradeoffs: string;
  edge_cases: string[];
  cross_problem_connections: string[];
  previous_attempt_comparison: AttemptComparisonDTO;
  lesson: string;
  next_action: string;
  general_pattern: string;
  has_code: boolean;
  limitations: string[];
  evidence_refs: string[];
}
