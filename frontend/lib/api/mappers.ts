/**
 * API → UI domain mapping.
 *
 * The backend DTOs and the UI domain types in `lib/types.ts` agree on most
 * fields, but not all of them. Every difference lives here, in one place, so a
 * page consuming `Problem` or `RevisionQueueItem` never has to know that the
 * wire format differs.
 *
 * The conversions below are pure: given a DTO they produce the domain value the
 * components already consume, without touching the DOM or React.
 */

import type {
  Difficulty,
  GraphEdge,
  GraphNode,
  GraphNodeDetail,
  KnowledgeCluster,
  Language,
  Problem,
  ProblemNote,
  ProgressOverTime,
  RevisionQueueItem,
  SearchResult,
  SolutionAnalysis,
  StruggleProblem,
  Submission,
  SubmissionStatus,
  Attempt,
  ActivityDay,
  TimelineEvent,
  GroundedInsight,
  KnowledgePattern,
  PatternRelationship,
  KnowledgePatternsData,
  SolutionEvolutionData,
  OptimizationExplanation,
  AttemptEvolutionAnalysis,
  SubmissionPatternInsights,
  NextProblems,
  PersonalizedRoadmap,
  CollectiveLearningInsight,
  SubmissionLearningAnalysis,
  ComplexityComparison,
  AttemptTimelineEntry,
  SubmissionPatternFinding,
  LearningInsightItem,
  LearningProgressTrend,
  CollectiveLearningProfile,
  SubmissionImprovement,
  AttemptComparison,
  ProblemRecommendation,
  RoadmapMilestone,
} from "@/lib/types";
import type {
  AnalyticsOverviewDTO,
  ActivityDayDTO,
  TimelineEventDTO,
  AttemptDTO,
  DifficultyStatDTO,
  LanguageStatDTO,
  ProblemDTO,
  ProblemListItemDTO,
  ProblemNoteDTO,
  ProgressOverTimeDTO,
  RevisionQueueItemDTO,
  SolutionAnalysisDTO,
  StruggleProblemDTO,
  SubmissionDTO,
  SubmissionListItemDTO,
  TopicStatDTO,
  GraphEdgeDTO,
  KnowledgeClusterDTO,
  SearchResultItemDTO,
  GroundedInsightDTO,
  KnowledgePatternDTO,
  PatternRelationshipDTO,
  KnowledgePatternsDTO,
  SolutionEvolutionDTO,
  OptimizationExplanationDTO,
  AttemptEvolutionAnalysisDTO,
  SubmissionPatternInsightsDTO,
  NextProblemsDTO,
  PersonalizedRoadmapDTO,
  CollectiveLearningInsightDTO,
  SubmissionLearningAnalysisDTO,
  ComplexityComparisonDTO,
  AttemptTimelineEntryDTO,
  SubmissionPatternFindingDTO,
  ProblemRecommendationDTO,
  RoadmapMilestoneDTO,
  LearningInsightItemDTO,
  LearningProgressTrendDTO,
  CollectiveLearningProfileDTO,
  SubmissionImprovementDTO,
  AttemptComparisonDTO,
} from "@/lib/api/types";

const DIFFICULTIES: Difficulty[] = ["Easy", "Medium", "Hard", "Unknown"];

/** Solve states carried on the problem list summary row. */
const SOLVE_STATUSES = ["Solved", "Attempted", "Untouched"] as const;
export type SolveStatus = (typeof SOLVE_STATUSES)[number];

const SUBMISSION_STATUSES: SubmissionStatus[] = [
  "Accepted",
  "Wrong Answer",
  "Time Limit Exceeded",
  "Memory Limit Exceeded",
  "Runtime Error",
  "Compile Error",
  "Unknown",
];

/**
 * Language names arrive lowercase from the API ("python"); the UI's `Language`
 * union is title-cased ("Python"). Known aliases are mapped explicitly and an
 * unrecognized name is title-cased as a best effort rather than dropped.
 */
const LANGUAGE_ALIASES: Record<string, Language> = {
  python: "Python",
  python3: "Python 3",
  py: "Python",
  java: "Java",
  cpp: "C++",
  "c++": "C++",
  c: "C",
  javascript: "JavaScript",
  js: "JavaScript",
  typescript: "TypeScript",
  ts: "TypeScript",
  go: "Go",
  golang: "Go",
  rust: "Rust",
  ruby: "Ruby",
  swift: "Swift",
  kotlin: "Kotlin",
};

