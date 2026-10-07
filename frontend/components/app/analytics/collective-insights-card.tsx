"use client";

import * as React from "react";
import { getCollectiveLearningProfile, ApiError } from "@/lib/api";
import type {
  CollectiveLearningInsightDTO,
  LearningInsightItemDTO,
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
  TrendingUp,
  TrendingDown,
  Target,
  Award,
  Info,
  ExternalLink,
  Lightbulb,
} from "lucide-react";
import { cn } from "@/lib/utils";

const PRIORITY_VARIANT: Record<string, "error" | "warning" | "neutral"> = {
  high: "error",
  medium: "warning",
  low: "neutral",
};

const CONFIDENCE_LABEL: Record<string, string> = {
  recurring: "Recurring pattern",
  early_signal: "Early signal",
};

function InsightRow({ item, accent }: { item: LearningInsightItemDTO; accent: string }) {
  const [expanded, setExpanded] = React.useState(false);
  const hasDetail = Boolean(item.impact || item.interpretation || item.action || item.evidence);

  return (
    <div className="rounded-lg border border-border-soft bg-surface-card p-3.5 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className={cn("mt-1 h-1.5 w-1.5 rounded-full shrink-0", accent)} aria-hidden="true" />
          <span className="text-body-sm font-semibold text-text-primary">{item.title}</span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <Badge variant={PRIORITY_VARIANT[item.priority] ?? "neutral"} className="text-caption capitalize">
            {item.priority}
          </Badge>
          <span className="text-caption text-text-faint">
            {CONFIDENCE_LABEL[item.confidence] ?? item.confidence}
          </span>
        </div>
      </div>

      <p className="text-body-sm text-text-secondary">{item.summary}</p>

      {item.examples.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {item.examples.slice(0, 4).map((ex) => (
            <span
              key={ex}
              className="px-1.5 py-0.5 rounded text-caption bg-surface-elevated text-text-muted border border-border-soft"
            >
              {ex}
            </span>
          ))}
        </div>
      )}

      {hasDetail && (
        <>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="flex items-center gap-1 text-caption text-accent hover:underline"
          >
            {expanded ? "Show less" : "Why it matters & action"}
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
          {expanded && (
            <div className="pt-2 border-t border-border-soft space-y-1.5">
              {item.evidence && (
                <p className="text-caption text-text-muted">
                  <span className="font-medium text-text-primary">Evidence: </span>
                  {item.evidence}
                </p>
              )}
              {item.impact && (
                <p className="text-caption text-text-secondary">
                  <span className="font-medium text-text-primary">Why it matters: </span>
                  {item.impact}
                </p>
              )}
              {item.interpretation && (
                <p className="text-caption text-text-muted italic">{item.interpretation}</p>
              )}
              {item.action && (
                <p className="text-caption text-accent font-medium">→ {item.action}</p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function SectionTitle({ icon, label, count }: { icon: React.ReactNode; label: string; count: number }) {
  return (
    <div className="flex items-center gap-2">
      {icon}
      <span className="eyebrow text-text-primary">{label}</span>
      <span className="text-caption text-text-faint">({count})</span>
    </div>
  );
}

function PracticeNext({ recs }: { recs: ProblemRecommendationDTO[] }) {
  if (recs.length === 0) return null;
  return (
    <div className="space-y-2">
      <SectionTitle icon={<Target className="h-3.5 w-3.5 text-accent" />} label="Practice next" count={recs.length} />
      <div className="space-y-2">
        {recs.map((rec) => (
          <div key={rec.problem_slug} className="flex items-center justify-between gap-2 rounded-lg bg-surface-elevated border border-border-soft p-2.5">
            <div className="min-w-0">
              <p className="text-body-sm text-text-primary truncate">{rec.title}</p>
              <p className="text-caption text-text-muted truncate">{rec.target_skill || rec.selection_rationale}</p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Badge variant="neutral" className="text-caption">{rec.difficulty}</Badge>
              {rec.url && (
                <a
                  href={rec.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-caption font-semibold text-accent hover:opacity-75"
                >
                  Open <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function CollectiveInsightsCard({ className }: { className?: string }) {
  const [data, setData] = React.useState<CollectiveLearningInsightDTO | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const fetchData = React.useCallback(() => {
    setLoading(true);
    setError(null);
    getCollectiveLearningProfile()
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "Could not load your learning profile.");
        setLoading(false);
      });
  }, []);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  const profile = data?.profile;

  return (
    <Surface className={className}>
      <SurfaceHeader
        eyebrow="Your DSA Learning Profile"
        title="What you have learned so far"
        description="Strengths, recurring mistakes, and trends computed from your entire solved and attempted history."
        action={
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-1.5 text-caption text-text-muted hover:text-text-primary transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        }
      />

      <div className="p-5 space-y-5">
        {loading ? (
          <div className="py-8 text-center space-y-2">
            <RefreshCw className="h-5 w-5 animate-spin mx-auto text-accent" />
            <p className="text-body-sm text-text-muted">Analysing your full practice history…</p>
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 p-3 rounded bg-error-soft text-error text-body-sm border border-error/25">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : data && profile ? (
          <>
            <div className="flex items-start justify-between gap-2">
              <p className="text-body-sm text-text-secondary leading-relaxed">{data.overall_summary}</p>
              {data.is_early_stage && (
                <Badge variant="neutral" className="text-caption shrink-0">Early stage</Badge>
              )}
            </div>

            {profile.total_problems > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <Stat label="Problems" value={String(profile.total_problems)} />
                <Stat label="Solved" value={String(profile.total_solved)} />
                <Stat label="Acceptance" value={`${profile.acceptance_rate_pct.toFixed(0)}%`} />
                <Stat label="First-try" value={`${profile.first_attempt_acceptance_rate_pct.toFixed(0)}%`} />
              </div>
            )}

            {data.strengths.length > 0 && (
              <div className="space-y-2">
                <SectionTitle icon={<Award className="h-3.5 w-3.5 text-success" />} label="Your strengths" count={data.strengths.length} />
                {data.strengths.map((s, i) => (
                  <InsightRow key={i} item={s} accent="bg-success" />
                ))}
              </div>
            )}

            {data.weaknesses.length > 0 && (
              <div className="space-y-2">
                <SectionTitle icon={<TrendingDown className="h-3.5 w-3.5 text-warning" />} label="Top improvement areas" count={data.weaknesses.length} />
                {data.weaknesses.map((w, i) => (
                  <InsightRow key={i} item={w} accent="bg-warning" />
                ))}
              </div>
            )}

            {data.recurring_mistakes.length > 0 && (
              <div className="space-y-2">
                <SectionTitle icon={<AlertCircle className="h-3.5 w-3.5 text-error" />} label="Recurring mistakes" count={data.recurring_mistakes.length} />
                {data.recurring_mistakes.map((m, i) => (
                  <InsightRow key={i} item={m} accent="bg-error" />
                ))}
              </div>
            )}

            {data.progress.length > 0 && (
              <div className="space-y-2">
                <SectionTitle icon={<TrendingUp className="h-3.5 w-3.5 text-accent" />} label="Your progress" count={data.progress.length} />
                <div className="rounded-lg border border-border-soft overflow-hidden">
                  <div className="grid grid-cols-4 gap-2 px-3 py-1.5 bg-surface-elevated text-caption text-text-faint">
                    <span>Metric</span>
                    <span>Earlier</span>
                    <span>Recent</span>
                    <span>Change</span>
                  </div>
                  {data.progress.map((p, i) => (
                    <div key={i} className="grid grid-cols-4 gap-2 px-3 py-2 border-t border-border-soft text-caption">
                      <span className="text-text-primary">{p.metric}</span>
                      <span className="text-text-muted">{p.earlier}</span>
                      <span className="text-text-muted">{p.recent}</span>
                      <span className="text-accent">{p.delta || "—"}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {data.optimization_trends.length > 0 && (
              <div className="space-y-2">
                <SectionTitle icon={<TrendingUp className="h-3.5 w-3.5 text-accent" />} label="How your solutions are evolving" count={data.optimization_trends.length} />
                {data.optimization_trends.map((t, i) => (
                  <InsightRow key={i} item={t} accent="bg-accent" />
                ))}
              </div>
            )}

            {data.focus_areas.length > 0 && (
              <div className="space-y-2">
                <SectionTitle icon={<Target className="h-3.5 w-3.5 text-accent" />} label="What to focus on next" count={data.focus_areas.length} />
                {data.focus_areas.map((f, i) => (
                  <InsightRow key={i} item={f} accent="bg-accent" />
                ))}
              </div>
            )}

            {data.recommended_actions.length > 0 && (
              <div className="space-y-2">
                <SectionTitle icon={<Lightbulb className="h-3.5 w-3.5 text-warning" />} label="Recommended actions" count={data.recommended_actions.length} />
                <ul className="space-y-1.5">
                  {data.recommended_actions.map((action, i) => (
                    <li key={i} className="flex items-start gap-2 text-body-sm text-text-secondary">
                      <CheckCircle2 className="h-3.5 w-3.5 mt-0.5 text-accent shrink-0" />
                      <span>{action}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <PracticeNext recs={data.practice_next} />

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
          </>
        ) : (
          <div className="py-8 text-center">
            <p className="text-body-sm text-text-muted">No learning profile could be built yet.</p>
            <p className="text-caption text-text-faint mt-1">
              Import or sync submissions to build a profile from your history.
            </p>
          </div>
        )}
      </div>
    </Surface>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-surface-elevated border border-border-soft px-3 py-2">
      <p className="text-caption text-text-faint">{label}</p>
      <p className="text-heading-xs text-text-primary tabular-nums">{value}</p>
    </div>
  );
}