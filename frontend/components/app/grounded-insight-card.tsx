"use client";

import * as React from "react";
import { getFullProfileInsight, getTopicInsight, getProblemInsight, ApiError } from "@/lib/api";
import type { GroundedInsight } from "@/lib/types";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { Badge } from "@/components/ui/badge";
import { Sparkles, CheckCircle2, Lightbulb, AlertCircle, RefreshCw } from "lucide-react";

export interface GroundedInsightCardProps {
  type?: "full" | "topic" | "problem";
  topic?: string;
  slug?: string;
  className?: string;
}

export function GroundedInsightCard({
  type = "full",
  topic,
  slug,
  className,
}: GroundedInsightCardProps) {
  const [insight, setInsight] = React.useState<GroundedInsight | null>(null);
  const [loading, setLoading] = React.useState<boolean>(true);
  const [error, setError] = React.useState<string | null>(null);
  const [showSummary, setShowSummary] = React.useState<boolean>(false);

  const fetchInsight = React.useCallback(() => {
    setLoading(true);
    setError(null);

    let promise: Promise<GroundedInsight>;
    if (type === "topic" && topic) {
      promise = getTopicInsight(topic);
    } else if (type === "problem" && slug) {
      promise = getProblemInsight(slug);
    } else {
      promise = getFullProfileInsight();
    }

    promise
      .then((data) => {
        setInsight(data);
        setLoading(false);
      })
      .catch((err: unknown) => {
        const msg =
          err instanceof ApiError
            ? err.message
            : "Could not fetch grounded insight.";
        setError(msg);
        setLoading(false);
      });
  }, [type, topic, slug]);

  React.useEffect(() => {
    fetchInsight();
  }, [fetchInsight]);

  return (
    <Surface className={className}>
      <SurfaceHeader
        eyebrow="Grounded AI Intelligence"
        title="AI Practice Insight"
        description="Grounded strictly in your recorded practice evidence — zero hallucinated metrics."
        action={
          <button
            onClick={fetchInsight}
            disabled={loading}
            className="flex items-center gap-1.5 text-caption text-text-muted hover:text-text-primary transition-colors disabled:opacity-50"
            title="Refresh Insight"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        }
      />

      <div className="p-5 space-y-4">
        {loading ? (
          <div className="py-6 text-center space-y-2">
            <RefreshCw className="h-5 w-5 animate-spin mx-auto text-accent" />
            <p className="text-body-sm text-text-muted">Generating grounded insight from practice evidence...</p>
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 p-3 rounded bg-error-soft text-error text-body-sm border border-error/25">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : insight ? (
          <>
            <div className="flex items-center justify-between gap-2">
              <Badge variant="accent" className="capitalize">
                {insight.scope.replace("_", " ")}
              </Badge>

              <span className="text-caption text-text-faint">
                Evidence ID: {insight.evidenceId.slice(0, 8)}...
              </span>
            </div>

            <div className="space-y-1.5">
              <h4 className="text-heading-xs text-text-primary font-semibold">
                {insight.headline}
              </h4>
              <p className="text-body-sm text-text-secondary leading-relaxed whitespace-pre-line">
                {insight.narrative}
              </p>
            </div>

            {insight.keyObservations.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-border-soft">
                <div className="eyebrow text-text-muted flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                  <span>Key Observations</span>
                </div>
                <ul className="space-y-1 text-body-sm text-text-secondary pl-5 list-disc">
                  {insight.keyObservations.map((obs, idx) => (
                    <li key={idx}>{obs}</li>
                  ))}
                </ul>
              </div>
            )}

            {insight.recommendedActions.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-border-soft">
                <div className="eyebrow text-text-muted flex items-center gap-1.5">
                  <Lightbulb className="h-3.5 w-3.5 text-warning" />
                  <span>Recommended Actions</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {insight.recommendedActions.map((act, idx) => (
                    <Badge key={idx} variant="neutral">
                      {act}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {insight.evidenceSummary && (
              <div className="pt-2 border-t border-border-soft">
                <button
                  onClick={() => setShowSummary(!showSummary)}
                  className="text-caption text-accent hover:underline font-medium"
                >
                  {showSummary ? "Hide Evidence Summary" : "Show Deterministic Evidence Summary"}
                </button>
                {showSummary && (
                  <pre className="mt-2 p-3 rounded bg-surface-card text-caption text-text-muted font-mono whitespace-pre-wrap border border-border">
                    {insight.evidenceSummary}
                  </pre>
                )}
              </div>
            )}
          </>
        ) : null}
      </div>
    </Surface>
  );
}