export function mapLanguage(value: string | null | undefined): Language {
  if (!value) return "Unknown" as Language;
  const normalized = value.trim().toLowerCase();
  return LANGUAGE_ALIASES[normalized] ?? (value.trim() as Language);
}

export function mapDifficulty(value: string | null | undefined): Difficulty {
  const match = DIFFICULTIES.find((candidate) => candidate.toLowerCase() === value?.toLowerCase());
  return match ?? "Unknown";
}

export function mapSubmissionStatus(value: string | null | undefined): SubmissionStatus {
  const match = SUBMISSION_STATUSES.find(
    (candidate) => candidate.toLowerCase() === value?.toLowerCase(),
  );
  return match ?? "Unknown";
}

/**
 * The backend reports a problem-level `"Solved"` / `"Unsolved"` on struggle
 * rows, but the UI renders that slot with a `StatusBadge`, which expects a
 * submission status. Solved maps to `Accepted`; unsolved has no submission
 * status of its own, so it becomes `Unknown` — the badge's neutral state.
 */
export function mapStruggleStatus(value: string | null | undefined): SubmissionStatus {
  if (value?.toLowerCase() === "solved") return "Accepted";
  return "Unknown";
}

export function mapSolutionAnalysis(dto: SolutionAnalysisDTO | null): SolutionAnalysis | null {
  if (!dto) return null;
  return {
    approachName: dto.approachName,
    timeComplexity: dto.timeComplexity,
    spaceComplexity: dto.spaceComplexity,
    keyInsights: dto.keyInsights,
    tradeOffs: dto.tradeOffs,
    bottleneck: dto.bottleneck,
  };
}

export function mapSubmission(dto: SubmissionDTO): Submission {
  return {
    id: dto.id,
    problemId: dto.problemId,
    attemptId: dto.attemptId,
    code: dto.code,
    language: mapLanguage(dto.language),
    status: mapSubmissionStatus(dto.status),
    runtimeMs: dto.runtimeMs,
    memoryMb: dto.memoryMb,
    submittedAt: dto.submittedAt,
    errorMessage: dto.errorMessage,
    submissionHash: dto.submissionHash,
    sourceProvider: dto.sourceProvider ?? null,
    sourceAccount: dto.sourceAccount ?? null,
    // The API does not expose a percentile; the UI's "beats" hint renders "—".
    beatsPercent: null,
  };
}

export function mapAttempt(dto: AttemptDTO): Attempt {
  return {
    id: dto.id,
    problemId: dto.problemId,
    attemptNumber: dto.attemptNumber,
    approachSummary: dto.approachSummary,
    reasoning: dto.reasoning,
    mistakes: dto.mistakes,
    analysis: mapSolutionAnalysis(dto.analysis),
    status: mapSubmissionStatus(dto.status),
    createdAt: dto.createdAt,
    updatedAt: dto.updatedAt,
    submissions: dto.submissions.map(mapSubmission),
  };
}

export function mapProblemNote(dto: ProblemNoteDTO): ProblemNote {
  return {
    id: dto.id,
    problemId: dto.problemId,
    attemptId: dto.attemptId,
    content: dto.content,
    noteType: dto.noteType as ProblemNote["noteType"],
    createdAt: dto.createdAt,
  };
}

export function mapProblem(dto: ProblemDTO): Problem {
  return {
    id: dto.id,
    title: dto.title,
    slug: dto.slug,
    difficulty: mapDifficulty(dto.difficulty),
    platform: dto.platform as Problem["platform"],
    url: dto.url,
    topics: dto.topics,
    statement: dto.statement,
    createdAt: dto.createdAt,
    updatedAt: dto.updatedAt,
    attempts: dto.attempts.map(mapAttempt),
    notes: dto.notes.map(mapProblemNote),
  };
}

export type ProblemListItem = {
  id: string;
  title: string;
  slug: string;
  difficulty: Difficulty;
  platform: Problem["platform"];
  topics: string[];
  createdAt: string;
  updatedAt: string;
  attemptCount: number;
  acceptedCount: number;
  submissionCount: number;
  languages: Language[];
  bestRuntime: number | null;
  bestMemory: number | null;
  lastActivityAt: string;
  status: SolveStatus;
};

