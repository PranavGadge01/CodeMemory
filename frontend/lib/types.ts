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

/** Entity counts for the knowledge snapshot header */
export interface KnowledgeEntityCounts {
  Problem?: number;
  Topic?: number;
  Approach?: number;
  Mistake?: number;
  Language?: number;
  Concept?: number;
}

/** Extended graph node with optional problem details */
export interface GraphNodeDetail extends GraphNode {
  difficulty?: string;
  topics?: string[];
  approaches?: string[];
  languages?: string[];
  mistakes?: string[];
  connectionCount?: number;
}

export interface KnowledgeCluster {
  id: string;
  title: string;
  description: string;
  topicId: string;
  problemIds: string[];
  masteryPct: number;
}

export interface KnowledgeData {
  graph: KnowledgeGraph;
  clusters: KnowledgeCluster[];
  entityCounts: KnowledgeEntityCounts;
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

/* --- Grounded Insights ------------------------------------------------ */

export interface GroundedInsight {
  scope: string;
  generatedAt: string;
  headline: string;
  narrative: string;
  keyObservations: string[];
  recommendedActions: string[];
  evidenceSummary: string;
  evidenceRefs: string[];
  confidenceNotes: string[];
  evidenceId: string;
}

/* --- Knowledge Patterns ------------------------------------------------- */

export interface KnowledgePattern {
  id: string;
  label: string;
  description: string;
  problemCount: number;
  firstAttemptAccepts: number;
}

export interface PatternRelationship {
  patternA: string;
  patternB: string;
  sharedProblemCount: number;
}

export interface KnowledgePatternsData {
  patterns: KnowledgePattern[];
  relationships: PatternRelationship[];
  generatedAt: string;
}

/* --- Solution Evolution -------------------------------------------------- */

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

export interface SolutionEvolutionData {
  problemId: string;
  problemTitle: string;
  totalAttempts: number;
  steps: SolutionEvolutionStep[];
  evolutionNarrative: string;
  keyBreakthrough: string | null;
  betterApproach?: string | null;
  similarProblems?: string[];
}

/* --- Learning / Explainable AI ------------------------------------------ */

export interface ComplexityComparison {
  currentTime: string;
  proposedTime: string;
  currentSpace: string;
  proposedSpace: string;
  explanation: string;
  assumptions: string;
}

export interface OptimizationExplanation {
  problemSlug: string;
  submissionId: string | null;
  currentApproach: string;
  approachSource: string;
  currentSolutionSummary: string;
  bottleneck: string;
  whyItMatters: string;
  recommendedApproach: string;
  whyItWorks: string;
  complexityComparison: ComplexityComparison;
  transformationSteps: string[];
  tradeoffs: string;
  workedExample: string | null;
  edgeCases: string[];
  whenOriginalIsAcceptable: string;
  takeaway: string;
  generalPattern: string;
  followUpQuestion: string | null;
  evidenceRefs: string[];
}

export interface AttemptTimelineEntry {
  attempt: number;
  submissionId: string;
  status: string;
  language: string;
  runtimeMs: number | null;
  memoryMb: number | null;
  date: string | null;
}

export interface AttemptEvolutionAnalysis {
  problemSlug: string;
  problemTitle: string;
  hasCodeSnapshots: boolean;
  timeline: AttemptTimelineEntry[];
  changesBetweenAttempts: string[];
  improvements: string[];
  regressions: string[];
  unresolvedIssues: string[];
  learningSummary: string;
  recommendedNextAction: string;
  evidenceRefs: string[];
}

export interface SubmissionPatternFinding {
  title: string;
  observation: string;
  category: string;
  metricOrExamples: string;
  whyItMatters: string;
  suggestedAction: string;
  evidenceRefs: string[];
}

export interface SubmissionPatternInsights {
  summary: string;
  findings: SubmissionPatternFinding[];
  mostImportantGap: string;
  evidenceRefs: string[];
  sampleSizeNotes: string[];
}

export interface ProblemRecommendation {
  problemSlug: string;
  title: string;
  difficulty: string;
  topics: string[];
  url: string | null;
  isRevision: boolean;
  selectionRationale: string;
  targetSkill: string;
  priorAttemptConnection: string;
  difficultyRationale: string;
  solvingFocus: string;
  reflectionChecklist: string[];
  nextStepAfter: string;
  evidenceRefs: string[];
  similarityReasons: string[];
  source: string;
  sourceProblemSlug: string | null;
}

export interface NextProblems {
  recommendations: ProblemRecommendation[];
  generatedAt: string;
}

export interface RoadmapMilestone {
  id: string;
  title: string;
  order: number;
  learningObjective: string;
  relevance: string;
  objective: string;
  rationale: string;
  prerequisites: string[];
  conceptsToStudy: string[];
  targetSkills: string[];
  recommendedProblems: ProblemRecommendation[];
  completionCriteria: string;
  reflectionQuestion: string;
  transition: string;
  nextMilestoneId: string | null;
  status: string;
  evidenceRefs: string[];
}

export interface PersonalizedRoadmap {
  title: string;
  description: string;
  learningProfileSummary: string;
  overallRationale: string;
  milestones: RoadmapMilestone[];
  limitations: string[];
  isEarlyStage: boolean;
  generatedAt: string;
  evidenceId: string;
  isReadOnly: boolean;
}

/* --- Collective learning profile ---------------------------------------- */

export interface LearningInsightItem {
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
  evidenceRefs: string[];
}

export interface LearningProgressTrend {
  metric: string;
  earlier: string;
  recent: string;
  delta: string;
  summary: string;
  evidenceRefs: string[];
}

export interface CollectiveLearningProfile {
  totalProblems: number;
  totalAttempted: number;
  totalSolved: number;
  totalSubmissions: number;
  totalAttempts: number;
  acceptanceRatePct: number;
  firstAttemptAcceptanceRatePct: number;
  avgAttemptsPerSolvedProblem: number;
  difficultySolved: Record<string, number>;
  topicObservations: Record<string, unknown>[];
  languageShare: Record<string, unknown>[];
  patternsPracticed: string[];
  complexitySignals: Record<string, unknown>[];
}

export interface CollectiveLearningInsight {
  scope: string;
  generatedAt: string;
  overallSummary: string;
  profile: CollectiveLearningProfile;
  strengths: LearningInsightItem[];
  weaknesses: LearningInsightItem[];
  recurringMistakes: LearningInsightItem[];
  optimizationTrends: LearningInsightItem[];
  progress: LearningProgressTrend[];
  focusAreas: LearningInsightItem[];
  recommendedActions: string[];
  practiceNext: ProblemRecommendation[];
  limitations: string[];
  isEarlyStage: boolean;
  evidenceId: string;
  evidenceRefs: string[];
}

/* --- Per-submission learning analysis ----------------------------------- */

export interface SubmissionImprovement {
  title: string;
  what: string;
  why: string;
  how: string;
  evidenceRefs: string[];
}

export interface AttemptComparison {
  available: boolean;
  previousSubmissionId: string | null;
  previousStatus: string | null;
  currentStatus: string | null;
  summary: string;
  changes: string[];
  improvement: string;
  lesson: string;
  evidenceRefs: string[];
}

export interface SubmissionLearningAnalysis {
  submissionId: string;
  problemId: string;
  problemSlug: string;
  problemTitle: string;
  difficulty: string;
  topics: string[];
  status: string;
  language: string;
  overview: string;
  whatWentWell: string[];
  improvements: SubmissionImprovement[];
  currentApproach: string;
  currentTimeComplexity: string;
  currentSpaceComplexity: string;
  complexitySource: string;
  alternativeApproach: string;
  alternativeTimeComplexity: string;
  alternativeSpaceComplexity: string;
  tradeoffs: string;
  edgeCases: string[];
  crossProblemConnections: string[];
  previousAttemptComparison: AttemptComparison;
  lesson: string;
  nextAction: string;
  generalPattern: string;
  hasCode: boolean;
  limitations: string[];
  evidenceRefs: string[];
}