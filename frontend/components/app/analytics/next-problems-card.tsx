"use client";

import * as React from "react";
import { getNextRecommendations, ApiError } from "@/lib/api";
import type { ProblemRecommendationDTO } from "@/lib/api/types";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { Badge } from "@/components/ui/badge";
import { RefreshCw, AlertCircle, ExternalLink, ChevronDown, ChevronUp, CheckCircle2, ArrowRight, Zap, Target } from "lucide-react";

const DIFFICULTY_COLOR: Record<string, string> = {
  Easy: "success",
  Medium: "warning",
  Hard: "error",
};

function SingleProblemCard({ rec }: { rec: ProblemRecommendationDTO }) {
  const [expanded, setExpanded] = React.useState(false);
  const diffColor = DIFFICULTY_COLOR[rec.difficulty] ?? "neutral";

  return (
    <div className="rounded-xl border border-accent/20 bg-gradient-to-br from-accent/5 to-accent/2 overflow-hidden">
      {/* Header strip */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-accent/15 bg-accent/8">
        <Zap className="h-3.5 w-3.5 text-accent shrink-0" />
        <span className="text-caption font-semibold text-accent tracking-wide uppercase">
          {rec.is_revision ? "Revision Pick" : "Optimize This Next"}
        </span>
      </div>

      {/* Main content */}
      <div className="p-5 space-y-4">
        {/* Title row */}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 space-y-2">
            <p className="text-body font-bold text-text-primary leading-snug">{rec.title}</p>
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant={diffColor as "success" | "warning" | "error" | "neutral"}>
                {rec.difficulty}
              </Badge>
              {rec.topics.slice(0, 3).map((t) => (
                <Badge key={t} variant="neutral" className="text-caption">{t}</Badge>
              ))}
            </div>
          </div>
          {rec.url && (
            <a
              href={rec.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent text-white text-caption font-semibold hover:bg-accent/85 transition-colors"
            >
              <span>Solve</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>

        {/* Why this problem */}
        <div className="space-y-1">
          <p className="text-caption font-semibold text-text-primary flex items-center gap-1.5">
            <Target className="h-3.5 w-3.5 text-accent" />
            Why this problem?
          </p>
          <p className="text-body-sm text-text-secondary leading-relaxed">{rec.selection_rationale}</p>
        </div>

        {/* Optimization focus */}
        <div className="p-3 rounded-lg bg-surface-elevated border border-border-soft">
          <p className="text-caption font-semibold text-text-primary mb-1">Optimization focus</p>
          <p className="text-body-sm text-text-secondary">{rec.solving_focus}</p>
        </div>

        {/* Expand toggle */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 text-caption text-accent hover:underline"
        >
          {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          {expanded ? "Show less" : "Checklist & next step"}
        </button>
      </div>

      {/* Expanded section */}
      {expanded && (
        <div className="border-t border-border-soft p-5 space-y-4 bg-surface-elevated">
          {rec.similarity_reasons && rec.similarity_reasons.length > 0 && (
            <div className="space-y-2">
              <p className="text-caption font-semibold text-text-primary">Why it matches</p>
              {rec.similarity_reasons.map((reason, i) => (
                <div key={i} className="flex items-start gap-2 text-body-sm text-text-secondary">
                  <Target className="h-3.5 w-3.5 mt-0.5 text-accent shrink-0" />
                  <span>{reason}</span>
                </div>
              ))}
            </div>
          )}
          {rec.reflection_checklist.length > 0 && (
            <div className="space-y-2">
              <p className="text-caption font-semibold text-text-primary">Before you submit — check these</p>
              {rec.reflection_checklist.map((item, i) => (
                <div key={i} className="flex items-start gap-2 text-body-sm text-text-secondary">
                  <CheckCircle2 className="h-3.5 w-3.5 mt-0.5 text-success shrink-0" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          )}
          <div className="flex items-start gap-2 text-body-sm text-text-secondary">
            <ArrowRight className="h-3.5 w-3.5 mt-0.5 text-accent shrink-0" />
            <span><span className="font-medium text-text-primary">After solving: </span>{rec.next_step_after}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export function NextProblemsCard({ className, limit = 1 }: { className?: string; limit?: number }) {
  const [data, setData] = React.useState<ProblemRecommendationDTO[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const fetchData = React.useCallback(() => {
    setLoading(true);
    setError(null);
    getNextRecommendations(limit)
      .then((d) => { setData(d.recommendations); setLoading(false); })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "Could not load recommendation.");
        setLoading(false);
      });
  }, [limit]);

  React.useEffect(() => { fetchData(); }, [fetchData]);

  const single = data[0] ?? null;

  return (
    <Surface className={className}>
      <SurfaceHeader
        eyebrow="Solve Next"
        title="Your Next Problem"
        description="Picked from your catalog — related to your latest solve and needs an optimized approach."
        action={
          <button onClick={fetchData} disabled={loading} className="flex items-center gap-1.5 text-caption text-text-muted hover:text-text-primary transition-colors disabled:opacity-50">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        }
      />
      <div className="p-5">
        {loading ? (
          <div className="py-8 text-center space-y-2">
            <RefreshCw className="h-5 w-5 animate-spin mx-auto text-accent" />
            <p className="text-body-sm text-text-muted">Finding your ideal next problem…</p>
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 p-3 rounded bg-error-soft text-error text-body-sm border border-error/25">
            <AlertCircle className="h-4 w-4 shrink-0" /><span>{error}</span>
          </div>
        ) : single ? (
          <SingleProblemCard rec={single} />
        ) : (
          <div className="py-8 text-center">
            <p className="text-body-sm text-text-muted">No unsolved problems in your catalog yet.</p>
            <p className="text-caption text-text-faint mt-1">Sync LeetCode or import problems to get a recommendation.</p>
          </div>
        )}
      </div>
    </Surface>
  );
}