export function mapProblemListItem(dto: ProblemListItemDTO): ProblemListItem {
  return {
    id: dto.id,
    title: dto.title,
    slug: dto.slug,
    difficulty: mapDifficulty(dto.difficulty),
    platform: dto.platform as Problem["platform"],
    topics: dto.topics,
    createdAt: dto.createdAt,
    updatedAt: dto.updatedAt,
    attemptCount: dto.attemptCount,
    acceptedCount: dto.acceptedCount,
    submissionCount: dto.submissionCount,
    languages: dto.languages.map(mapLanguage),
    bestRuntime: dto.bestRuntime,
    bestMemory: dto.bestMemory,
    lastActivityAt: dto.lastActivityAt ?? dto.updatedAt,
    status: (SOLVE_STATUSES as readonly string[]).includes(dto.status)
      ? (dto.status as SolveStatus)
      : "Untouched",
  };
}

export type SubmissionListItem = Submission & {
  problemTitle: string | null;
  problemSlug: string | null;
};

export function mapSubmissionListItem(dto: SubmissionListItemDTO): SubmissionListItem {
  return {
    ...mapSubmission(dto),
    problemTitle: dto.problemTitle ?? null,
    problemSlug: dto.problemSlug ?? null,
  };
}

/* --- Analytics --------------------------------------------------------- */

export function mapTopicStat(dto: TopicStatDTO) {
  return {
    topic: dto.topic,
    totalProblems: dto.totalProblems,
    solvedProblems: dto.solvedProblems,
    totalAttempts: dto.totalAttempts,
    totalSubmissions: dto.totalSubmissions,
    acceptedSubmissions: dto.acceptedSubmissions,
    acceptanceRatePct: dto.acceptanceRatePct,
    successRatePct: dto.successRatePct,
  };
}

export function mapDifficultyStat(dto: DifficultyStatDTO) {
  return {
    difficulty: mapDifficulty(dto.difficulty),
    totalProblems: dto.totalProblems,
    solvedProblems: dto.solvedProblems,
    totalAttempts: dto.totalAttempts,
    totalSubmissions: dto.totalSubmissions,
    acceptedSubmissions: dto.acceptedSubmissions,
    acceptanceRatePct: dto.acceptanceRatePct,
  };
}

export function mapLanguageStat(dto: LanguageStatDTO) {
  return {
    language: mapLanguage(dto.language),
    totalSubmissions: dto.totalSubmissions,
    acceptedSubmissions: dto.acceptedSubmissions,
    acceptanceRatePct: dto.acceptanceRatePct,
    usageSharePct: dto.usageSharePct,
  };
}

/**
 * Turn a backend period key into the short label the charts render.
 *
 *   "2026-09-06" → "Sep 6"   (day)
 *   "2026-W36"   → "W36"     (week)
 *   "2026-09"    → "Sep 2026" (month)
 *
 * The day path is the common one; the week and month paths keep the label
 * readable when the analytics granularity parameter changes.
 */
