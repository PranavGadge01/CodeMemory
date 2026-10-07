"use client";

import * as React from "react";
import { getPersonalizedRoadmap, ApiError } from "@/lib/api";
import type {
  PersonalizedRoadmapDTO,
  RoadmapMilestoneDTO,
  ProblemRecommendationDTO,
} from "@/lib/api/types";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { Badge } from "@/components/ui/badge";
import {
  RefreshCw,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Circle,
  Lock,
  ExternalLink,
  Target,
  Sparkles,
  BookOpen,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; label: string }> = {
  available: { icon: <Circle className="h-4 w-4 text-accent" />, label: "Available" },
  completed: { icon: <CheckCircle2 className="h-4 w-4 text-success" />, label: "Completed" },
  locked: { icon: <Lock className="h-4 w-4 text-text-faint" />, label: "Later" },
  in_progress: { icon: <RefreshCw className="h-4 w-4 text-warning" />, label: "Start here" },
};

const DIFFICULTY_VARIANT = {
  Easy: "success",
  Medium: "warning",
  Hard: "error",
} as const;

type BadgeVariant = "success" | "warning" | "error" | "neutral";

function ProblemRow({ prob }: { prob: ProblemRecommendationDTO }) {
  const [showWhy, setShowWhy] = React.useState(false);
  const reasons =
    prob.similarity_reasons && prob.similarity_reasons.length > 0
      ? prob.similarity_reasons
      : [prob.selection_rationale];

  return (
    <div className="rounded-lg bg-surface-elevated border border-border-soft">
      <div className="flex items-center justify-between gap-2 p-2.5">
        <div className="flex items-center gap-2 min-w-0">
          <Badge
            variant={(DIFFICULTY_VARIANT[prob.difficulty as keyof typeof DIFFICULTY_VARIANT] ?? "neutral") as BadgeVariant}
            className="text-caption shrink-0"
          >
            {prob.difficulty}
          </Badge>
          <span className="text-body-sm text-text-primary truncate">{prob.title}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setShowWhy((v) => !v)}
            className="text-caption text-text-muted hover:text-text-primary transition-colors"
          >
            {showWhy ? "Hide why" : "Why this?"}
          </button>
          {prob.url && (
            <a
              href={prob.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-caption font-semibold text-accent hover:opacity-75"
            >
              <span>Open</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </div>

      {showWhy && (
        <div className="px-3 pb-3 pt-2 border-t border-border-soft space-y-2">
          {prob.topics.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {prob.topics.slice(0, 4).map((t) => (
                <span key={t} className="px-1.5 py-0.5 rounded text-caption bg-surface-card text-text-muted border border-border-soft">
                  {t}
                </span>
              ))}
            </div>
          )}
          <p className="text-caption text-text-secondary">
            <span className="font-medium text-text-primary">Skill: </span>
            {prob.target_skill}
          </p>
          <ul className="space-y-1">
            {reasons.map((reason, i) => (
              <li key={i} className="flex items-start gap-1.5 text-caption text-text-secondary">
                <CheckCircle2 className="h-3 w-3 mt-0.5 text-accent shrink-0" />
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function PhaseCard({ milestone, index }: { milestone: RoadmapMilestoneDTO; index: number }) {
  const [expanded, setExpanded] = React.useState(index === 0);
  const [showWhy, setShowWhy] = React.useState(false);
  const status = STATUS_CONFIG[milestone.status] ?? STATUS_CONFIG.locked;
  const objective = milestone.objective || milestone.learning_objective;
  const rationale = milestone.rationale || milestone.relevance;
  const skills = milestone.target_skills?.length ? milestone.target_skills : milestone.concepts_to_study;

  return (
    <div
      className={cn(
        "rounded-xl border transition-all duration-200",
        milestone.status === "completed"
          ? "border-success/30 bg-success/5"
          : milestone.status === "in_progress"
          ? "border-accent/40 bg-accent/5"
          : "border-border-soft bg-surface-card",
      )}
    >
      <button onClick={() => setExpanded(!expanded)} className="w-full flex items-center gap-3 p-4 text-left">
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-surface-elevated border border-border-soft flex items-center justify-center">
          <span className="text-caption font-bold text-text-primary">{milestone.order}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {status.icon}
            <p className="text-body-sm font-semibold text-text-primary truncate">{milestone.title}</p>
            <Badge variant="neutral" className="text-caption shrink-0">
              {milestone.recommended_problems.length} problems
            </Badge>
          </div>
          <p className="text-caption text-text-muted mt-0.5 line-clamp-2">{objective}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Badge variant="neutral" className="text-caption capitalize">{status.label}</Badge>
          {expanded ? <ChevronUp className="h-4 w-4 text-text-faint" /> : <ChevronDown className="h-4 w-4 text-text-faint" />}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-border-soft p-4 space-y-4">
          <button
            onClick={() => setShowWhy((v) => !v)}
            className="flex items-center gap-1.5 text-caption font-medium text-accent hover:underline"
          >
            <Sparkles className="h-3.5 w-3.5" />
            {showWhy ? "Hide phase rationale" : "Why this phase?"}
          </button>
          {showWhy && (
            <div className="p-3 rounded-lg bg-surface-elevated border border-border-soft space-y-2">
              <p className="text-body-sm text-text-secondary leading-relaxed">{rationale}</p>
              {milestone.prerequisites.length > 0 && (
                <div>
                  <p className="text-caption font-medium text-text-primary mb-1">Prerequisites</p>
                  <div className="flex flex-wrap gap-1.5">
                    {milestone.prerequisites.map((p) => (
                      <Badge key={p} variant="neutral" className="text-caption">{p}</Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {skills.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-1.5">
                <BookOpen className="h-3.5 w-3.5 text-accent" />
                <p className="text-caption font-medium text-text-primary">Target skills</p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {skills.map((c) => (
                  <span key={c} className="px-2 py-0.5 rounded text-caption bg-accent/10 text-accent border border-accent/20">
                    {c}
                  </span>
                ))}
              </div>
            </div>
          )}

          {milestone.recommended_problems.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <Target className="h-3.5 w-3.5 text-accent" />
                <p className="text-caption font-medium text-text-primary">Practice these</p>
              </div>
              <div className="space-y-2">
                {milestone.recommended_problems.map((prob) => (
                  <ProblemRow key={prob.problem_slug} prob={prob} />
                ))}
              </div>
            </div>
          )}

          <div className="space-y-1.5">
            <p className="text-caption font-medium text-text-primary">Done when</p>
            <p className="text-body-sm text-text-secondary">{milestone.completion_criteria}</p>
          </div>

          {milestone.reflection_question && (
            <div className="p-3 rounded-lg bg-accent/8 border border-accent/20">
              <p className="text-body-sm text-accent italic">{milestone.reflection_question}</p>
            </div>
          )}

          {milestone.transition && (
            <p className="text-caption text-text-faint">{milestone.transition}</p>
          )}
        </div>
      )}
    </div>
  );
}

export function PersonalizedRoadmapCard({ className }: { className?: string }) {
  const [data, setData] = React.useState<PersonalizedRoadmapDTO | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const fetchData = React.useCallback(() => {
    setLoading(true);
    setError(null);
    getPersonalizedRoadmap()
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "Could not load roadmap.");
        setLoading(false);
      });
  }, []);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <Surface className={className}>
      <SurfaceHeader
        eyebrow="Personalized DSA Roadmap"
        title={data?.title ?? "Personalized DSA Roadmap"}
        description="Based on your solved problems, submission history, and recurring improvement areas."
        action={
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-1.5 text-caption text-text-muted hover:text-text-primary transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Regenerate</span>
          </button>
        }
      />
      <div className="p-5 space-y-3">
        {loading ? (
          <div className="py-10 text-center space-y-2">
            <RefreshCw className="h-6 w-6 animate-spin mx-auto text-accent" />
            <p className="text-body-sm text-text-muted">Building your personalized roadmap...</p>
            <p className="text-caption text-text-faint">This analyses your full history, it may take a moment.</p>
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 p-3 rounded bg-error-soft text-error text-body-sm border border-error/25">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : data && data.milestones.length > 0 ? (
          <>
            {(data.learning_profile_summary || data.overall_rationale) && (
              <div className="p-3 rounded-lg bg-surface-elevated border border-border-soft space-y-1.5">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-3.5 w-3.5 text-accent" />
                  <p className="text-caption font-semibold text-text-primary">Personalized from your history</p>
                  {data.is_early_stage && (
                    <Badge variant="neutral" className="text-caption">Early stage</Badge>
                  )}
                </div>
                {data.learning_profile_summary && (
                  <p className="text-body-sm text-text-secondary">{data.learning_profile_summary}</p>
                )}
                {data.overall_rationale && (
                  <p className="text-caption text-text-muted">{data.overall_rationale}</p>
                )}
              </div>
            )}

            {data.limitations.length > 0 && (
              <div className="flex items-start gap-2 p-2.5 rounded-lg bg-surface-elevated border border-border-soft">
                <Info className="h-3.5 w-3.5 mt-0.5 text-text-faint shrink-0" />
                <div className="space-y-0.5">
                  {data.limitations.slice(0, 3).map((lim, i) => (
                    <p key={i} className="text-caption text-text-muted">{lim}</p>
                  ))}
                </div>
              </div>
            )}

            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 rounded-full bg-surface-elevated overflow-hidden">
                <div
                  className="h-full bg-accent rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.round(
                      (data.milestones.filter((m) => m.status === "completed").length /
                        data.milestones.length) *
                        100,
                    )}%`,
                  }}
                />
              </div>
              <span className="text-caption text-text-muted shrink-0">
                {data.milestones.length} phases
              </span>
            </div>

            <div className="space-y-2.5">
              {data.milestones.map((m, i) => (
                <PhaseCard key={m.id} milestone={m} index={i} />
              ))}
            </div>

            <p className="text-caption text-text-faint text-right">
              Generated {new Date(data.generated_at).toLocaleDateString()}
            </p>
          </>
        ) : (
          <div className="py-8 text-center">
            <p className="text-body-sm text-text-muted">No roadmap could be built yet.</p>
            <p className="text-caption text-text-faint mt-1">
              Add or sync more problems so each phase can be filled with at least three real problems.
            </p>
          </div>
        )}
      </div>
    </Surface>
  );
}