export function periodLabel(period: string): string {
  const weekly = /^(\d{4})-W(\d{1,2})$/.exec(period);
  if (weekly) return `W${weekly[2]}`;

  const monthly = /^(\d{4})-(\d{2})$/.exec(period);
  if (monthly) {
    const date = new Date(Number(monthly[1]), Number(monthly[2]) - 1, 1);
    return date.toLocaleDateString("en-US", { month: "short", year: "numeric" });
  }

  const daily = /^(\d{4})-(\d{2})-(\d{2})$/.exec(period);
  if (daily) {
    const date = new Date(Number(daily[1]), Number(daily[2]) - 1, Number(daily[3]));
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  return period;
}

export function mapProgressOverTime(dto: ProgressOverTimeDTO): ProgressOverTime {
  return {
    period: dto.period,
    label: periodLabel(dto.period),
    problemsSolved: dto.problemsSolved,
    totalSubmissions: dto.totalSubmissions,
    acceptedSubmissions: dto.acceptedSubmissions,
  };
}

export function mapStruggleProblem(dto: StruggleProblemDTO): StruggleProblem {
  return {
    problemId: dto.problemId,
    title: dto.title,
    slug: dto.slug,
    difficulty: mapDifficulty(dto.difficulty),
    totalAttempts: dto.totalAttempts,
    failedAttempts: dto.failedAttempts,
    failedSubmissions: dto.failedSubmissions,
    status: mapStruggleStatus(dto.status),
    topics: dto.topics,
  };
}

export function mapAnalyticsOverview(dto: AnalyticsOverviewDTO) {
  return {
    totalProblems: dto.totalProblems,
    totalAttempts: dto.totalAttempts,
    totalSubmissions: dto.totalSubmissions,
    acceptedProblems: dto.acceptedProblems,
    unsolvedProblems: dto.unsolvedProblems,
    overallAcceptanceRatePct: dto.overallAcceptanceRatePct,
    avgAttemptsPerSolvedProblem: dto.avgAttemptsPerSolvedProblem,
    firstAttemptAcceptanceRatePct: dto.firstAttemptAcceptanceRatePct,
    repeatedProblemRatePct: dto.repeatedProblemRatePct,
    avgSolvingTimeMinutes: dto.avgSolvingTimeMinutes,
    currentStreakDays: dto.currentStreakDays,
    longestStreakDays: dto.longestStreakDays,
    activeDaysLast30: dto.activeDaysLast30,
  };
}

/* --- Revision ---------------------------------------------------------- */

/**
 * Revision status is not populated by the backend (the field arrives null), so
 * it is derived from the same facts the queue itself is scored on: a problem
 * untouched for over 30 days is overdue, one touched within 7 days is still
 * scheduled, and the window between is due.
 */
function deriveRevisionStatus(daysSinceLastActivity: number): RevisionQueueItem["status"] {
  if (daysSinceLastActivity > 30) return "Overdue";
  if (daysSinceLastActivity >= 7) return "Due";
  return "Scheduled";
}

/**
 * Confidence is not populated by the backend either. It is derived from the
 * failure component of the score — the same signal the revision service uses
 * to rank the queue.
 */
function deriveRevisionConfidence(failureScore: number): RevisionQueueItem["confidence"] {
  if (failureScore > 3) return "Low";
  if (failureScore > 1) return "Medium";
  return "High";
}

/**
 * A human-readable reason the problem landed in the queue, derived from the
 * breakdown the backend does return. Mirrors the copy the mock layer produced
 * so the queue rows read the same as before.
 */
function deriveRevisionReason(
  dto: RevisionQueueItemDTO["breakdown"],
  lastActivityAt: string | null,
): string {
  const days = dto.daysSinceLastActivity;
  const failed = dto.failureScore;

  if (failed > 1) {
    return `Took ${Math.round(failed)} failed submission${
      Math.round(failed) === 1 ? "" : "s"
    } before accepting — the pattern is not yet internalised.`;
  }

  if (dto.weaknessScore > 0) {
    return `Sits in a weak topic and was last touched ${days} day${days === 1 ? "" : "s"} ago.`;
  }

  return `Last touched ${formatDaysAgo(lastActivityAt)} — worth a refresh before it fades.`;
}

function formatDaysAgo(iso: string | null): string {
  if (!iso) return "some time ago";
  const days = Math.max(
    0,
    Math.round((Date.now() - new Date(iso).getTime()) / (24 * 60 * 60 * 1000)),
  );
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  return `${days} days ago`;
}

/**
 * The revision score components arrive unnormalized — difficulty on a 1–3
 * scale, failure on a 0–5 count, recency on a 0–10 day scale — while the UI's
 * breakdown panel renders each on a 0–1 axis. Each component is rescaled to
 * its own observed maximum so the bars stay proportional and the displayed
 * arithmetic still sums to the priority score.
 */
const SCORE_SCALE = {
  difficulty: 3,
  failure: 5,
  recency: 10,
  weakness: 2,
  recentSolvedPenalty: 4,
} as const;

function normalize(value: number, max: number): number {
  return Math.max(0, Math.min(1, value / max));
}

export function mapRevisionQueueItem(dto: RevisionQueueItemDTO): RevisionQueueItem {
  const breakdown = dto.breakdown;

  return {
    problemId: dto.problemId,
    title: dto.title,
    slug: dto.slug,
    difficulty: mapDifficulty(dto.difficulty),
    priorityScore: dto.priorityScore,
    lastActivityAt: dto.lastActivityAt ?? new Date(0).toISOString(),
    topics: dto.topics,
    status: dto.status === "Due" || dto.status === "Overdue" || dto.status === "Scheduled" ||
      dto.status === "Learned"
      ? dto.status
      : deriveRevisionStatus(breakdown.daysSinceLastActivity),
    confidence: dto.confidence === "Low" || dto.confidence === "Medium" || dto.confidence === "High"
      ? dto.confidence
      : deriveRevisionConfidence(breakdown.failureScore),
    reason: dto.reason ?? deriveRevisionReason(breakdown, dto.lastActivityAt),
    breakdown: {
      problemId: breakdown.problemId,
      title: breakdown.title,
      slug: breakdown.slug,
      difficulty: mapDifficulty(breakdown.difficulty),
      finalScore: breakdown.finalScore,
      difficultyScore: normalize(breakdown.difficultyScore, SCORE_SCALE.difficulty),
      failureScore: normalize(breakdown.failureScore, SCORE_SCALE.failure),
      recencyScore: normalize(breakdown.recencyScore, SCORE_SCALE.recency),
      weaknessScore: normalize(breakdown.weaknessScore, SCORE_SCALE.weakness),
      recentSolvedPenalty: normalize(
        breakdown.recentSolvedPenalty,
        SCORE_SCALE.recentSolvedPenalty,
      ),
      daysSinceLastActivity: breakdown.daysSinceLastActivity,
    },
  };
}

/* --- Knowledge --------------------------------------------------------- */

const GRAPH_NODE_TYPES: GraphNode["type"][] = [
  "Topic",
  "Problem",
  "Approach",
  "Mistake",
  "Language",
  "Concept",
];

/** Knowledge DTO node with expanded details (Problem nodes) or compact details (others) */
type KnowledgeGraphNodeDTO = {
  id: string;
  label: string;
  type: string;
  connectionCount?: number;
  difficulty?: string;
  topics?: string[];
  approaches?: string[];
  languages?: string[];
  mistakes?: string[];
};

export function mapGraphNode(dto: KnowledgeGraphNodeDTO): GraphNode {
  const match = GRAPH_NODE_TYPES.find((candidate) => candidate === dto.type);
  const base: GraphNode = {
    id: dto.id,
    label: dto.label,
    type: match ?? "Concept",
  };
  return base;
}

export function mapGraphNodeDetail(dto: KnowledgeGraphNodeDTO): GraphNodeDetail {
  const match = GRAPH_NODE_TYPES.find((candidate) => candidate === dto.type);
  const base: GraphNodeDetail = {
    id: dto.id,
    label: dto.label,
    type: match ?? "Concept",
    connectionCount: dto.connectionCount,
  };
  // Add optional problem details
  if (dto.difficulty !== undefined) base.difficulty = dto.difficulty;
  if (dto.topics) base.topics = dto.topics;
  if (dto.approaches) base.approaches = dto.approaches;
  if (dto.languages) base.languages = dto.languages;
  if (dto.mistakes !== undefined) base.mistakes = dto.mistakes;
  return base;
}

export function mapGraphEdge(dto: GraphEdgeDTO): GraphEdge {
  return {
    sourceId: dto.sourceId,
    targetId: dto.targetId,
    relationship: dto.relationship as GraphEdge["relationship"],
  };
}

export function mapKnowledgeGraph(dto: { nodes: KnowledgeGraphNodeDTO[]; edges: GraphEdgeDTO[] }) {
  return {
    nodes: dto.nodes.map(mapGraphNode),
    edges: dto.edges.map(mapGraphEdge),
  };
}

export function mapKnowledgeGraphWithDetails(dto: { nodes: KnowledgeGraphNodeDTO[]; edges: GraphEdgeDTO[] }) {
  return {
    nodes: dto.nodes.map(mapGraphNodeDetail),
    edges: dto.edges.map(mapGraphEdge),
  };
}

export function mapKnowledgeCluster(dto: KnowledgeClusterDTO): KnowledgeCluster {
  return {
    id: dto.id,
    title: dto.title,
    description: dto.description,
    topicId: dto.topicId,
    problemIds: dto.problemIds,
    masteryPct: dto.masteryPct,
  };
}

/* --- Activity ---------------------------------------------------------- */

export function mapActivityDay(dto: ActivityDayDTO): ActivityDay {
  return {
    date: dto.date,
    submissions: dto.submissions,
    accepted: dto.accepted,
    solved: dto.solved,
    minutesActive: dto.minutesActive,
  };
}

export function mapTimelineEvent(dto: TimelineEventDTO): TimelineEvent {
  return {
    id: dto.id,
    kind: dto.kind as TimelineEvent["kind"],
    title: dto.title,
    detail: dto.detail,
    problemSlug: dto.problemSlug,
    language: dto.language ? mapLanguage(dto.language) : null,
    occurredAt: dto.occurredAt,
  };
}

/* --- Search ----------------------------------------------------------- */

export function mapSearchResult(dto: SearchResultItemDTO): SearchResult {
  return {
    type: dto.type,
    id: dto.id,
    title: dto.title,
    slug: dto.slug,
    metadata: dto.metadata,
  };
}

/* --- Grounded Insights ------------------------------------------------ */

export function mapGroundedInsight(dto: GroundedInsightDTO): GroundedInsight {
  return {
    scope: dto.scope,
    generatedAt: dto.generated_at,
    headline: dto.headline,
    narrative: dto.narrative,
    keyObservations: dto.key_observations ?? [],
    recommendedActions: dto.recommended_actions ?? [],
    evidenceSummary: dto.evidence_summary ?? "",
    evidenceRefs: dto.evidence_refs ?? [],
    confidenceNotes: dto.confidence_notes ?? [],
    evidenceId: dto.evidence_id,
  };
}

/* --- Knowledge Patterns ------------------------------------------------ */

export function mapKnowledgePattern(dto: KnowledgePatternDTO): KnowledgePattern {
  return {
    id: dto.id,
    label: dto.label,
    description: dto.description,
    problemCount: dto.problemCount,
    firstAttemptAccepts: dto.firstAttemptAccepts,
  };
}

export function mapPatternRelationship(dto: PatternRelationshipDTO): PatternRelationship {
  return {
    patternA: dto.patternA,
    patternB: dto.patternB,
    sharedProblemCount: dto.sharedProblemCount,
  };
}

export function mapKnowledgePatterns(dto: KnowledgePatternsDTO): KnowledgePatternsData {
  return {
    patterns: dto.patterns.map(mapKnowledgePattern),
    relationships: dto.relationships.map(mapPatternRelationship),
    generatedAt: dto.generatedAt,
  };
}

/* --- Solution Evolution ------------------------------------------------- */

export function mapEvolutionStep(dto: SolutionEvolutionDTO["steps"][number]): SolutionEvolutionData["steps"][number] {
  return {
    attemptNumber: dto.attemptNumber,
    status: dto.status,
    approach: dto.approach,
    timeComplexity: dto.timeComplexity,
    spaceComplexity: dto.spaceComplexity,
    runtime: dto.runtime,
    memory: dto.memory,
    timestamp: dto.timestamp,
  };
}

export function mapSolutionEvolution(dto: SolutionEvolutionDTO): SolutionEvolutionData {
  return {
    problemId: dto.problemId,
    problemTitle: dto.problemTitle,
    totalAttempts: dto.totalAttempts,
    steps: dto.steps.map(mapEvolutionStep),
    evolutionNarrative: dto.evolutionNarrative,
    keyBreakthrough: dto.keyBreakthrough ?? null,
    betterApproach: dto.betterApproach ?? null,
    similarProblems: dto.similarProblems ?? [],
  };
}

/* --- Learning / Explainable AI ----------------------------------------- */

export function mapComplexityComparison(
  dto: ComplexityComparisonDTO
): ComplexityComparison {
  return {
    currentTime: dto.current_time,
    proposedTime: dto.proposed_time,
    currentSpace: dto.current_space,
    proposedSpace: dto.proposed_space,
    explanation: dto.explanation,
    assumptions: dto.assumptions,
  };
}

export function mapOptimizationExplanation(
  dto: OptimizationExplanationDTO
): OptimizationExplanation {
  return {
    problemSlug: dto.problem_slug,
    submissionId: dto.submission_id,
    currentApproach: dto.current_approach,
    approachSource: dto.approach_source,
    currentSolutionSummary: dto.current_solution_summary,
    bottleneck: dto.bottleneck,
    whyItMatters: dto.why_it_matters,
    recommendedApproach: dto.recommended_approach,
    whyItWorks: dto.why_it_works,
    complexityComparison: mapComplexityComparison(dto.complexity_comparison),
    transformationSteps: dto.transformation_steps,
    tradeoffs: dto.tradeoffs,
    workedExample: dto.worked_example,
    edgeCases: dto.edge_cases,
    whenOriginalIsAcceptable: dto.when_original_is_acceptable,
    takeaway: dto.takeaway,
    generalPattern: dto.general_pattern,
    followUpQuestion: dto.follow_up_question,
    evidenceRefs: dto.evidence_refs,
  };
}

export function mapAttemptTimelineEntry(
  dto: AttemptEvolutionAnalysisDTO["timeline"][number]
): AttemptTimelineEntry {
  return {
    attempt: dto.attempt,
    submissionId: dto.submission_id,
    status: dto.status,
    language: dto.language,
    runtimeMs: dto.runtime_ms,
    memoryMb: dto.memory_mb,
    date: dto.date,
  };
}

export function mapAttemptEvolutionAnalysis(
  dto: AttemptEvolutionAnalysisDTO
): AttemptEvolutionAnalysis {
  return {
    problemSlug: dto.problem_slug,
    problemTitle: dto.problem_title,
    hasCodeSnapshots: dto.has_code_snapshots,
    timeline: dto.timeline.map(mapAttemptTimelineEntry),
    changesBetweenAttempts: dto.changes_between_attempts,
    improvements: dto.improvements,
    regressions: dto.regressions,
    unresolvedIssues: dto.unresolved_issues,
    learningSummary: dto.learning_summary,
    recommendedNextAction: dto.recommended_next_action,
    evidenceRefs: dto.evidence_refs,
  };
}

export function mapSubmissionPatternFinding(
  dto: SubmissionPatternFindingDTO
): SubmissionPatternFinding {
  return {
    title: dto.title,
    observation: dto.observation,
    category: dto.category,
    metricOrExamples: dto.metric_or_examples,
    whyItMatters: dto.why_it_matters,
    suggestedAction: dto.suggested_action,
    evidenceRefs: dto.evidence_refs,
  };
}

export function mapSubmissionPatternInsights(
  dto: SubmissionPatternInsightsDTO
): SubmissionPatternInsights {
  return {
    summary: dto.summary,
    findings: dto.findings.map(mapSubmissionPatternFinding),
    mostImportantGap: dto.most_important_gap,
    evidenceRefs: dto.evidence_refs,
    sampleSizeNotes: dto.sample_size_notes,
  };
}

export function mapProblemRecommendation(dto: ProblemRecommendationDTO): ProblemRecommendation {
  return {
    problemSlug: dto.problem_slug,
    title: dto.title,
    difficulty: dto.difficulty,
    topics: dto.topics,
    url: dto.url,
    isRevision: dto.is_revision,
    selectionRationale: dto.selection_rationale,
    targetSkill: dto.target_skill,
    priorAttemptConnection: dto.prior_attempt_connection,
    difficultyRationale: dto.difficulty_rationale,
    solvingFocus: dto.solving_focus,
    reflectionChecklist: dto.reflection_checklist,
    nextStepAfter: dto.next_step_after,
    evidenceRefs: dto.evidence_refs,
    similarityReasons: dto.similarity_reasons,
    source: dto.source,
    sourceProblemSlug: dto.source_problem_slug,
  };
}

export function mapNextProblems(dto: NextProblemsDTO): NextProblems {
  return {
    recommendations: dto.recommendations.map(mapProblemRecommendation),
    generatedAt: dto.generated_at,
  };
}

export function mapRoadmapMilestone(dto: RoadmapMilestoneDTO): RoadmapMilestone {
  return {
    id: dto.id,
    title: dto.title,
    order: dto.order,
    learningObjective: dto.learning_objective,
    relevance: dto.relevance,
    objective: dto.objective,
    rationale: dto.rationale,
    prerequisites: dto.prerequisites,
    conceptsToStudy: dto.concepts_to_study,
    targetSkills: dto.target_skills,
    recommendedProblems: dto.recommended_problems.map(mapProblemRecommendation),
    completionCriteria: dto.completion_criteria,
    reflectionQuestion: dto.reflection_question,
    transition: dto.transition,
    nextMilestoneId: dto.next_milestone_id,
    status: dto.status,
    evidenceRefs: dto.evidence_refs,
  };
}

export function mapPersonalizedRoadmap(dto: PersonalizedRoadmapDTO): PersonalizedRoadmap {
  return {
    title: dto.title,
    description: dto.description,
    learningProfileSummary: dto.learning_profile_summary,
    overallRationale: dto.overall_rationale,
    milestones: dto.milestones.map(mapRoadmapMilestone),
    limitations: dto.limitations,
    isEarlyStage: dto.is_early_stage,
    generatedAt: dto.generated_at,
    evidenceId: dto.evidence_id,
    isReadOnly: dto.is_read_only,
  };
}

export function mapLearningInsightItem(dto: LearningInsightItemDTO): LearningInsightItem {
  return {
    category: dto.category,
    title: dto.title,
    summary: dto.summary,
    evidence: dto.evidence,
    impact: dto.impact,
    interpretation: dto.interpretation,
    action: dto.action,
    priority: dto.priority,
    confidence: dto.confidence,
    topics: dto.topics,
    examples: dto.examples,
    evidenceRefs: dto.evidence_refs,
  };
}

export function mapLearningProgressTrend(dto: LearningProgressTrendDTO): LearningProgressTrend {
  return {
    metric: dto.metric,
    earlier: dto.earlier,
    recent: dto.recent,
    delta: dto.delta,
    summary: dto.summary,
    evidenceRefs: dto.evidence_refs,
  };
}

export function mapCollectiveLearningProfile(
  dto: CollectiveLearningProfileDTO
): CollectiveLearningProfile {
  return {
    totalProblems: dto.total_problems,
    totalAttempted: dto.total_attempted,
    totalSolved: dto.total_solved,
    totalSubmissions: dto.total_submissions,
    totalAttempts: dto.total_attempts,
    acceptanceRatePct: dto.acceptance_rate_pct,
    firstAttemptAcceptanceRatePct: dto.first_attempt_acceptance_rate_pct,
    avgAttemptsPerSolvedProblem: dto.avg_attempts_per_solved_problem,
    difficultySolved: dto.difficulty_solved,
    topicObservations: dto.topic_observations,
    languageShare: dto.language_share,
    patternsPracticed: dto.patterns_practiced,
    complexitySignals: dto.complexity_signals,
  };
}

export function mapCollectiveLearningInsight(
  dto: CollectiveLearningInsightDTO
): CollectiveLearningInsight {
  return {
    scope: dto.scope,
    generatedAt: dto.generated_at,
    overallSummary: dto.overall_summary,
    profile: mapCollectiveLearningProfile(dto.profile),
    strengths: dto.strengths.map(mapLearningInsightItem),
    weaknesses: dto.weaknesses.map(mapLearningInsightItem),
    recurringMistakes: dto.recurring_mistakes.map(mapLearningInsightItem),
    optimizationTrends: dto.optimization_trends.map(mapLearningInsightItem),
    progress: dto.progress.map(mapLearningProgressTrend),
    focusAreas: dto.focus_areas.map(mapLearningInsightItem),
    recommendedActions: dto.recommended_actions,
    practiceNext: dto.practice_next.map(mapProblemRecommendation),
    limitations: dto.limitations,
    isEarlyStage: dto.is_early_stage,
    evidenceId: dto.evidence_id,
    evidenceRefs: dto.evidence_refs,
  };
}

/* --- Per-submission learning analysis ----------------------------------- */

export function mapSubmissionImprovement(
  dto: SubmissionImprovementDTO
): SubmissionImprovement {
  return {
    title: dto.title,
    what: dto.what,
    why: dto.why,
    how: dto.how,
    evidenceRefs: dto.evidence_refs,
  };
}

export function mapAttemptComparison(
  dto: AttemptComparisonDTO
): AttemptComparison {
  return {
    available: dto.available,
    previousSubmissionId: dto.previous_submission_id,
    previousStatus: dto.previous_status,
    currentStatus: dto.current_status,
    summary: dto.summary,
    changes: dto.changes,
    improvement: dto.improvement,
    lesson: dto.lesson,
    evidenceRefs: dto.evidence_refs,
  };
}

export function mapSubmissionLearningAnalysis(
  dto: SubmissionLearningAnalysisDTO
): SubmissionLearningAnalysis {
  return {
    submissionId: dto.submission_id,
    problemId: dto.problem_id,
    problemSlug: dto.problem_slug,
    problemTitle: dto.problem_title,
    difficulty: dto.difficulty,
    topics: dto.topics,
    status: dto.status,
    language: dto.language,
    overview: dto.overview,
    whatWentWell: dto.what_went_well,
    improvements: dto.improvements.map(mapSubmissionImprovement),
    currentApproach: dto.current_approach,
    currentTimeComplexity: dto.current_time_complexity,
    currentSpaceComplexity: dto.current_space_complexity,
    complexitySource: dto.complexity_source,
    alternativeApproach: dto.alternative_approach,
    alternativeTimeComplexity: dto.alternative_time_complexity,
    alternativeSpaceComplexity: dto.alternative_space_complexity,
    tradeoffs: dto.tradeoffs,
    edgeCases: dto.edge_cases,
    crossProblemConnections: dto.cross_problem_connections,
    previousAttemptComparison: mapAttemptComparison(dto.previous_attempt_comparison),
    lesson: dto.lesson,
    nextAction: dto.next_action,
    generalPattern: dto.general_pattern,
    hasCode: dto.has_code,
    limitations: dto.limitations,
    evidenceRefs: dto.evidence_refs,
  };
}

